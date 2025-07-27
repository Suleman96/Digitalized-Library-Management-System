import gradio as gr
import os
from config import LANGUAGES, SEARCH_MODES, SORT_BY_OPTIONS
from manager import DynamicBookManager
from recommender import BookRecommender

manager = DynamicBookManager()
reco = BookRecommender()

CATEGORIES = [
    "American Fiction", "Fiction", "Romance", "Fantasy", "Adventure",
    "Science Fiction", "Mystery", "Thriller", "Non-Fiction", "Biography",
    "History", "Science", "Poetry", "Young Adult", "Children", "Self-Help",
    "Business", "Philosophy", "Health", "Travel", "Humor"
]

THEME_CSS = """
<style>
:root {
  --bg: #ffffff;
  --fg: #1f2937;
  --card-bg: #ffffff;
  --card-fg: #1f2937;
  --subtle: #6b7280;
  --link: #007BFF;
  --button-bg: #FFA500;
  --button-fg: #ffffff;
  --input-bg: #ffffff;
  --checkbox-border: #ccc;
}

body {
  background-color: #ffffff !important;
  color: var(--fg);
  font-family: 'Segoe UI', Roboto, sans-serif;
  margin: 0;
  overflow-x: hidden;
}

input, textarea, select {
  background-color: var(--input-bg) !important;
  color: var(--fg) !important;
  border: 1px solid var(--checkbox-border);
  border-radius: 6px;
  padding: 8px;
}
input[type=checkbox] {
  accent-color: var(--link);
  width: 16px;
  height: 16px;
  margin-right: 8px;
}
button {
  background-color: var(--button-bg) !important;
  color: var(--button-fg) !important;
  border-radius: 6px !important;
  padding: 0.5rem 1rem;
  font-weight: bold;
  border: none;
}

header {
  width: 100%;
  background: linear-gradient(to right, #34425A, #182c3f);
  color: white !important;
  padding: 1rem 0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.header-inner {
  max-width: 1200px;
  margin: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.header-left img {
  height: 60px;
  width: 60px;
  object-fit: contain;
  filter: brightness(0) invert(1);
}
.header-left .title-container {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}
.header-left .title-container h1,
.header-left .title-container h2 {
  margin: 0;
  color: white;
  font-size: 1.6rem;
  font-weight: 600;
  font-family: 'Segoe UI', sans-serif;
}
.header-left .title-container h2 {
  font-size: 1.2rem;
  font-weight: 400;
  font-family: 'Segoe UI', Tahoma, sans-serif;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}
.header-right .icon {
  font-size: 1.6rem;
  color: white !important;
  filter: brightness(0) invert(1) !important;
  cursor: pointer;
}
</style>

<script>
document.addEventListener("DOMContentLoaded", function () {
  const savedTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
});
</script>
"""

def add_book_ui(isbn13, isbn10, title, subtitle, authors, categories,
                thumbnail, description, published_year,
                average_rating, num_pages, ratings_count):
    if not (isbn13.isdigit() and len(isbn13) == 13):
        return "❌ ISBN13 must be exactly 13 digits."
    if not (isbn10.isdigit() and len(isbn10) == 10):
        return "❌ ISBN10 must be exactly 10 digits."
    if not title.strip():
        return "❌ Title cannot be empty."
    if not categories:
        return "❌ Please select at least one category."
    try:
        y = int(published_year)
        if y < 1000 or y > 9999:
            raise ValueError()
    except:
        return "❌ Published Year must be a four-digit year."
    try:
        r = float(average_rating)
        if r < 0 or r > 5:
            raise ValueError()
    except:
        return "❌ Average Rating must be between 0 and 5."
    try:
        p = int(num_pages)
        if p < 1:
            raise ValueError()
    except:
        return "❌ Num Pages must be a positive integer."
    try:
        rc = int(ratings_count)
        if rc < 0:
            raise ValueError()
    except:
        return "❌ Ratings Count must be a non-negative integer."

    details = {
        "isbn13": isbn13,
        "isbn10": isbn10,
        "title": title.strip(),
        "subtitle": subtitle.strip(),
        "authors": authors.strip(),
        "categories": ",".join(categories),
        "thumbnail": thumbnail.strip(),
        "description": description.strip(),
        "published_year": y,
        "average_rating": r,
        "num_pages": p,
        "ratings_count": rc
    }

    result = manager.add_book(details)

    if thumbnail.strip().startswith("file/") or thumbnail.strip().startswith("http"):
        return f"<p>{result}</p><img src='{thumbnail.strip()}' style='max-height:200px;margin-top:10px;border:1px solid #ccc'>"
    else:
        return result

with gr.Blocks(css=THEME_CSS, title="Iqraa Digital Library system") as app:
    gr.HTML(f"""
<header>
  <div class="header-inner">
    <div class="header-left">
      <img src="https://diplotech-solutions.com/assets/img/Diplotech_Logo_2.png" alt="DPTech" style="filter:none !important">
      <div class="title-container">
        <h1>Iqra's Digital Library and Book Recommender</h1>
        <h2>مكتبة إقرأ الرقمية وموصي الكتب</h2>
      </div>
    </div>
    <div class="header-right">
      <span class="icon">👤</span>
      <span class="icon">🔔</span>
    </div>
  </div>
</header>
""")

    with gr.Tabs():
        with gr.TabItem("🔎 Recommend"):
            gr.Markdown("Enter your prompt and adjust filters below:")
            query = gr.Textbox(placeholder="e.g. books about.....", label="Search Prompt")
            with gr.Row():
                language    = gr.Dropdown(list(LANGUAGES.keys()), value="Any", label="Language")
                search_mode = gr.Dropdown(SEARCH_MODES,      value="Both", label="Scope")
                sort_by     = gr.Dropdown(SORT_BY_OPTIONS,   value="Rating", label="Sort By")
            with gr.Row():
                local_n    = gr.Slider(1, 20, value=5, step=1, label="Local Results")
                external_n = gr.Slider(1, 20, value=5, step=1, label="External Results")
                min_rating = gr.Slider(0, 5,  value=0.0, step=0.5, label="Min. Avg Rating")
            btn    = gr.Button("🔍 Get Recommendations", variant="primary")
            output = gr.HTML()
            btn.click(fn=lambda *args: reco.format_books(*reco.recommend(*args)),
                      inputs=[query, language, local_n, external_n, min_rating, search_mode, sort_by],
                      outputs=output)

        with gr.TabItem("📥 Add Book"):
            gr.Markdown("Fill in book details to add to your library.")
            isbn13         = gr.Textbox(label="ISBN13 (13 digits)")
            isbn10         = gr.Textbox(label="ISBN10 (10 digits)")
            title          = gr.Textbox(label="Title")
            subtitle       = gr.Textbox(label="Subtitle")
            authors        = gr.Textbox(label="Authors")
            categories     = gr.CheckboxGroup(CATEGORIES, label="Categories")
            thumbnail      = gr.Textbox(label="Thumbnail URL or file/image path")
            description    = gr.Textbox(label="Description", lines=4)
            published_year = gr.Number(label="Published Year", value=2025, precision=0)
            average_rating = gr.Slider(0, 5, step=0.1, value=0.0, label="Average Rating")
            num_pages      = gr.Number(label="Num Pages", value=1, precision=0)
            ratings_count  = gr.Number(label="Ratings Count", value=0, precision=0)
            add_output     = gr.HTML()
            gr.Button("➕ Add Book", variant="secondary") \
              .click(fn=add_book_ui,
                     inputs=[isbn13, isbn10, title, subtitle, authors, categories,
                             thumbnail, description, published_year,
                             average_rating, num_pages, ratings_count],
                     outputs=add_output)

        with gr.TabItem("🗑️ Remove Book"):
            gr.Markdown("Remove a book by its exact title (case-insensitive).")
            rem     = gr.Textbox(label="Book Title to Remove")
            rem_out = gr.Textbox(interactive=False)
            gr.Button("✂️ Remove Book", variant="danger") \
              .click(fn=manager.remove_book, inputs=rem, outputs=rem_out)

    gr.Markdown("<hr/>Built by DiploTech Solutions")

if __name__ == "__main__":
    app.launch(allowed_paths=["."])

