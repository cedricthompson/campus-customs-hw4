"""Pydantic types for the chat API, the agent's output, and its tools."""

from typing import Literal

import re

from pydantic import BaseModel, Field, field_validator

MAX_MESSAGE_CHARS = 2000
MAX_HISTORY_TURNS = 20

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(value: str) -> str:
    """Strip invisible control characters and surrounding whitespace."""
    return _CONTROL_CHARS.sub("", value).strip()


# --- Chat API (website <-> FastAPI) ------------------------------------------


class ChatTurn(BaseModel):
    """One earlier message in the conversation, sent back by the website."""

    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_MESSAGE_CHARS * 2)

    _clean = field_validator("content")(classmethod(lambda cls, v: clean_text(v)))


class PageContext(BaseModel):
    """Where the shopper is on the site. Only the path and product id come from
    the browser; the server looks up the product's real details itself."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=200)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)

    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("Message is empty.")
        return v

    # Used for guests only. Logged-in customers' history is loaded from the database.
    history: list[ChatTurn] = Field(default_factory=list, max_length=MAX_HISTORY_TURNS)
    page: PageContext | None = None


class ProductCard(BaseModel):
    """A product shown under a chat reply. Built from the database, not the model."""

    product_id: str
    name: str
    price: float
    image_url: str
    total_stock: int


class ProductListing(BaseModel):
    """A product card on the Products page: same fields the site's ProductCard uses."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    colors: list[str]
    price: float
    image_url: str
    total_stock: int


class PageResults(BaseModel):
    """Chat search results for the website to show on the Products page."""

    label: str  # Heading, e.g. "Hoodies" or "Navy crewnecks under $60"
    query: str  # The shopper's message that produced these results
    products: list[ProductListing]


class ChatReply(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResults | None = None


class SavedChatMessage(BaseModel):
    """One message from a logged-in customer's saved history (GET /api/chat/history)."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str


# --- Agent dependencies --------------------------------------------------------


class CustomerInfo(BaseModel):
    """The logged-in customer, from the session. Never includes the password hash."""

    id: int
    name: str
    first_name: str | None
    email: str


# --- Agent output ------------------------------------------------------------


class PageSearch(BaseModel):
    """Filters for a browse-style search whose results fill the Products page.
    The server runs this search itself, so every product shown is real."""

    label: str = Field(
        description="Short heading for the results, e.g. 'Hoodies', 'Gray quarter-zips', "
        "'Navy crewnecks under $60', 'Sneakers'."
    )
    keyword: str | None = Field(default=None, description="Same meaning as in search_products.")
    category: str | None = Field(default=None, description="Same meaning as in search_products.")
    garment_type: str | None = Field(default=None, description="Same meaning as in search_products.")
    color: str | None = Field(default=None, description="Same meaning as in search_products.")
    size: str | None = Field(default=None, description="Same meaning as in search_products.")
    min_price: float | None = Field(default=None, description="Same meaning as in search_products.")
    max_price: float | None = Field(default=None, description="Same meaning as in search_products.")
    sort: Literal["price_low", "price_high", "name"] = Field(
        default="price_low", description="Same meaning as in search_products."
    )


class AgentOutput(BaseModel):
    """What the agent returns. It names products by id only; the server looks up
    their real name, price, image, and stock so the model can't invent them."""

    reply: str = Field(description="The message to show the shopper. Short and friendly.")
    product_ids: list[str] = Field(
        default_factory=list,
        description="product_id of each product to show as a card, best match first. "
        "Only ids returned by a tool in this conversation. Max 6. Empty if none.",
    )
    page_search: PageSearch | None = Field(
        default=None,
        description="Set when the shopper is browsing a category, type, color, or price range "
        "(e.g. 'what hoodies do you have?', 'show me gray crewnecks'), using the same filters "
        "you searched with. Leave null for questions about one specific product.",
    )

    @field_validator("reply")
    @classmethod
    def reply_not_blank(cls, v: str) -> str:
        v = clean_text(v)
        if not v:
            raise ValueError("reply must not be empty")
        return v[:2000]

    @field_validator("product_ids")
    @classmethod
    def dedupe_ids(cls, v: list[str]) -> list[str]:
        return list(dict.fromkeys(i.strip() for i in v if i.strip()))[:6]


# --- Tool results ------------------------------------------------------------
# Each tool returns only what the agent needs to answer; see output/harness.md.


class ProductSummary(BaseModel):
    """One search hit: enough to compare options, not the full description."""

    product_id: str
    name: str
    category: str
    garment_type: str
    colors: list[str]
    price: float
    total_stock: int
    sizes_in_stock: list[str]


class SearchResults(BaseModel):
    """search_products result: up to 12 products plus true totals, so the agent
    never has to guess how many matched."""

    total_in_stock: int = Field(description="How many matching products have stock.")
    total_including_sold_out: int = Field(
        description="How many products match at all; this is how many the Products page shows."
    )
    products: list[ProductSummary] = Field(description="Up to 12 of the matches, in the requested sort order.")
    alternatives: list[ProductSummary] = Field(
        default_factory=list,
        description="Only when nothing matched: real, in-stock products found by dropping some filters.",
    )
    relaxed_filters: list[str] = Field(
        default_factory=list,
        description="Which filters were dropped to find the alternatives, e.g. ['color'].",
    )


class SizeStock(BaseModel):
    size: str
    quantity: int
    sold_out: bool


class ProductDetails(BaseModel):
    """Full facts for one product: description, price, and stock in every size."""

    product_id: str
    name: str
    garment_type: str
    description: str
    colors: list[str]
    price: float
    stock_by_size: list[SizeStock]
    sizes_in_stock: list[str]
    total_stock: int


class StockCheck(BaseModel):
    """Answer to "do you have <product> in <size>?"."""

    product_id: str
    name: str
    price: float
    size: str
    quantity: int
    status: Literal["in_stock", "low_stock", "sold_out", "size_not_offered"]
    sizes_in_stock: list[str] = Field(
        description="Other sizes with stock, to suggest when this one is sold out."
    )


class ProductMatch(BaseModel):
    product_id: str
    name: str


class LookupMiss(BaseModel):
    """Returned when a product name or id didn't match exactly one product."""

    found: Literal[False] = False
    reason: Literal["not_found", "ambiguous"]
    query: str
    candidates: list[ProductMatch] = Field(
        description="Closest matches. Ask the shopper which one they mean, or say it wasn't found."
    )
