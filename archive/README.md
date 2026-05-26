# archive/

This directory holds **deprecated and superseded files** — kept for historical
reference only.  Do NOT import from or run any file in this directory.

| File | Original purpose | Superseded by |
|------|-----------------|---------------|
| `app_v1_dark_mode.py` | Early UI prototype with manual dark/light CSS | `app.py` |
| `app_v2_meeting_demo.py` | Demo shown at the DiploTech meeting | `app.py` |
| `app_v3_gradio.py` | Intermediate Gradio refactor | `app.py` |
| `book_manager_legacy.py` | Original manager (no CSV rebuild, no logging) | `manager.py` |
| `prepare_data_legacy.py` | One-off script to build initial FAISS index | `manager.py` auto-builds on startup |
| `testing_scratch.py` | Ad-hoc manual tests | `tests/` pytest suite |
| `testing_notebook.ipynb` | Exploration notebook | `tests/` pytest suite |
| `yt_code_reference.py` | YouTube tutorial TF-IDF approach | `recommender.py` (sentence-transformers) |
| `book_recommendation_notebook.ipynb` | Early notebook prototype | `recommender.py` |
| `gutenberg_metadata.py` | Gutenberg dataset scraper (unused) | Not used in current build |
| `kaggle_dataset_link.md` | Kaggle download link | `data/books.csv` (already downloaded) |
