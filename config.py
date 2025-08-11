# config.py

"""
Centralized configuration for:
- file paths
- API keys
- UI option lists
- language mappings
"""
import os

# File paths

DATA_DIR    = "data/Kaggle_7k_books"
CSV_PATH    = r"data/Kaggle_7k_books/books.csv"
INDEX_PATH  = "book_index.faiss"
META_PATH   = "books_metadata.pkl"

LOGO_PATH = r'static/logo.png'
#LOGO_PATH = 'static/logo.png'
#  External API Keys

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY and os.path.exists("API.txt"):
    with open("API.txt", "r") as f:
        GOOGLE_API_KEY = f.read().strip()
if not GOOGLE_API_KEY:
    raise RuntimeError("Google Books API key not found: set GOOGLE_API_KEY or create API.txt")

# User-Facing Options

LANGUAGES = {
    "Any":        "",
    "English":    "en",
    "German":     "de",
    "French":     "fr",
    "Spanish":    "es",
    "Italian":    "it",
    "Chinese":    "zh",
    "Japanese":   "ja",
    "Korean":     "ko",
    "Russian":    "ru",
    "Portuguese": "pt",
    "Dutch":      "nl",
    "Arabic":     "ar",
    "Swedish":    "sv",
    "Turkish":    "tr",
    "Hindi":      "hi",
}

SEARCH_MODES = [
    "Both",         # Local + External
    "Local Only",
    "External Only",
]

SORT_BY_OPTIONS = [
    "Rating",       # highest average_rating first
    "Similarity",   # highest semantic similarity first
]
