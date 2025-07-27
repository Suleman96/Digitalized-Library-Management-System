# recommender.py

"""
BookRecommender:
- Loads FAISS index + metadata pickle
- Embeds user prompt
- Searches local + external
- Filters & sorts
- Renders HTML cards
"""

import pickle
import requests
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from config import INDEX_PATH, META_PATH, GOOGLE_API_KEY, LANGUAGES

import torch
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class BookRecommender:
    """Provides semantic & API-backed book recommendations with formatted cards."""

    def __init__(self):
        self.index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "rb") as f:
            self.metadata = pickle.load(f)
        self.model   = SentenceTransformer("all-MiniLM-L6-v2", device=DEVICE)
        self.api_key = GOOGLE_API_KEY

    def embed(self, texts):
        embs = self.model.encode(texts, convert_to_numpy=True)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        return (embs / np.clip(norms, 1e-8, None)).astype(np.float32)

    def sanitize(self, raw: dict, source: str) -> dict:
        def clean(x): return (x or "").strip()
        auth = raw.get("authors") or raw.get("authors_list") or ""
        if isinstance(auth, list): auth = ", ".join(auth)
        return {
            "title":          clean(raw.get("title")),
            "authors":        clean(auth),
            "description":    clean(raw.get("description")),
            "thumbnail":      clean(raw.get("thumbnail") 
                                   or raw.get("imageLinks",{}).get("thumbnail","")),
            "average_rating": float(raw.get("average_rating") 
                                    or raw.get("averageRating") or 0),
            "ratings_count":  int(raw.get("ratings_count") 
                                  or raw.get("ratingsCount") or 0),
            "info_link":      raw.get("info_link") 
                               or raw.get("infoLink") or "#",
            "language":       clean(raw.get("language")).lower(),
            "source":         source,
        }

    def _search_local(self, query, lang_code, pool_k):
        q_emb = self.embed([query])
        D, I  = self.index.search(q_emb, pool_k)
        results = []
        for sim, idx in zip(D[0], I[0]):
            if idx < 0: continue
            b = self.sanitize(self.metadata[idx], "Local")
            if lang_code and b["language"] != lang_code:
                continue
            b["similarity"] = float(sim)
            results.append(b)
        return results

    def _search_external(self, query, lang_code, pool_k):
        items, start = [], 0
        while len(items) < pool_k:
            batch = min(40, pool_k - len(items))
            params = {
                "q":          query,
                "maxResults": batch,
                "startIndex": start,
                "key":        self.api_key,
                "orderBy":    "relevance",
            }
            if lang_code:
                params["langRestrict"] = lang_code
            try:
                res = requests.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params=params, timeout=5
                ).json()
            except Exception:
                break
            batch_items = res.get("items", [])
            if not batch_items: break
            items += batch_items
            start += len(batch_items)
            if len(batch_items) < batch: break

        clean_raw = [
            self.sanitize(v.get("volumeInfo", {}), "External")
            for v in items
        ]
        texts = [b["title"] + ". " + b["description"] for b in clean_raw]
        if texts:
            embs  = self.embed(texts)
            q_emb = self.embed([query])[0]
            sims  = embs.dot(q_emb)
            for b, s in zip(clean_raw, sims):
                b["similarity"] = float(s)
        else:
            for b in clean_raw:
                b["similarity"] = 0.0

        return sorted(clean_raw, key=lambda x: x["similarity"], reverse=True)

    def recommend(
        self, prompt, language, local_n, external_n,
        min_rating, search_mode, sort_by
    ):
        lang_code = LANGUAGES.get(language, "")
        locals, externals = [], []

        if search_mode in ("Both","Local Only") and local_n>0:
            pool = self._search_local(prompt, lang_code, local_n*5)
            high = [b for b in pool if b["average_rating"]>=min_rating]
            locals = (high[:local_n]
                      + pool[:max(0, local_n-len(high))])

        if search_mode in ("Both","External Only") and external_n>0:
            pool = self._search_external(prompt, lang_code, external_n*5)
            high = [b for b in pool if b["average_rating"]>=min_rating]
            externals = (high[:external_n]
                         + pool[:max(0, external_n-len(high))])

        keyfn = (lambda b: (b["average_rating"], b["similarity"])) \
                if sort_by=="Rating" else (lambda b: b["similarity"])
        locals    = sorted(locals,    key=keyfn, reverse=True)
        externals = sorted(externals, key=keyfn, reverse=True)
        return locals, externals

    def create_card(self, b: dict) -> str:
        return f"""
<div style="
  background: var(--card-bg);
  color: var(--card-fg);
  border-radius:8px;
  box-shadow:0 2px 8px rgba(0,0,0,0.1);
  overflow:hidden;
  display:flex;flex-direction:column;
">
  <img src="{b['thumbnail']}" style="
    width:100%;aspect-ratio:2/3;object-fit:cover;
  "/>
  <div style="padding:1rem;flex:1;display:flex;flex-direction:column;">
    <h3 style="margin:0 0 .5rem;font-size:1.1rem;">
      {b['title']}
    </h3>
    <p style="margin:0;font-size:.9rem;color:var(--subtle);">
      {b['authors']}
    </p>
    <p style="margin:.5rem 0;font-size:.9rem;color:var(--subtle);">
      ⭐ {b['average_rating']} ({b['ratings_count']})
    </p>
    <p style="
      flex:1;margin:0 0 .75rem;
      font-size:.9rem;color:var(--subtle);
      overflow:hidden;max-height:4.5rem;
    ">
      {b['description']}
    </p>
    <a href="{b['info_link']}" target="_blank" style="
      text-decoration:none;color:var(--link);font-weight:500;
    ">
      More Info →
    </a>
  </div>
</div>"""

    def format_books(self, locals, externals) -> str:
        html = [
            '<div style="display:grid;'
            'grid-template-columns:repeat(auto-fill,minmax(240px,1fr));'
            'gap:1rem;">',
            '<h2 style="grid-column:1/-1;">📚 Local Recommendations</h2>'
        ]
        html += [self.create_card(b) for b in locals] or \
                ['<p style="grid-column:1/-1;">No local results.</p>']
        html.append('<h2 style="grid-column:1/-1;">🌐 External Recommendations</h2>')
        html += [self.create_card(b) for b in externals] or \
                ['<p style="grid-column:1/-1;">No external results.</p>']
        html.append("</div>")
        return "\n".join(html)
