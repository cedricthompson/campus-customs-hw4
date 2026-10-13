"""Campus Customs API: product catalogue, product images, accounts, and chat.

Run from inside backend/:  uvicorn main:app --reload --port 8000
"""

import asyncio
import json
import logging
import os
import secrets
import sqlite3
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Settings live in hw4/.env (next to .env.example); backend/.env also works.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic_ai.exceptions import ModelHTTPError  # noqa: E402
from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

import history  # noqa: E402
from agent import MODEL_NAME, AgentDeps, ask  # noqa: E402
from auth import current_user  # noqa: E402
from auth import router as auth_router  # noqa: E402
from db import CATEGORIES, IMAGES_DIR, category_for, get_db, image_url, size_sort_key  # noqa: E402
from models import (  # noqa: E402
    ChatReply,
    ChatRequest,
    PageContext,
    PageResults,
    ProductDetails,
    SavedChatMessage,
)
from tools import get_product_details, page_listings, product_cards  # noqa: E402

logger = logging.getLogger("campus_customs")

CHAT_ERROR = "Our assistant is having trouble right now. Please try again."
CHAT_TIMEOUT = "That took longer than expected. Please try again."
CHAT_BUSY = "I'm still working on your last message. One moment!"
CHAT_TOO_FAST = "You're sending messages very quickly. Please wait a few seconds and try again."
CHAT_INVALID = "Please type a message (up to 2,000 characters)."
GENERIC_ERROR = "Something went wrong on our end. Please try again."

MAX_CHATS_PER_MINUTE = 12
FILTERED_REPLY = "I can't help with that, but I'd love to help you find some Yale gear! What are you looking for?"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Migration on startup: index for loading one customer's chat history (Problem 9).
    # Startup never touches the audit trail.
    with get_db(write=True) as conn:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")
    yield


app = FastAPI(title="Campus Customs API", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def friendly_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Don't show shoppers Pydantic's technical error list.
    detail = CHAT_INVALID if request.url.path == "/api/chat" else "Please check the form and try again."
    return JSONResponse(status_code=400, content={"detail": detail})


@app.exception_handler(Exception)
async def friendly_server_error(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": GENERIC_ERROR})

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Login state lives in a signed, HTTP-only cookie holding just the user id.
# Set SESSION_SECRET in backend/.env to keep people logged in across restarts;
# otherwise a random key is used and everyone is logged out on restart.
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET") or secrets.token_urlsafe(32),
    session_cookie="cc_session",
    max_age=7 * 24 * 60 * 60,
    same_site="lax",
)

app.include_router(auth_router)

# Only the products folder is public; the database next to it is not.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


def product_from_row(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": image_url(row["image_file_path"]),
        "price": row["price"],
        "category": category_for(row["garment_type"]),
    }


@app.get("/api/categories")
def list_categories() -> list[str]:
    return CATEGORIES


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": MODEL_NAME}


@app.get("/api/products")
def list_products() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock
            FROM catalogue c LEFT JOIN inventory i ON i.product_id = c.product_id
            GROUP BY c.product_id
            ORDER BY c.name
            """
        ).fetchall()
    return [{**product_from_row(r), "total_stock": r["total_stock"]} for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str) -> dict:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    inventory = sorted(
        ({"size": s["size"], "quantity": s["quantity"]} for s in stock),
        key=lambda s: size_sort_key(s["size"]),
    )
    return {
        **product_from_row(row),
        "inventory": inventory,
        "total_stock": sum(s["quantity"] for s in inventory),
    }


def viewing_product(page: PageContext | None) -> ProductDetails | None:
    """The product on the shopper's current page, looked up in the catalogue by exact id.
    Only the id comes from the browser, so the agent never sees made-up details."""
    if page is None or not page.product_id:
        return None
    details = get_product_details(page.product_id)
    if isinstance(details, ProductDetails) and details.product_id == page.product_id:
        return details
    return None


@app.get("/api/chat/history")
def chat_history(request: Request) -> list[SavedChatMessage]:
    """The logged-in customer's own saved messages. The user id comes from the
    session cookie, never from the request, so nobody can read another's chat."""
    customer = current_user(request)
    if customer is None:
        raise HTTPException(status_code=401, detail="Log in to see your saved chat.")
    return history.load_for_page(customer.id)


# One chat request at a time per shopper, and a per-minute cap (in memory).
_chats_in_flight: set[str] = set()
_recent_chats: dict[str, deque[float]] = defaultdict(deque)


def chat_session_key(request: Request, customer_id: int | None) -> str:
    """Logged-in customers are keyed by id; guests get a random id in their session cookie."""
    if customer_id is not None:
        return f"user:{customer_id}"
    if "chat_guest_id" not in request.session:
        request.session["chat_guest_id"] = secrets.token_urlsafe(12)
    return f"guest:{request.session['chat_guest_id']}"


def _too_many_recent(key: str) -> bool:
    now = time.monotonic()
    recent = _recent_chats[key]
    while recent and now - recent[0] > 60:
        recent.popleft()
    if len(recent) >= MAX_CHATS_PER_MINUTE:
        return True
    recent.append(now)
    return False


@app.post("/api/chat")
async def chat(body: ChatRequest, request: Request) -> ChatReply:
    customer = current_user(request)
    key = chat_session_key(request, customer.id if customer else None)
    if key in _chats_in_flight:
        raise HTTPException(status_code=409, detail=CHAT_BUSY)
    if _too_many_recent(key):
        raise HTTPException(status_code=429, detail=CHAT_TOO_FAST)
    _chats_in_flight.add(key)
    try:
        return await _answer(body, customer)
    finally:
        _chats_in_flight.discard(key)


async def _answer(body: ChatRequest, customer) -> ChatReply:
    # Logged in: history comes from the database (the browser's copy is ignored).
    # Guest: use the turns the browser sent; nothing is saved.
    past = history.load_for_agent(customer.id) if customer else body.history
    deps = AgentDeps(customer=customer, page=body.page, viewing_product=viewing_product(body.page))

    try:
        output = await ask(body.message, past, deps)
    except asyncio.TimeoutError:
        logger.warning("Chat agent timed out")
        raise HTTPException(status_code=504, detail=CHAT_TIMEOUT)
    except ModelHTTPError as e:
        if isinstance(e.body, dict) and e.body.get("code") == "content_filter":
            # The model provider's safety filter blocked the message (often a jailbreak attempt).
            reply = ChatReply(reply=FILTERED_REPLY)
            if customer:
                history.save_exchange(customer.id, body.message, reply.reply, [])
            return reply
        logger.exception("Chat agent failed")
        raise HTTPException(status_code=502, detail=CHAT_ERROR)
    except Exception:
        logger.exception("Chat agent failed")
        raise HTTPException(status_code=502, detail=CHAT_ERROR)

    # Cards come from the database, so names, prices, and images are always real.
    cards = product_cards(output.product_ids)
    page_results = None
    if output.page_search is not None:
        # Browse search: the server runs the agent's filters itself and sends every
        # match, so the Products page can show them as regular product cards.
        page_results = PageResults(
            label=output.page_search.label,
            query=body.message,
            products=page_listings(output.page_search),
        )

    if customer:
        history.save_exchange(customer.id, body.message, output.reply, cards)

    return ChatReply(reply=output.reply, products=cards, page_results=page_results)
