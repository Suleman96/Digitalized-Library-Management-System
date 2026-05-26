import gradio as gr
import os
from config import LANGUAGES, SEARCH_MODES, SORT_BY_OPTIONS, LOGO_PATH
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
  --link: #2563eb;
  --input-bg: #ffffff;
  --button-bg: #2563eb;
  --button-fg: #ffffff;
  --checkbox-border: #ccc;
}

[data-theme='dark'] {
  --bg: #111827;
  --fg: #f9fafb;
  --card-bg: #1f2937;
  --card-fg: #f9fafb;
  --subtle: #9ca3af;
  --link: #60a5fa;
  --input-bg: #1f2937;
  --button-bg: #374151;
  --button-fg: #f9fafb;
  --checkbox-border: #374151;
}

body {
  background: var(--bg);
  color: var(--fg);
  font-family: 'Segoe UI', Roboto, sans-serif;
  margin: 0;
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 2rem;
  background: var(--card-bg);
  border-bottom: 1px solid var(--subtle);
  box-shadow: 0 2px 4px rgba(0,0,0,0.08);
}

header .left {
  display: flex;
  align-items: center;
}

header img {
  height: 60px;
  margin-right: 1rem;
}

header h1 {
  font-size: 1.8rem;
  font-weight: bold;
  color: var(--fg);
}

header .right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  color: var(--subtle);
}

.switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 24px;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.4s;
  border-radius: 34px;
}
.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  transition: 0.4s;
  border-radius: 50%;
}
input:checked + .slider {
  background-color: var(--link);
}
input:checked + .slider:before {
  transform: translateX(26px);
}
</style>

<script>
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.querySelector(".switch input");
  const savedTheme = localStorage.getItem("theme") || "light";
  document.documentElement.setAttribute("data-theme", savedTheme);
  toggle.checked = savedTheme === "dark";

  toggle.addEventListener("change", function () {
    const theme = this.checked ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  });
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
    return manager.add_book(details)

with gr.Blocks(css=THEME_CSS, title="Iqraa Digital Library") as app:
    logo_web_path = f"/file/{LOGO_PATH.replace(os.sep, '/')}"
    gr.HTML(f"""
<header>
  <div class="left">
    <img src="{logo_web_path}" alt="DiploTech Logo">
    <h1>Iqraa Digital Library</h1>
  </div>
  <div class="right">
    <span>Dark Mode</span>
    <label class="switch">
      <input type="checkbox">
      <span class="slider"></span>
    </label>
  </div>
</header>
""")

    with gr.Tabs():
        with gr.TabItem("🔎 Recommend"):
            gr.Markdown("Enter your prompt and adjust filters below:")
            query = gr.Textbox(placeholder="e.g. books about horses…", label="Search Prompt")
            with gr.Row():
                language    = gr.Dropdown(list(LANGUAGES.keys()), value="Any", label="Language")
                search_mode = gr.Dropdown(SEARCH_MODES,      value="Both", label="Scope")
                sort_by     = gr.Dropdown(SORT_BY_OPTIONS,   value="Rating", label="Sort By")
            with gr.Row():
                local_n   = gr.Slider(1, 20, value=5, step=1, label="Local Results")
                external_n= gr.Slider(1, 20, value=5, step=1, label="External Results")
                min_rating= gr.Slider(0, 5,  value=0.0, step=0.5, label="Min. Avg Rating")
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
            thumbnail      = gr.Textbox(label="Thumbnail URL")
            description    = gr.Textbox(label="Description", lines=4)
            published_year = gr.Number(label="Published Year", value=2025, precision=0)
            average_rating = gr.Slider(0, 5, step=0.1, value=0.0, label="Average Rating")
            num_pages      = gr.Number(label="Num Pages", value=1, precision=0)
            ratings_count  = gr.Number(label="Ratings Count", value=0, precision=0)
            add_output     = gr.Textbox(interactive=False)
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
    app.launch()
