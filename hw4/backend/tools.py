"""Read-only catalogue tools the agent can call.

These only read the `catalogue` and `inventory` tables through a read-only
connection. They never touch `users` or `chat_messages`.
"""

import functools
import json
import math
import re
import sqlite3
import time

import audit

from db import CATEGORIES, category_for, get_db, image_url, size_sort_key
from models import (
    LookupMiss,
    PageSearch,
    ProductCard,
    ProductDetails,
    ProductListing,
    ProductMatch,
    ProductSummary,
    SearchResults,
    SizeStock,
    StockCheck,
)

MAX_RESULTS = 12  # Search results given to the agent.
MAX_PAGE_RESULTS = 120  # Chat search results shown on the Products page (covers the whole catalogue).
LOW_STOCK = 3  # At or below this, a size counts as "low stock".

# Garment words shoppers use, mapped to text that appears in garment_type values.
GARMENT_SYNONYMS = {
    "hoodie": ["hood"],
    "hoody": ["hood"],
    "sweatshirt": ["sweatshirt", "crewneck", "hood", "quarter-zip", "mockneck"],
    "crew": ["crewneck"],
    "tee": ["t-shirt"],
    "t-shirt": ["t-shirt"],
    "sweater": ["sweatshirt", "crewneck", "quarter-zip"],
    "tshirt": ["t-shirt"],
    "shirt": ["shirt"],
    "quarter zip": ["quarter-zip"],
    "1/4 zip": ["quarter-zip"],
    "zip": ["zip"],
    "fleece": ["fleece"],
    "jacket": ["jacket"],
}

# Spelling variants shoppers use that the catalogue spells one way.
WORD_VARIANTS = {"grey": "gray", "colour": "color"}

# A color a shopper names, mapped to the catalogue color words in that family.
# e.g. "blue" also finds navy, navy blue, royal blue, and light blue.
COLOR_FAMILIES = {
    "blue": ["blue", "navy"],
    "navy": ["navy"],
    "gray": ["gray", "charcoal"],
    "charcoal": ["charcoal"],
    "white": ["white", "ivory", "cream"],
    "cream": ["cream", "ivory"],
    "red": ["red"],
    "pink": ["pink", "coral"],
    "coral": ["coral"],
    "yellow": ["yellow", "gold"],
    "gold": ["gold", "yellow"],
    "green": ["green"],
    "black": ["black"],
}

SORTS = ("price_low", "price_high", "name")

# How shoppers name sizes, mapped to the sizes in the inventory table.
SIZE_ALIASES = {
    "xs": "XS", "extra small": "XS", "x-small": "XS", "xsmall": "XS",
    "s": "S", "small": "S", "sm": "S",
    "m": "M", "medium": "M", "med": "M",
    "l": "L", "large": "L", "lg": "L",
    "xl": "XL", "extra large": "XL", "x-large": "XL", "xlarge": "XL",
    "xxl": "XXL", "2xl": "XXL", "xx-large": "XXL", "xxlarge": "XXL", "2x": "XXL",
}

# Words that don't help identify a product by name.
NAME_STOPWORDS = {"the", "a", "an", "in", "of", "for", "size", "one", "your", "that", "this"}

# Text a keyword can match. The users table is never queried.
_SEARCH_TEXT = "(c.name || ' ' || c.garment_type || ' ' || c.description || ' ' || c.colors || ' ' || c.search_tags)"
_NAME_TEXT = "(c.product_id || ' ' || c.name || ' ' || c.garment_type || ' ' || c.search_tags)"


def _normalize_word(word: str) -> str:
    return WORD_VARIANTS.get(word, word)


def _garment_patterns(garment_type: str) -> list[str]:
    term = garment_type.strip().lower().rstrip("s")
    return GARMENT_SYNONYMS.get(term, [term])


def _normalize_size(size: str) -> str | None:
    return SIZE_ALIASES.get(size.strip().lower().rstrip("."))


def _sizes_in_stock(stock: list[SizeStock]) -> list[str]:
    return [s.size for s in stock if s.quantity > 0]


def _stock_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    stock = [SizeStock(size=r["size"], quantity=r["quantity"], sold_out=r["quantity"] == 0) for r in rows]
    return sorted(stock, key=lambda s: size_sort_key(s.size))


def _resolve_product(conn: sqlite3.Connection, product: str) -> sqlite3.Row | LookupMiss:
    """Find one catalogue row from an id or a (partial) product name."""
    query = product.strip()
    cols = "c.product_id, c.name, c.garment_type, c.description, c.colors, c.price"

    # 1. Exact id or exact name.
    row = conn.execute(
        f"SELECT {cols} FROM catalogue c WHERE c.product_id = ? OR LOWER(c.name) = LOWER(?)",
        (query, query),
    ).fetchone()
    if row:
        return row

    # 2. Every meaningful word appears in the id, name, garment type, or tags.
    words = [
        _normalize_word(w)
        for w in re.findall(r"[a-z0-9']+", query.lower().replace("-", " "))
        if w not in NAME_STOPWORDS
    ][:8]
    if not words:
        return LookupMiss(reason="not_found", query=query, candidates=[])
    where = " AND ".join(f"LOWER({_NAME_TEXT}) LIKE ?" for _ in words)
    rows = conn.execute(
        f"SELECT {cols} FROM catalogue c WHERE {where} ORDER BY c.name LIMIT 6",
        [f"%{w}%" for w in words],
    ).fetchall()
    if len(rows) == 1:
        return rows[0]
    if rows:
        return LookupMiss(
            reason="ambiguous",
            query=query,
            candidates=[ProductMatch(product_id=r["product_id"], name=r["name"]) for r in rows],
        )

    # 3. Nothing matched every word: offer the products matching the most words.
    score = " + ".join(f"(LOWER({_NAME_TEXT}) LIKE ?)" for _ in words)
    near = conn.execute(
        f"SELECT c.product_id, c.name, ({score}) AS hits FROM catalogue c "
        "WHERE hits > 0 ORDER BY hits DESC, c.name LIMIT 5",
        [f"%{w}%" for w in words],
    ).fetchall()
    return LookupMiss(
        reason="not_found",
        query=query,
        candidates=[ProductMatch(product_id=r["product_id"], name=r["name"]) for r in near],
    )


# --- Agent tools ---------------------------------------------------------------


def search_products(
    keyword: str | None = None,
    category: str | None = None,
    garment_type: str | None = None,
    color: str | None = None,
    size: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "price_low",
    in_stock_only: bool = True,
) -> SearchResults:
    """Search the Campus Customs catalogue to find, compare, or recommend products.
    Always call this before recommending specific products. All filters are optional.

    Args:
        keyword: Words to find in the name, description, colors, and tags,
            e.g. "baseball", "Davenport", "Harvard game", "gift". Every word must match.
        category: One of: Hoodies, Crewnecks & sweatshirts, T-shirts, Quarter-zips,
            Jackets & fleece, Long-sleeve shirts.
        garment_type: Free-text garment word if no category fits, e.g. "bomber", "mockneck".
        color: A color, e.g. "blue" (also matches navy, royal blue, light blue), "gray"/"grey",
            "white" (also ivory, cream), "pink" (closest: dusty coral).
        size: Only products with stock in this size: XS, S, M, L, XL, XXL or words like "medium".
        min_price: Lowest price in US dollars.
        max_price: Highest price in US dollars.
        sort: "price_low" (default; use for affordable/cheap/budget requests),
            "price_high" (premium/nicest), or "name".
        in_stock_only: If true (default), skip products with no stock in any size.

    Returns up to 12 products plus the true number of matches. If nothing matches,
    `alternatives` holds close real products and `relaxed_filters` says which of
    your filters were dropped to find them.
    """
    filters = dict(
        keyword=keyword, category=category, garment_type=garment_type, color=color,
        size=size, min_price=min_price, max_price=max_price,
    )
    all_rows = _search_rows(**filters, sort=sort)
    in_stock = [r for r in all_rows if r["total_stock"] > 0]
    shown = in_stock if in_stock_only else all_rows

    alternatives: list[ProductSummary] = []
    relaxed: list[str] = []
    if not shown:
        # Drop the most specific filters first until something real turns up.
        for name in ("color", "size", "min_price", "max_price", "keyword", "garment_type", "category"):
            if filters.get(name) is None:
                continue
            filters[name] = None
            relaxed.append(name)
            if not any(v is not None for v in filters.values()):
                break
            rows = [r for r in _search_rows(**filters, sort=sort) if r["total_stock"] > 0]
            if rows:
                alternatives = [_summary(r) for r in rows[:6]]
                break
        if not alternatives:
            # Nothing close (e.g. sneakers): offer one real, in-stock pick per category.
            picks: dict[str, dict] = {}
            for r in _search_rows(sort="price_low"):
                if r["total_stock"] > 0:
                    picks.setdefault(r["category"], r)
            alternatives = [_summary(r) for r in picks.values()]
            relaxed = ["all"]

    return SearchResults(
        total_in_stock=len(in_stock),
        total_including_sold_out=len(all_rows),
        products=[_summary(r) for r in shown[:MAX_RESULTS]],
        alternatives=alternatives,
        relaxed_filters=relaxed,
    )


def _summary(r: dict) -> ProductSummary:
    return ProductSummary(
        product_id=r["product_id"],
        name=r["name"],
        category=r["category"],
        garment_type=r["garment_type"],
        colors=r["colors"],
        price=r["price"],
        total_stock=r["total_stock"],
        sizes_in_stock=r["sizes_in_stock"],
    )


def _color_words(color: str) -> list[str]:
    c = _normalize_word(color.strip().lower())
    return COLOR_FAMILIES.get(c, [c])


def _category_name(category: str) -> str | None:
    c = category.strip().lower().replace(" ", "-").replace("1/4", "quarter")
    c = c.replace("-&-", " & ")
    for name in CATEGORIES:
        n = name.lower()
        if c == n or c.rstrip("s") in n or n.split(" ")[0].rstrip("s") in c:
            return name
    return None


def _search_rows(
    keyword: str | None = None,
    category: str | None = None,
    garment_type: str | None = None,
    color: str | None = None,
    size: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    sort: str = "price_low",
) -> list[dict]:
    """Shared catalogue search for the agent's tool and the Products page results.

    One SQL query does the text and price filtering; category, color family, and
    size are applied in Python on the (at most 102) rows that come back.
    """
    where: list[str] = []
    params: list[object] = []
    if keyword:
        for word in re.findall(r"[\w'-]+", keyword.lower())[:6]:
            where.append(f"LOWER({_SEARCH_TEXT}) LIKE ?")
            params.append(f"%{_normalize_word(word)}%")
    if garment_type:
        patterns = _garment_patterns(garment_type)
        where.append("(" + " OR ".join("LOWER(c.garment_type) LIKE ?" for _ in patterns) + ")")
        params.extend(f"%{p}%" for p in patterns)
    if min_price is not None:
        where.append("c.price >= ?")
        params.append(min_price)
    if max_price is not None:
        where.append("c.price <= ?")
        params.append(max_price)

    sql = f"""
        SELECT c.product_id, c.name, c.garment_type, c.description, c.colors, c.price,
               c.image_file_path,
               COALESCE(SUM(i.quantity), 0) AS total_stock,
               GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_in_stock
        FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
        {"WHERE " + " AND ".join(where) if where else ""}
        GROUP BY c.product_id
    """
    with get_db() as conn:
        raw = conn.execute(sql, params).fetchall()

    want_category = _category_name(category) if category else None
    if category and want_category is None:
        # Not one of our category names ("tees", "sweaters"…): match garment words instead.
        patterns = _garment_patterns(category)
        raw = [r for r in raw if any(p in r["garment_type"].lower() for p in patterns)]
        category = None
    color_words = _color_words(color) if color else None
    want_size = _normalize_size(size) if size else None

    rows: list[dict] = []
    for r in raw:
        cat = category_for(r["garment_type"])
        if category and cat != want_category:
            continue
        colors = json.loads(r["colors"])
        if color_words:
            # Match the product's listed colors only, so a navy logo on a gray tee isn't "blue".
            listed = " ".join(colors).lower()
            if not any(w in listed for w in color_words):
                continue
        sizes = sorted(r["sizes_in_stock"].split(",") if r["sizes_in_stock"] else [], key=size_sort_key)
        if size and want_size not in sizes:
            continue
        rows.append({**dict(r), "category": cat, "colors": colors, "sizes_in_stock": sizes})

    if sort == "price_high":
        rows.sort(key=lambda r: (-r["price"], r["name"]))
    elif sort == "name":
        rows.sort(key=lambda r: r["name"])
    else:
        rows.sort(key=lambda r: (r["price"], r["name"]))
    return rows


def similar_products(product: str) -> list[ProductSummary] | LookupMiss:
    """Find other products like one product, e.g. the same kind of item in other
    colors or designs. Use for "does this come in another color?" or "anything like this?".
    (Each catalogue product has fixed colors; other colors are separate products.)

    Args:
        product: The product's id or name (on a product page, use its product_id).

    Returns up to 6 in-stock products in the same category, most similar first.
    """
    with get_db() as conn:
        row = _resolve_product(conn, product)
    if isinstance(row, LookupMiss):
        return row
    cat = category_for(row["garment_type"])
    base_words = set(re.findall(r"[a-z]{3,}", row["name"].lower())) - {"yale", "the", "and"}
    candidates = [r for r in _search_rows(category=cat) if r["product_id"] != row["product_id"] and r["total_stock"] > 0]
    candidates.sort(key=lambda r: -len(base_words & set(re.findall(r"[a-z]{3,}", r["name"].lower()))))
    return [_summary(r) for r in candidates[:6]]


def get_product_details(product: str) -> ProductDetails | LookupMiss:
    """Get one product's description, colors, price, and stock in every size.
    Use for "tell me about…", "how much is…", and "what sizes do you have…".

    Args:
        product: The product's id (from search_products) or its name,
            e.g. "Davenport College Crewneck" or "davenport crewneck".

    Returns the product, or a LookupMiss with candidate products if the name
    matched none or several.
    """
    with get_db() as conn:
        row = _resolve_product(conn, product)
        if isinstance(row, LookupMiss):
            return row
        stock = _stock_for(conn, row["product_id"])

    return ProductDetails(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        stock_by_size=stock,
        sizes_in_stock=_sizes_in_stock(stock),
        total_stock=sum(s.quantity for s in stock),
    )


def check_stock(product: str, size: str) -> StockCheck | LookupMiss:
    """Check how many of one product are in stock in one size.
    Use for "do you have <product> in <size>?" and "how many <size> are left?".

    Args:
        product: The product's id (from search_products) or its name,
            e.g. "Davenport College Crewneck" or "davenport crewneck".
        size: The size the shopper asked for: XS, S, M, L, XL, XXL, or words
            like "medium" or "extra large".

    Returns the quantity and a status: in_stock, low_stock (3 or fewer),
    sold_out (0 left), or size_not_offered. Also lists the sizes that are in
    stock so you can suggest one when the requested size is sold out.
    """
    with get_db() as conn:
        row = _resolve_product(conn, product)
        if isinstance(row, LookupMiss):
            return row
        stock = _stock_for(conn, row["product_id"])

    in_stock = _sizes_in_stock(stock)
    wanted = _normalize_size(size)
    match = next((s for s in stock if s.size == wanted), None)
    if match is None:
        status, quantity = "size_not_offered", 0
    elif match.quantity == 0:
        status, quantity = "sold_out", 0
    elif match.quantity <= LOW_STOCK:
        status, quantity = "low_stock", match.quantity
    else:
        status, quantity = "in_stock", match.quantity

    return StockCheck(
        product_id=row["product_id"],
        name=row["name"],
        price=row["price"],
        size=wanted or size.strip(),
        quantity=quantity,
        status=status,
        sizes_in_stock=in_stock,
    )


# --- Server helpers (not given to the agent) ---------------------------------


def product_cards(product_ids: list[str]) -> list[ProductCard]:
    """Look up product cards for the ids the agent chose. Unknown ids are dropped."""
    ids = list(dict.fromkeys(product_ids))[:6]
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    with get_db() as conn:
        rows = conn.execute(
            f"""
            SELECT c.product_id, c.name, c.price, c.image_file_path,
                   COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            WHERE c.product_id IN ({placeholders})
            GROUP BY c.product_id
            """,
            ids,
        ).fetchall()
    by_id = {r["product_id"]: r for r in rows}
    return [
        ProductCard(
            product_id=r["product_id"],
            name=r["name"],
            price=r["price"],
            image_url=image_url(r["image_file_path"]),
            total_stock=r["total_stock"],
        )
        for pid in ids
        if (r := by_id.get(pid)) is not None
    ]


def page_listings(search: PageSearch) -> list[ProductListing]:
    """Run the agent's browse search for the Products page. Includes sold-out
    items (the card says so) and returns up to MAX_PAGE_RESULTS products."""
    rows = _search_rows(
        keyword=search.keyword, category=search.category, garment_type=search.garment_type,
        color=search.color, size=search.size, min_price=search.min_price,
        max_price=search.max_price, sort=search.sort,
    )
    return [
        ProductListing(
            product_id=r["product_id"],
            name=r["name"],
            category=r["category"],
            garment_type=r["garment_type"],
            description=r["description"],
            colors=r["colors"],
            price=r["price"],
            image_url=image_url(r["image_file_path"]),
            total_stock=r["total_stock"],
        )
        for r in rows[:MAX_PAGE_RESULTS]
    ]


# --- Tool guard: input checks, de-duplication, and the audit trail -----------

MAX_TEXT_ARG = 100  # Longest text a tool accepts (keyword, product name, ...)
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def _clean_args(kwargs: dict) -> dict:
    """Validate tool inputs from the model: trim and cap text, drop bad numbers."""
    clean = {}
    for k, v in kwargs.items():
        if isinstance(v, str):
            v = _CONTROL.sub("", v).strip()[:MAX_TEXT_ARG] or None
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            if not math.isfinite(v) or v < 0 or v > 10_000:
                v = None  # e.g. a negative or absurd price filter is ignored
        clean[k] = v
    return clean


def _summarize_args(kwargs: dict) -> str:
    parts = [f"{k}={v!r}" for k, v in kwargs.items() if v is not None and v != ""]
    return audit.redact(", ".join(parts) or "(no filters)", 200)


def _summarize_result(result) -> tuple[str, str]:
    """(outcome, short summary) for the audit trail. No full product dumps."""
    if isinstance(result, SearchResults):
        if result.total_including_sold_out == 0:
            alts = f"; {len(result.alternatives)} alternatives after relaxing {result.relaxed_filters}" if result.alternatives else ""
            return "no_match", f"0 matches{alts}"
        names = ", ".join(p.name for p in result.products[:3])
        return "ok", f"{result.total_including_sold_out} matches ({result.total_in_stock} in stock); first: {names}"
    if isinstance(result, ProductDetails):
        return "ok", f"{result.name}: ${result.price:g}, {result.total_stock} in stock, sizes in stock {result.sizes_in_stock}"
    if isinstance(result, StockCheck):
        return "ok", f"{result.name} size {result.size}: {result.status}, quantity {result.quantity}"
    if isinstance(result, LookupMiss):
        return "lookup_miss", f"{result.reason} for {result.query!r}; {len(result.candidates)} candidates"
    if isinstance(result, list):
        return "ok", f"{len(result)} similar products: " + ", ".join(getattr(p, "name", "?") for p in result[:3])
    return "ok", type(result).__name__


def audited(fn):
    """Wrap an agent tool: validate inputs, reuse identical calls within one
    answer instead of querying again, and record every call in the audit trail."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        kwargs = _clean_args(kwargs)
        run = audit.current_run.get()
        key = (fn.__name__, json.dumps(kwargs, sort_keys=True, default=str))
        base = {"event": "tool_call", "tool": fn.__name__, "arguments": _summarize_args(kwargs)}

        if run is not None and key in run["cache"]:
            result = run["cache"][key]
            outcome, summary = _summarize_result(result)
            audit.record({**base, "outcome": "duplicate_call_reused", "result": summary, "duration_ms": 0})
            return result

        started = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            audit.record({**base, "outcome": "error", "error": audit.redact(f"{type(e).__name__}: {e}"),
                          "duration_ms": round((time.perf_counter() - started) * 1000)})
            raise
        outcome, summary = _summarize_result(result)
        audit.record({**base, "outcome": outcome, "result": audit.redact(summary),
                      "duration_ms": round((time.perf_counter() - started) * 1000)})
        if run is not None:
            run["cache"][key] = result
            run["tool_calls"] += 1
        return result

    return wrapper


# Tools registered with the agent. These are the ONLY things the agent can do:
# read-only catalogue lookups. There are no order, payment, refund, account, or
# user-table tools, so the agent cannot perform or access any of those.
AGENT_TOOLS = [audited(t) for t in (search_products, get_product_details, check_stock, similar_products)]
