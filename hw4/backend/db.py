"""SQLite connection helpers for data/campus_customs.db."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]


# Shopper-facing categories, derived from the catalogue's 22 garment_type spellings.
# Order matters: the first rule whose words appear in garment_type wins.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Hoodies", ("hood",)),
    ("Quarter-zips", ("quarter-zip",)),
    ("Jackets & fleece", ("jacket", "fleece")),
    ("T-shirts", ("t-shirt",)),
    ("Long-sleeve shirts", ("long-sleeve performance shirt",)),
    ("Crewnecks & sweatshirts", ("crewneck", "sweatshirt", "mockneck")),
]
CATEGORIES = [name for name, _ in CATEGORY_RULES]


def category_for(garment_type: str) -> str:
    g = garment_type.lower()
    for name, words in CATEGORY_RULES:
        if any(w in g for w in words):
            return name
    return "Other"


@contextmanager
def get_db(write: bool = False) -> Iterator[sqlite3.Connection]:
    """Open a connection for one `with` block: commit on success, roll back on error,
    and always close it (plain `with sqlite3.connect()` commits but leaves it open)."""
    # Read-only unless the caller needs to write (e.g. creating an account).
    mode = "rw" if write else "ro"
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        if write:
            conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def image_url(image_file_path: str) -> str:
    # DB stores "products/<file>.jpg"; main.py serves that folder at /images.
    return f"/images/{Path(image_file_path).name}"


def size_sort_key(size: str) -> int:
    return SIZE_ORDER.index(size) if size in SIZE_ORDER else len(SIZE_ORDER)
