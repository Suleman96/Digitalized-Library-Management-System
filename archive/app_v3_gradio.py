import os
import re
import requests
import pickle
import faiss
import numpy as np
import torch
import gradio as gr
from sentence_transformers import SentenceTransformer

# === Configuration ===
with open("API.txt", "r") as f:
    key = f.read().strip()
os.environ["GOOGLE_API_KEY"] = key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

LANGUAGES = {
    "Any": "",
    "English": "en",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Portuguese": "pt",
    "Dutch": "nl",
    "Arabic": "ar",
    "Swedish": "sv",
    "Turkish": "tr",
    "Hindi": "hi",
}
SEARCH_MODES = ["Both", "Local Only", "External Only"]
SORT_BY_OPTIONS = ["Rating", "Similarity"]

# === Utility Functions ===
def clean_text(text: str) -> str:
    return re.sub(r"[^\x00-\x7F]+", " ", str(text or "")).strip()

# === Book Recommender ===
class BookRecommender:
    def __init__(self, index_path, metadata_path, api_key):
        # load FAISS index & metadata
        self.index = faiss.read_index(index_path)
        with open(metadata_path, "rb") as f:
            self.metadata = pickle.load(f)
        self.model = SentenceTransformer("all-MiniLM-L6-v2", device=DEVICE)
        self.api_key = api_key

    def embed(self, texts):
        embs = self.model.encode(texts, convert_to_numpy=True)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        return (embs / np.clip(norms, 1e-8, None)).astype(np.float32)

    def sanitize(self, raw, source):
        authors = raw.get("authors")
        if isinstance(authors, list):
            authors = ", ".join(authors)
        authors = clean_text(authors)
        thumb = raw.get("thumbnail") or raw.get("imageLinks", {}).get("thumbnail", "")
        info = raw.get("info_link") or raw.get("infoLink") or "#"
        return {
            "title": clean_text(raw.get("title")) or "Unknown Title",
            "authors": authors or "Unknown Author",
            "description": clean_text(raw.get("description")) or "No description available.",
            "thumbnail": thumb,
            "average_rating": float(raw.get("average_rating") or raw.get("averageRating", 0)),
            "ratings_count": int(raw.get("ratings_count") or raw.get("ratingsCount", 0)),
            "info_link": info,
            "language": (raw.get("language") or raw.get("languageCode") or "").lower() or "unknown",
            "source": source
        }

    def filter_by_rating(self, books, min_rating):
        return [b for b in books if b["average_rating"] >= min_rating]

    def search_local(self, query, lang_code, pool_k):
        q_emb = self.embed([query])
        D, I = self.index.search(q_emb, pool_k)
        out = []
        for sim, idx in zip(D[0], I[0]):
            if idx < 0: continue
            raw = self.metadata[idx]
            book = self.sanitize(raw, "Local")
            if lang_code and book["language"] not in (lang_code, "unknown"):
                continue
            book["similarity"] = float(sim)
            out.append(book)
        return out

    def get_google_books(self, query, lang_code, pool_k):
        items = []
        start = 0
        # Google Books API maxResults per request = 40
        while len(items) < pool_k:
            batch = min(pool_k - len(items), 40)
            params = {
                "q": query,
                "maxResults": batch,
                "startIndex": start,
                "orderBy": "relevance",
                "key": self.api_key
            }
            if lang_code:
                params["langRestrict"] = lang_code
            try:
                r = requests.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=10)
                r.raise_for_status()
                page = r.json().get("items", [])
            except Exception:
                break
            if not page:
                break
            items.extend(page)
            if len(page) < batch:
                break
            start += len(page)
        # sanitize
        books = []
        for item in items:
            info = item.get("volumeInfo", {})
            books.append(self.sanitize(info, "External"))
        return books

    def search_external(self, query, lang_code, pool_k):
        raw = self.get_google_books(query, lang_code, pool_k)
        if lang_code:
            raw = [b for b in raw if b["language"] == lang_code]
        if not raw:
            return []
        texts = [f"{b['title']} {b['description']}" for b in raw]
        embs = self.embed(texts)
        q_emb = self.embed([query])[0]
        sims = embs.dot(q_emb)
        for b, s in zip(raw, sims):
            b["similarity"] = float(s)
        return sorted(raw, key=lambda b: b["similarity"], reverse=True)

    def recommend(self, prompt, language, local_n, external_n, min_rating, search_mode, sort_by):
        lang_code = LANGUAGES.get(language, "")
        locals, externals = [], []

        # Local
        if search_mode in ("Both", "Local Only") and local_n > 0:
            pool = self.search_local(prompt, lang_code, local_n * 5)
            good = self.filter_by_rating(pool, min_rating)
            locals = good[:local_n]
            if len(locals) < local_n:
                add = [b for b in pool if b not in locals]
                locals += add[: local_n - len(locals)]

        # External
        if search_mode in ("Both", "External Only") and external_n > 0:
            pool = self.search_external(prompt, lang_code, external_n * 5)
            good = self.filter_by_rating(pool, min_rating)
            externals = good[:external_n]
            if len(externals) < external_n:
                add = [b for b in pool if b not in externals]
                externals += add[: external_n - len(externals)]

        # Sort
        if sort_by == "Rating":
            keyfn = lambda b: (b["average_rating"], b["similarity"])
        else:
            keyfn = lambda b: b["similarity"]
        locals = sorted(locals, key=keyfn, reverse=True)
        externals = sorted(externals, key=keyfn, reverse=True)

        return locals, externals

    def create_card(self, b):
        return f"""
<div style="background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);overflow:hidden;display:flex;flex-direction:column;">
  <img src="{b['thumbnail']}" style="width:100%;aspect-ratio:2/3;object-fit:cover;">
  <div style="padding:1rem;flex:1;display:flex;flex-direction:column;">
    <h3 style="margin:0 0 0.5rem;font-size:1.1rem;">{b['title']}</h3>
    <p style="margin:0;font-size:0.9rem;color:#555;">{b['authors']}</p>
    <p style="margin:0.5rem 0;font-size:0.9rem;color:#555;">⭐ {b['average_rating']} ({b['ratings_count']} reviews)</p>
    <p style="flex:1;margin:0 0 0.75rem;font-size:0.9rem;color:#666;overflow:hidden;max-height:4.5rem;">{b['description']}</p>
    <a href="{b['info_link']}" target="_blank" style="text-decoration:none;color:#4f46e5;font-weight:500;">More Info</a>
  </div>
</div>
"""

    def format_books(self, locals, externals):
        html = "<div style='display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:1rem;'>"
        html += "<h2 style='width:100%;grid-column:1/-1;'>📚 Local Recommendations</h2>"
        html += "".join(self.create_card(b) for b in locals) or "<p style='grid-column:1/-1;'>No local results</p>"
        html += "<h2 style='width:100%;grid-column:1/-1;'>🌐 External Recommendations</h2>"
        html += "".join(self.create_card(b) for b in externals) or "<p style='grid-column:1/-1;'>No external results</p>"
        html += "</div>"
        return html

# === Initialize & UI ===
recommender = BookRecommender("book_index.faiss", "books_metadata.pkl", GOOGLE_API_KEY)

with gr.Blocks() as app:
    gr.Markdown("# 📚 Book Recommendation System")
    with gr.Accordion("Search Options", open=True):
        query = gr.Textbox(label="Prompt")
        language = gr.Dropdown(list(LANGUAGES.keys()), value="Any", label="Language")
        search_mode = gr.Dropdown(SEARCH_MODES, value="Both", label="Search Mode")
        sort_by = gr.Dropdown(SORT_BY_OPTIONS, value="Rating", label="Sort By")
        local_count = gr.Slider(0, 20, value=5, label="Max Local Results")
        external_count = gr.Slider(0, 50, value=10, label="Max External Results")
        min_rating = gr.Slider(0, 5, value=0, step=0.5, label="Min Rating")
    btn = gr.Button("🔍 Recommend")
    out = gr.HTML()

    btn.click(
        fn=lambda q, lg, ln, en, mr, mode, sb: recommender.format_books(
            *recommender.recommend(q, lg, ln, en, mr, mode, sb)
        ),
        inputs=[query, language, local_count, external_count, min_rating, search_mode, sort_by],
        outputs=out
    )

if __name__ == "__main__":
    app.launch(share=True)
