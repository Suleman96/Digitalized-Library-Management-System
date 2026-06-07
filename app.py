# =============================================================================
# app.py — Iqra Digital Library v2
# =============================================================================
# Entry point.  Run with:
#
#   python app.py
#
# New in v2
# ---------
#   • AI Settings panel — Claude / OpenAI / Gemini / Ollama toggle
#   • 🤖 AI Librarian  — LangGraph ReAct conversational agent
#   • 📊 Analytics     — Rating histogram, category bar, year trend
#   • 📌 Reading List  — JSON-backed bookmarks with PDF export
#   • Hybrid Search    — Knowledge Graph + FAISS (author/category/semantic edges)
#   • Enhanced Recommend — book selector, Save / Similar / Explain / PDF
# =============================================================================

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

# Matplotlib must set its backend before pyplot is imported
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import html as html_mod
import gradio as gr
import gradio_client.utils as gradio_client_utils
import pandas as pd

from config import settings
from manager import DynamicBookManager
from recommender import BookRecommender
from reading_list import ReadingList
from exporter import export_books_pdf
from hybrid_retriever import HybridRetriever
from rag_pipeline import RAGPipeline
from llm_provider import llm, PROVIDER_MODELS
from agent import LibraryAgent

# Workaround for gradio_client bug in newer Gradio versions where a JSON schema
# may be represented as a boolean (True/False). This otherwise crashes API info
# generation when Gradio tries to introspect the interface.
try:
    _original_get_type = gradio_client_utils.get_type

    def _safe_get_type(schema):
        if isinstance(schema, bool):
            return "any"
        return _original_get_type(schema)

    gradio_client_utils.get_type = _safe_get_type
except Exception:
    pass

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Back-end singletons
# ---------------------------------------------------------------------------
manager          = DynamicBookManager()
reco             = BookRecommender()
reading_list_mgr = ReadingList()
hybrid_ret       = HybridRetriever()
hybrid_ret.build(embed_fn=reco._embed)        # reuse reco's loaded model
rag_pipeline     = RAGPipeline(hybrid_ret, llm)
agent_mgr        = LibraryAgent(hybrid_ret, reco, reading_list_mgr, llm)

# Auto-connect LLM if LLM_PROVIDER / LLM_MODEL are set in the environment
_auto_provider = os.getenv("LLM_PROVIDER", "").strip().lower()
_auto_model    = os.getenv("LLM_MODEL", "").strip()
if _auto_provider and _auto_model:
    _status = llm.configure(_auto_provider, _auto_model)
    logger.info("Auto-connect LLM: %s", _status)
    if llm.is_enabled:
        agent_mgr.build()
        logger.info("Auto-connect: LibraryAgent built.")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BROWSE_PAGE_SIZE = 12

_CATEGORIES: list[str] = [
    "Adventure",       "American Fiction", "Biography",
    "Business",        "Children",         "Fantasy",
    "Fiction",         "Health",           "History",
    "Horror",          "Humor",            "Mystery",
    "Non-Fiction",     "Philosophy",       "Poetry",
    "Romance",         "Science",          "Science Fiction",
    "Self-Help",       "Thriller",         "Travel",
    "Young Adult",
]

# ---------------------------------------------------------------------------
# Gradio theme (handles component-level colours; dark/light via `.dark` class)
# ---------------------------------------------------------------------------
_theme = gr.themes.Base(
    primary_hue=gr.themes.colors.emerald,
    secondary_hue=gr.themes.colors.slate,
    neutral_hue=gr.themes.colors.zinc,
    font=[gr.themes.GoogleFont("Plus Jakarta Sans"), "ui-sans-serif", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "ui-monospace", "monospace"],
    spacing_size=gr.themes.sizes.spacing_md,
    radius_size=gr.themes.sizes.radius_lg,
).set(
    # ── dark token overrides ───────────────────────────────────────────────
    body_background_fill_dark="#050912",
    body_text_color_dark="#E8F0FF",
    body_text_color_subdued_dark="#7A93B8",
    background_fill_primary_dark="#050912",
    background_fill_secondary_dark="#0C1221",
    block_background_fill_dark="#0C1221",
    block_border_color_dark="#1C2E45",
    block_border_width_dark="1px",
    block_label_background_fill_dark="#0C1221",
    block_label_text_color_dark="#7A93B8",
    block_title_text_color_dark="#E8F0FF",
    border_color_primary_dark="#1C2E45",
    border_color_accent_dark="#4F8EF7",
    input_background_fill_dark="#111927",
    input_border_color_dark="#1C2E45",
    input_border_color_focus_dark="#4F8EF7",
    input_shadow_focus_dark="0 0 0 3px rgba(79,142,247,.16)",
    accordion_text_color_dark="#7A93B8",
    table_border_color_dark="#1C2E45",
    table_even_background_fill_dark="#111927",
    table_odd_background_fill_dark="#0C1221",
    table_row_focus_dark="rgba(79,142,247,.07)",
    checkbox_background_color_dark="#111927",
    checkbox_border_color_dark="#1C2E45",
    slider_color_dark="#4F8EF7",
    # buttons dark
    button_primary_background_fill_dark="linear-gradient(135deg,#2563EB,#4F8EF7)",
    button_primary_background_fill_hover_dark="linear-gradient(135deg,#1D4ED8,#3578E5)",
    button_primary_text_color_dark="#ffffff",
    button_primary_border_color_dark="transparent",
    button_secondary_background_fill_dark="#111927",
    button_secondary_background_fill_hover_dark="#19263A",
    button_secondary_text_color_dark="#E8F0FF",
    button_secondary_border_color_dark="#1C2E45",
    button_cancel_background_fill_dark="rgba(248,113,113,.12)",
    button_cancel_background_fill_hover_dark="rgba(248,113,113,.22)",
    button_cancel_text_color_dark="#FCA5A5",
    button_cancel_border_color_dark="rgba(248,113,113,.3)",
    # ── light token overrides ──────────────────────────────────────────────
    body_background_fill="#F0F4FA",
    body_text_color="#0D1B2E",
    background_fill_primary="#F0F4FA",
    background_fill_secondary="#FFFFFF",
    block_background_fill="#FFFFFF",
    block_border_color="#DDE6F0",
    input_background_fill="#FFFFFF",
    input_border_color="#DDE6F0",
    button_primary_background_fill="linear-gradient(135deg,#1D4ED8,#2563EB)",
    button_primary_background_fill_hover="linear-gradient(135deg,#1E40AF,#1D4ED8)",
    button_primary_text_color="#ffffff",
    button_primary_border_color="transparent",
    button_secondary_background_fill="#F7FAFC",
    button_secondary_background_fill_hover="#EDF1F7",
    button_secondary_text_color="#0D1B2E",
    button_secondary_border_color="#DDE6F0",
    button_cancel_background_fill="#FEF2F2",
    button_cancel_background_fill_hover="#FEE2E2",
    button_cancel_text_color="#991B1B",
    button_cancel_border_color="#FECACA",
    button_large_padding=".65rem 1.4rem",
    button_small_padding=".45rem 1rem",
)

# ---------------------------------------------------------------------------
# Custom CSS — complete redesign, dark-first
# ---------------------------------------------------------------------------
_CSS = """
/* ════════════════════════════════════════════════════════════════════
   IQRA DIGITAL LIBRARY — Premium Dark UI
   ════════════════════════════════════════════════════════════════════ */

/* ── Tokens (dark default) ───────────────────────────────────────── */
:root {
  --bg:    #050912;
  --s1:    #0C1221;
  --s2:    #111927;
  --s3:    #19263A;
  --bd:    #1C2E45;
  --bd2:   #243550;
  --tx:    #E8F0FF;
  --tx2:   #7A93B8;
  --tx3:   #3D5272;
  --blue:  #4F8EF7;
  --blue2: #3578E5;
  --glow:  rgba(79,142,247,.16);
  --glow2: rgba(79,142,247,.07);
  --amber: #FBBF24;
  --green: #34D399;
  --red:   #F87171;
  --purp:  #A78BFA;
  --sh:    0 24px 64px rgba(0,0,0,.75);
  --sh-md: 0 8px 32px rgba(0,0,0,.55);
  --sh-sm: 0 2px 14px rgba(0,0,0,.4);
  --r:     12px;
  --r-sm:  8px;
  --r-lg:  18px;
  --f: 'Inter', ui-sans-serif, system-ui, sans-serif;

  --primary:    var(--blue);
  --primary-lt: var(--glow);
  --accent:     var(--amber);
  --danger:     var(--red);
  --success:    var(--green);
  --surface-0:  var(--bg);
  --surface-1:  var(--s1);
  --border:     var(--bd);
  --text:       var(--tx);
  --muted:      var(--tx2);
  --subtle:     var(--tx3);
  --radius-md:  var(--r);
  --radius-sm:  var(--r-sm);
  --shadow-sm:  var(--sh-sm);
  --shadow-md:  var(--sh);
  --primary-dk: #2563EB;
  --accent-lt:  rgba(251,191,36,.14);
}

html:not(.dark) {
  --bg:    #F0F4FA;
  --s1:    #FFFFFF;
  --s2:    #F7FAFC;
  --s3:    #EDF1F7;
  --bd:    #DDE6F0;
  --bd2:   #C5D4E5;
  --tx:    #0D1B2E;
  --tx2:   #5A7291;
  --tx3:   #94ADC5;
  --blue:  #2563EB;
  --blue2: #1D55D6;
  --glow:  rgba(37,99,235,.12);
  --glow2: rgba(37,99,235,.06);
  --sh:    0 24px 64px rgba(10,30,60,.1);
  --sh-md: 0 8px 32px rgba(10,30,60,.07);
  --sh-sm: 0 2px 14px rgba(10,30,60,.05);
}

/* ── Reset ───────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body, .gradio-container {
  background: var(--bg) !important;
  color: var(--tx) !important;
  font-family: var(--f) !important;
  min-height: 100vh;
}
.gradio-container { padding: 0 !important; max-width: 100% !important; gap: 0 !important; }
#gradio-app { background: var(--bg) !important; }

/* ── Navbar / header ─────────────────────────────────────────────── */
.iqra-header {
  background: #020710;
  border-bottom: 1px solid var(--bd);
  position: sticky; top: 0; z-index: 300;
  box-shadow: 0 1px 0 rgba(79,142,247,.1), 0 4px 24px rgba(0,0,0,.65);
}
.iqra-header-inner {
  max-width: 1440px; margin: auto;
  padding: .85rem 2.5rem;
  display: flex; align-items: center; justify-content: space-between;
}
.iqra-brand { display: flex; align-items: center; gap: .9rem; }
.iqra-logo {
  width: 36px; height: 36px; border-radius: 8px; flex-shrink: 0;
  background: linear-gradient(135deg, #1A3FA8 0%, #4F8EF7 100%);
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 0 16px rgba(79,142,247,.45);
}
.iqra-logo img { width: 22px; height: 22px; object-fit: contain; filter: brightness(0) invert(1); }
.iqra-title { font-size: 1.1rem; font-weight: 800; color: #fff; letter-spacing: -.03em; line-height: 1.15; }
.iqra-title span { color: var(--blue); }
.iqra-subtitle { font-size: .7rem; color: rgba(255,255,255,.3); direction: rtl; margin-top: .04rem; }
.iqra-right { display: flex; align-items: center; gap: .6rem; }
.btn-theme {
  background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.09);
  border-radius: 7px; padding: .35rem .85rem;
  color: rgba(255,255,255,.5); cursor: pointer; font-size: .78rem;
  font-weight: 500; font-family: var(--f);
  transition: all .18s;
}
.btn-theme:hover { background: rgba(255,255,255,.1); color: #fff; border-color: rgba(255,255,255,.18); }

/* ── HERO ────────────────────────────────────────────────────────── */
.hero {
  background: linear-gradient(160deg, #020812 0%, #050F26 45%, #07163A 100%);
  border-bottom: 1px solid var(--bd);
  padding: 4rem 2.5rem 3.25rem;
  position: relative; overflow: hidden;
  text-align: center;
}
html:not(.dark) .hero {
  background: linear-gradient(160deg, #1E3A8A 0%, #1D4ED8 55%, #2563EB 100%);
}
.hero-orb { position: absolute; border-radius: 50%; filter: blur(70px); pointer-events: none; }
.hero-orb-1 {
  width: 700px; height: 700px;
  background: radial-gradient(circle, rgba(79,142,247,.1) 0%, transparent 65%);
  top: -200px; left: 50%; transform: translateX(-50%);
}
.hero-orb-2 {
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(167,139,250,.09) 0%, transparent 70%);
  bottom: -100px; right: 5%;
}
.hero-orb-3 {
  width: 280px; height: 280px;
  background: radial-gradient(circle, rgba(52,211,153,.07) 0%, transparent 70%);
  top: 0; left: 3%;
}
.hero-inner { position: relative; z-index: 1; max-width: 820px; margin: 0 auto; }
.hero-badge {
  display: inline-flex; align-items: center;
  background: rgba(79,142,247,.1); border: 1px solid rgba(79,142,247,.28);
  color: #93C5FD; font-size: .71rem; font-weight: 700;
  letter-spacing: .12em; text-transform: uppercase;
  padding: .3rem .95rem; border-radius: 99px; margin-bottom: 1.5rem;
}
.hero-h1 {
  font-size: clamp(2.4rem, 5.5vw, 3.75rem);
  font-weight: 900; color: #fff;
  letter-spacing: -.048em; line-height: 1.08;
  margin-bottom: 1.1rem;
}
.hero-h1 span {
  background: linear-gradient(135deg, #4F8EF7 0%, #A78BFA 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
}
.hero-sub {
  font-size: .91rem; color: rgba(255,255,255,.38);
  line-height: 1.7; margin-bottom: 2.75rem;
  max-width: 580px; margin-left: auto; margin-right: auto;
}
html:not(.dark) .hero-sub { color: rgba(255,255,255,.65); }
.hero-stats {
  display: flex; align-items: center; justify-content: center; flex-wrap: wrap;
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: var(--r-lg); padding: 1.5rem 1rem;
  margin: 0 auto; max-width: 700px;
  backdrop-filter: blur(16px);
  box-shadow: 0 8px 32px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.06);
}
html:not(.dark) .hero-stats {
  background: rgba(255,255,255,.18);
  border-color: rgba(255,255,255,.3);
  box-shadow: 0 8px 32px rgba(0,0,0,.1), inset 0 1px 0 rgba(255,255,255,.5);
}
.hstat { text-align: center; padding: 0 1.75rem; flex: 1; min-width: 100px; }
.hstat-val {
  font-size: 2rem; font-weight: 900; color: #fff;
  letter-spacing: -.05em; line-height: 1;
}
.hstat-lbl {
  font-size: .68rem; color: rgba(255,255,255,.36);
  margin-top: .4rem; letter-spacing: .08em; text-transform: uppercase;
}
.hstat-div { width: 1px; height: 46px; background: rgba(255,255,255,.09); flex-shrink: 0; }
@media (max-width: 600px) {
  .hero { padding: 2.5rem 1.25rem 2rem; }
  .hstat-div { display: none; }
  .hstat { padding: .5rem 1rem; }
}

/* ── AI pill row ─────────────────────────────────────────────────── */
.ai-pill-wrap {
  background: var(--s1); border-bottom: 1px solid var(--bd);
  padding: .4rem 2.5rem;
}
.ai-pill { display: inline-flex; align-items: center; gap: .42rem; padding: .22rem .75rem; border-radius: 99px; font-size: .77rem; font-weight: 600; }
.ai-pill-on  { background: rgba(52,211,153,.1); color: #6EE7B7; border: 1px solid rgba(52,211,153,.22); }
.ai-pill-off { background: var(--s3); color: var(--tx2); border: 1px solid var(--bd); }
.ai-pill-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.ai-pill-on .ai-pill-dot { background: #34D399; box-shadow: 0 0 8px rgba(52,211,153,.9); animation: pulse 2.2s ease-in-out infinite; }
.ai-pill-off .ai-pill-dot { background: var(--tx3); }
@keyframes pulse { 0%,100%{opacity:1;box-shadow:0 0 8px rgba(52,211,153,.9)} 50%{opacity:.3;box-shadow:none} }

/* ── AI settings panel ───────────────────────────────────────────── */
.ai-panel {
  background: var(--glow2) !important;
  border: 1px solid rgba(79,142,247,.18) !important;
  border-radius: var(--r) !important;
  margin: .6rem 2.5rem .2rem !important;
  max-width: 1440px !important;
}

/* ── Tab bar ─────────────────────────────────────────────────────── */
.tab-nav, div[role="tablist"] {
  background: var(--s1) !important;
  border-bottom: 1px solid var(--bd) !important;
  padding: 0 2.5rem !important;
}
.tab-nav button, div[role="tablist"] button {
  background: transparent !important; color: var(--tx2) !important;
  border: none !important; border-bottom: 2px solid transparent !important;
  border-radius: 0 !important; padding: .85rem 1.2rem !important;
  font-size: .86rem !important; font-weight: 500 !important;
  letter-spacing: .012em !important; white-space: nowrap !important;
  transition: color .15s, border-color .15s !important;
  margin-bottom: -1px !important;
}
.tab-nav button:hover, div[role="tablist"] button:hover { color: var(--tx) !important; }
.tab-nav button.selected, div[role="tablist"] button[aria-selected="true"] {
  color: var(--blue) !important;
  border-bottom-color: var(--blue) !important;
  font-weight: 600 !important;
}

/* ── Page wrapper ────────────────────────────────────────────────── */
.tab-wrap { max-width: 1440px; margin: 0 auto; padding: 1.75rem 2.5rem 4rem; }

/* ── Search hero card ────────────────────────────────────────────── */
.search-hero {
  background: linear-gradient(140deg, #020812 0%, #061228 55%, #091B3E 100%);
  border: 1px solid var(--bd);
  border-radius: var(--r-lg);
  padding: 2rem 2.25rem 1.75rem;
  margin-bottom: 1.4rem;
  position: relative; overflow: hidden;
}
.search-hero::before {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: radial-gradient(ellipse 55% 90% at 95% 50%, rgba(79,142,247,.07) 0%, transparent 70%);
}
html:not(.dark) .search-hero {
  background: linear-gradient(140deg, #1E3A8A 0%, #1D4ED8 55%, #2563EB 100%);
  border-color: rgba(37,99,235,.4);
}
.search-hero-label {
  font-size: .68rem; font-weight: 700; letter-spacing: .13em;
  text-transform: uppercase; color: rgba(255,255,255,.38); margin-bottom: .6rem;
}
.search-hero textarea, .search-hero input {
  background: rgba(255,255,255,.07) !important;
  border: 1px solid rgba(255,255,255,.14) !important;
  color: #fff !important; font-size: 1rem !important;
  border-radius: var(--r-sm) !important;
  transition: border-color .2s, box-shadow .2s !important;
}
.search-hero textarea:focus, .search-hero input:focus {
  border-color: rgba(79,142,247,.6) !important;
  box-shadow: 0 0 0 3px rgba(79,142,247,.15) !important;
}
.search-hero textarea::placeholder, .search-hero input::placeholder { color: rgba(255,255,255,.27) !important; }
.search-hero label { display: none !important; }

/* ── Filter / action cards ───────────────────────────────────────── */
.filter-card, .action-strip {
  background: var(--s1); border: 1px solid var(--bd);
  border-radius: var(--r); padding: 1.1rem 1.4rem; box-shadow: var(--sh-sm);
}
.filter-card { margin-bottom: 1.25rem; }
.action-strip { margin-top: 1.5rem; }
.action-strip-label {
  font-size: .68rem; font-weight: 700; color: var(--tx3);
  text-transform: uppercase; letter-spacing: .1em; margin-bottom: .7rem;
}

/* ── Status messages ─────────────────────────────────────────────── */
.msg-ok   { background: rgba(52,211,153,.07);  color: #6EE7B7; border: 1px solid rgba(52,211,153,.2);  border-radius: var(--r-sm); padding: .8rem 1.1rem; font-weight: 500; margin:.5rem 0; }
.msg-err  { background: rgba(248,113,113,.07); color: #FCA5A5; border: 1px solid rgba(248,113,113,.2); border-radius: var(--r-sm); padding: .8rem 1.1rem; font-weight: 500; margin:.5rem 0; }
.msg-info { background: var(--glow2);          color: #93C5FD; border: 1px solid rgba(79,142,247,.2);  border-radius: var(--r-sm); padding: .8rem 1.1rem; font-weight: 500; margin:.5rem 0; }
html:not(.dark) .msg-ok   { background:#ECFDF5; color:#065F46; border-color:#A7F3D0; }
html:not(.dark) .msg-err  { background:#FEF2F2; color:#991B1B; border-color:#FECACA; }
html:not(.dark) .msg-info { background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE; }

/* ── Book result sections ────────────────────────────────────────── */
.results-root { padding: .25rem 0; }
.section-header { display:flex; align-items:center; gap:.55rem; margin:2rem 0 1.1rem; padding-bottom:.6rem; border-bottom:1px solid var(--bd); }
.section-title { margin:0; font-size:.93rem; font-weight:700; flex:1; color:var(--tx); letter-spacing:-.01em; }
.section-count { background:var(--glow2); color:var(--blue); font-size:.7rem; font-weight:700; padding:.14rem .52rem; border-radius:99px; border:1px solid rgba(79,142,247,.22); }

/* ── Book cards ──────────────────────────────────────────────────── */
.cards-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(185px,1fr)); gap:1.1rem; }
.book-card {
  background:var(--s1); border:1px solid var(--bd); border-radius:var(--r); overflow:hidden;
  display:flex; flex-direction:column; box-shadow:var(--sh-sm);
  transition:transform .22s cubic-bezier(.4,0,.2,1), box-shadow .22s, border-color .22s;
}
.book-card:hover { transform:translateY(-4px); box-shadow:var(--sh-md),0 0 0 1px rgba(79,142,247,.22); border-color:rgba(79,142,247,.38); }
.book-cover-wrap { position:relative; background:var(--s2); aspect-ratio:2/3; overflow:hidden; }
.book-cover { width:100%; height:100%; object-fit:cover; display:block; transition:transform .4s cubic-bezier(.4,0,.2,1); }
.book-card:hover .book-cover { transform:scale(1.07); }
.src-badge { position:absolute; top:.45rem; left:.45rem; background:rgba(0,0,0,.72); color:rgba(255,255,255,.9); font-size:.62rem; font-weight:700; padding:.14rem .4rem; border-radius:4px; backdrop-filter:blur(6px); letter-spacing:.05em; }
.book-info { padding:.8rem .95rem .9rem; display:flex; flex-direction:column; flex:1; gap:.2rem; }
.book-title { margin:0; font-size:.9rem; font-weight:700; color:var(--tx); line-height:1.35; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.book-author { margin:0; font-size:.78rem; color:var(--tx2); font-weight:500; }
.book-meta { display:flex; flex-wrap:wrap; gap:.28rem; align-items:center; margin-top:.12rem; }
.stars  { color:var(--amber); font-size:.78rem; font-weight:600; }
.badge  { background:var(--glow2); color:var(--blue); font-size:.65rem; font-weight:700; padding:.1rem .35rem; border-radius:4px; border:1px solid rgba(79,142,247,.2); }
.book-desc { margin:.2rem 0 .4rem; font-size:.77rem; color:var(--tx2); line-height:1.55; flex:1; display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.more-link { display:inline-block; color:var(--blue) !important; font-size:.78rem; font-weight:600; text-decoration:none !important; margin-top:auto; }
.no-results { grid-column:1/-1; text-align:center; padding:3.5rem 2rem; color:var(--tx2); background:var(--s1); border:1px dashed var(--bd2); border-radius:var(--r); }
.subtle { font-size:.7rem; color:var(--tx3); }

/* ── Browse table ────────────────────────────────────────────────── */
.browse-wrap { overflow-x:auto; border:1px solid var(--bd); border-radius:var(--r); box-shadow:var(--sh-sm); }
.browse-table { width:100%; border-collapse:collapse; font-size:.86rem; background:var(--s1); }
.browse-table th { background:var(--s2); color:var(--tx2); text-align:left; padding:.7rem 1rem; font-weight:600; font-size:.74rem; text-transform:uppercase; letter-spacing:.06em; white-space:nowrap; border-bottom:1px solid var(--bd); }
.browse-table td { padding:.65rem 1rem; border-bottom:1px solid var(--bd); color:var(--tx); vertical-align:middle; }
.browse-table tr:last-child td { border-bottom:none; }
.browse-table tr:hover td { background:var(--s2); }

/* ── Analytics stat cards ────────────────────────────────────────── */
.stat-cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:1rem; margin:0 0 1.75rem; }
.stat-card { background:var(--s1); border:1px solid var(--bd); border-radius:var(--r-lg); padding:1.5rem 1.6rem; text-align:center; box-shadow:var(--sh-sm); position:relative; overflow:hidden; }
.stat-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; }
.stat-card .stat-value { font-size:2.1rem; font-weight:900; line-height:1; margin-bottom:.3rem; letter-spacing:-.05em; }
.stat-card .stat-label { font-size:.74rem; color:var(--tx2); letter-spacing:.03em; }
.stat-blue::before   { background:linear-gradient(90deg,#4F8EF7,#93C5FD); } .stat-blue   .stat-value { color:#4F8EF7; }
.stat-amber::before  { background:linear-gradient(90deg,#FBBF24,#FCD34D); } .stat-amber  .stat-value { color:#FBBF24; }
.stat-green::before  { background:linear-gradient(90deg,#34D399,#6EE7B7); } .stat-green  .stat-value { color:#34D399; }
.stat-purple::before { background:linear-gradient(90deg,#A78BFA,#C4B5FD); } .stat-purple .stat-value { color:#A78BFA; }

/* ── Manage & intro cards ────────────────────────────────────────── */
.manage-card { background:var(--s1); border:1px solid var(--bd); border-radius:var(--r); padding:1.5rem 1.75rem; margin-bottom:1.5rem; box-shadow:var(--sh-sm); }
.manage-card-title { font-size:.9rem; font-weight:700; color:var(--tx); margin-bottom:1.1rem; padding-bottom:.7rem; border-bottom:1px solid var(--bd); letter-spacing:-.01em; }
.intro-banner { background:var(--glow2); border:1px solid rgba(79,142,247,.18); border-radius:var(--r); padding:.9rem 1.25rem; margin-bottom:1.25rem; font-size:.87rem; color:var(--tx); line-height:1.6; }
html:not(.dark) .intro-banner { background:#EFF6FF; border-color:#BFDBFE; color:#1E3A8A; }

/* ── AI status text ──────────────────────────────────────────────── */
.ai-status-ok  { color:#34D399; font-weight:600; }
.ai-status-err { color:var(--red); font-weight:600; }
.ai-status-off { color:var(--tx2); }

/* ── Footer ──────────────────────────────────────────────────────── */
.iqra-footer { text-align:center; padding:1.5rem; font-size:.77rem; color:var(--tx3); border-top:1px solid var(--bd); margin-top:2rem; }
.iqra-footer a { color:var(--blue); text-decoration:none; }

/* ── Responsive ──────────────────────────────────────────────────── */
@media (max-width:900px) {
  .iqra-header-inner,.ai-pill-wrap { padding-left:1.25rem !important; padding-right:1.25rem !important; }
  .tab-wrap { padding:1.25rem 1.25rem 3rem; }
  .ai-panel { margin-left:1.25rem !important; margin-right:1.25rem !important; }
  .tab-nav, div[role="tablist"] { padding:0 1.25rem !important; }
  .cards-grid { grid-template-columns:repeat(auto-fill,minmax(145px,1fr)); }
  .search-hero { padding:1.4rem 1.25rem; }
  .stat-cards { grid-template-columns:1fr 1fr; }
}

/* ── Gradio component overrides ──────────────────────────────────── */
.gradio-container label { font-size:.84rem !important; font-weight:500 !important; color:var(--tx2) !important; margin-bottom:.3rem !important; }
.gradio-container .block { border-radius:var(--r) !important; }
.gradio-container input:focus, .gradio-container textarea:focus { box-shadow:0 0 0 3px var(--glow) !important; outline:none !important; border-color:var(--blue) !important; }

/* ── Buttons — comprehensive override ───────────────────────────── */
.gradio-container button,
button.gr-button {
  font-family: var(--f) !important;
  font-size: .86rem !important;
  font-weight: 600 !important;
  border-radius: var(--r-sm) !important;
  padding: .6rem 1.25rem !important;
  min-height: 40px !important;
  cursor: pointer !important;
  transition: all .18s cubic-bezier(.4,0,.2,1) !important;
  letter-spacing: .01em !important;
  border: none !important;
}

/* Primary */
.gradio-container button.primary,
button.gr-button.primary,
.gradio-container button[class*="primary"] {
  background: linear-gradient(135deg, #2563EB 0%, #4F8EF7 100%) !important;
  color: #fff !important;
  box-shadow: 0 4px 14px rgba(79,142,247,.4), inset 0 1px 0 rgba(255,255,255,.15) !important;
}
.gradio-container button.primary:hover,
button.gr-button.primary:hover,
.gradio-container button[class*="primary"]:hover {
  background: linear-gradient(135deg, #1D4ED8 0%, #3578E5 100%) !important;
  box-shadow: 0 6px 20px rgba(79,142,247,.55), inset 0 1px 0 rgba(255,255,255,.15) !important;
  transform: translateY(-1px) !important;
}
.gradio-container button.primary:active,
button.gr-button.primary:active {
  transform: translateY(0) !important;
  box-shadow: 0 2px 8px rgba(79,142,247,.35) !important;
}

/* Secondary */
.gradio-container button.secondary,
button.gr-button.secondary,
.gradio-container button[class*="secondary"] {
  background: var(--s2) !important;
  color: var(--tx) !important;
  border: 1px solid var(--bd2) !important;
  box-shadow: 0 2px 8px rgba(0,0,0,.25) !important;
}
.gradio-container button.secondary:hover,
button.gr-button.secondary:hover,
.gradio-container button[class*="secondary"]:hover {
  background: var(--s3) !important;
  border-color: var(--blue) !important;
  color: var(--blue) !important;
  transform: translateY(-1px) !important;
}

/* Stop / danger */
.gradio-container button[class*="stop"],
.gradio-container button.stop,
button.gr-button.stop {
  background: rgba(248,113,113,.12) !important;
  color: #FCA5A5 !important;
  border: 1px solid rgba(248,113,113,.28) !important;
}
.gradio-container button[class*="stop"]:hover,
.gradio-container button.stop:hover {
  background: rgba(248,113,113,.22) !important;
  border-color: rgba(248,113,113,.5) !important;
  color: #FCA5A5 !important;
  transform: translateY(-1px) !important;
}

/* ── Inputs, textareas ───────────────────────────────────────────── */
.gradio-container input,
.gradio-container textarea,
.gradio-container select {
  background: var(--s2) !important;
  border: 1px solid var(--bd2) !important;
  color: var(--tx) !important;
  border-radius: var(--r-sm) !important;
  font-family: var(--f) !important;
  font-size: .88rem !important;
  padding: .55rem .85rem !important;
  transition: border-color .18s, box-shadow .18s !important;
}
.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
  color: var(--tx3) !important;
}

/* ── Dropdowns ───────────────────────────────────────────────────── */
.gradio-container .wrap { border-radius: var(--r-sm) !important; }
.gradio-container ul[role="listbox"] {
  background: var(--s2) !important;
  border: 1px solid var(--bd2) !important;
  border-radius: var(--r-sm) !important;
  box-shadow: var(--sh-md) !important;
}
.gradio-container ul[role="listbox"] li {
  color: var(--tx) !important;
  font-size: .86rem !important;
}
.gradio-container ul[role="listbox"] li:hover {
  background: var(--glow) !important;
  color: var(--blue) !important;
}

/* ── Checkboxes ──────────────────────────────────────────────────── */
.gradio-container input[type="checkbox"] {
  accent-color: var(--blue) !important;
  width: 15px !important; height: 15px !important;
}

/* ── Sliders ─────────────────────────────────────────────────────── */
.gradio-container input[type="range"] {
  accent-color: var(--blue) !important;
  background: transparent !important;
  border: none !important; padding: 0 !important;
}

/* ── Chatbot ─────────────────────────────────────────────────────── */
.gradio-container .bubble-wrap { padding: .25rem 0 !important; }
.gradio-container .message.bot,
.gradio-container [class*="bot"] > .message,
.gradio-container [data-testid*="bot"] {
  background: var(--s2) !important;
  border: 1px solid var(--bd) !important;
  border-radius: var(--r) !important;
  color: var(--tx) !important;
}
.gradio-container .message.user,
.gradio-container [class*="user"] > .message,
.gradio-container [data-testid*="user"] {
  background: linear-gradient(135deg, rgba(37,99,235,.15) 0%, rgba(79,142,247,.1) 100%) !important;
  border: 1px solid rgba(79,142,247,.22) !important;
  border-radius: var(--r) !important;
  color: var(--tx) !important;
}

/* ── Accordion ───────────────────────────────────────────────────── */
.gradio-container details > summary {
  font-weight: 600 !important; font-size: .88rem !important;
  color: var(--tx) !important; cursor: pointer !important;
  padding: .75rem 1rem !important;
}
.gradio-container details {
  background: var(--s2) !important;
  border: 1px solid var(--bd) !important;
  border-radius: var(--r) !important;
}

/* ── Progress / loading ──────────────────────────────────────────── */
.gradio-container .progress-bar { background: var(--blue) !important; }
.gradio-container .eta-bar { background: rgba(79,142,247,.3) !important; }

/* ── Scrollbar ───────────────────────────────────────────────────── */
* { scrollbar-width: thin; scrollbar-color: var(--bd2) transparent; }
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--bd2); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--tx3); }
"""

_CSS += """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
  --bg: #F4F7FB;
  --surface: #FFFFFF;
  --surface-alt: #F8FAFD;
  --surface-strong: #EEF3F8;
  --border: #D8E1EC;
  --border-strong: #C4D1DE;
  --text: #122033;
  --muted: #5F728B;
  --subtle: #8798AD;
  --primary: #0F766E;
  --primary-strong: #0B5F58;
  --accent: #C69235;
  --accent-soft: rgba(198,146,53,.12);
  --primary-soft: rgba(15,118,110,.10);
  --success-soft: rgba(22,163,74,.10);
  --error-soft: rgba(190,24,93,.10);
  --info-soft: rgba(14,116,144,.10);
  --shadow-sm: 0 14px 30px rgba(15,23,42,.06);
  --shadow-md: 0 28px 72px rgba(15,23,42,.08);
  --radius-sm: 12px;
  --radius-md: 20px;
  --radius-lg: 32px;
  --font-display: 'Plus Jakarta Sans', ui-sans-serif, sans-serif;
}

html.dark {
  --bg: #08121E;
  --surface: #0F1B2D;
  --surface-alt: #122033;
  --surface-strong: #16283E;
  --border: #22364C;
  --border-strong: #2E4560;
  --text: #EAF1F6;
  --muted: #9AB0C2;
  --subtle: #68829B;
  --primary: #2DD4BF;
  --primary-strong: #14B8A6;
  --accent: #E2B760;
  --accent-soft: rgba(226,183,96,.14);
  --primary-soft: rgba(45,212,191,.12);
  --success-soft: rgba(74,222,128,.12);
  --error-soft: rgba(251,113,133,.12);
  --info-soft: rgba(56,189,248,.12);
  --shadow-sm: 0 18px 36px rgba(2,6,23,.44);
  --shadow-md: 0 34px 76px rgba(2,6,23,.58);
}

body,
.gradio-container {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--font-display) !important;
}

.gradio-container {
  max-width: 100% !important;
  padding: 0 0 2.5rem !important;
  gap: 0 !important;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 300;
  border-bottom: 1px solid var(--border);
  background: rgba(244,247,251,.88);
  backdrop-filter: blur(20px);
}

html.dark .app-header { background: rgba(8,18,30,.82); }

.app-header-inner {
  max-width: 1480px;
  margin: 0 auto;
  padding: 1rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.brand-lockup { display: flex; align-items: center; gap: .95rem; }

.brand-mark {
  width: 48px;
  height: 48px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(15,118,110,.18), rgba(198,146,53,.18));
  border: 1px solid rgba(15,118,110,.18);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
}

.brand-mark img { width: 30px; height: 30px; object-fit: contain; }
.brand-title {
  margin: 0;
  color: var(--text);
  font-size: 1.08rem;
  font-weight: 800;
  letter-spacing: -.03em;
}

.brand-tag {
  margin: .18rem 0 0;
  color: var(--muted);
  font-size: .8rem;
}

.header-tools { display: flex; align-items: center; gap: .8rem; }

.btn-theme {
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  border-radius: 999px;
  padding: .7rem 1rem;
  font-size: .84rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.hero {
  max-width: 1480px;
  margin: 1.25rem auto 1.15rem;
  padding: 0 2rem;
  background: transparent;
  border-bottom: none;
}

.hero-grid {
  position: relative;
  overflow: hidden;
  display: grid;
  grid-template-columns: 1.25fr .95fr;
  gap: 1.4rem;
  padding: 2.3rem;
  border-radius: var(--radius-lg);
  border: 1px solid rgba(15,118,110,.18);
  background:
    radial-gradient(circle at top left, rgba(45,212,191,.10), transparent 32%),
    radial-gradient(circle at bottom right, rgba(198,146,53,.14), transparent 30%),
    linear-gradient(135deg, #0E2235 0%, #142D45 55%, #18344F 100%);
  box-shadow: var(--shadow-md);
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  padding: .45rem .78rem;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.07);
  color: #E4F8F4;
  font-size: .8rem;
  font-weight: 700;
  letter-spacing: .08em;
  text-transform: uppercase;
}

.hero-title {
  margin: 1rem 0 .8rem;
  color: #FFFFFF;
  font-size: clamp(2.5rem, 5vw, 4.6rem);
  line-height: .96;
  letter-spacing: -.06em;
  font-weight: 900;
}

.hero-title span { color: #E2B760; }

.hero-copy p,
.hero-note {
  color: rgba(234,241,246,.78);
  font-size: 1rem;
  line-height: 1.8;
}

.hero-chip-row {
  margin-top: 1.4rem;
  display: flex;
  flex-wrap: wrap;
  gap: .7rem;
}

.hero-chip {
  display: inline-flex;
  align-items: center;
  padding: .58rem .82rem;
  border-radius: 999px;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.10);
  color: #EAF1F6;
  font-size: .84rem;
  font-weight: 600;
}

.hero-panel {
  padding: 1.35rem;
  border-radius: 24px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(7,18,30,.44);
  backdrop-filter: blur(18px);
}

.hero-panel-heading h3 {
  margin: 0;
  color: #FFFFFF;
  font-size: 1.08rem;
  font-weight: 800;
}

.hero-panel-heading p {
  margin: .35rem 0 0;
  color: rgba(234,241,246,.70);
  font-size: .88rem;
  line-height: 1.6;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .9rem;
  margin-top: 0;
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
}

.hstat {
  padding: 1rem;
  border-radius: 18px;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.08);
  min-width: 0;
}

.hstat-val {
  color: #FFFFFF;
  font-size: 1.55rem;
  font-weight: 900;
}

.hstat-lbl {
  margin-top: .35rem;
  color: rgba(234,241,246,.72);
  font-size: .76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
}

.hero-orb,
.hero-orb-1,
.hero-orb-2,
.hero-orb-3,
.hstat-div { display: none !important; }

.ai-panel,
.status-ribbon,
.iqra-footer { max-width: 1480px; margin: 0 auto; padding: 0 2rem; }

.status-ribbon { margin-bottom: 1rem; }
.tab-wrap { max-width: 1480px; padding: 0 2rem 2.2rem !important; }

.ai-panel .block,
.ai-panel > div,
.search-hero,
.filter-card,
.action-strip,
.manage-card,
.intro-banner,
.prompt-panel,
.catalog-note {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: 22px !important;
  box-shadow: var(--shadow-sm) !important;
}

.search-hero,
.filter-card,
.action-strip,
.manage-card,
.intro-banner,
.prompt-panel,
.catalog-note { padding: 1.15rem !important; }

.gradio-container .tab-nav {
  max-width: 1480px;
  margin: 0 auto .95rem;
  padding: 0 2rem;
  gap: .75rem;
  border: none !important;
  background: transparent !important;
}

.gradio-container button[role="tab"] {
  border: 1px solid var(--border) !important;
  background: var(--surface-alt) !important;
  color: var(--muted) !important;
  border-radius: 999px !important;
  padding: .72rem 1.05rem !important;
  font-weight: 700 !important;
}

.gradio-container button[role="tab"][aria-selected="true"] {
  background: var(--surface) !important;
  color: var(--text) !important;
  border-color: rgba(15,118,110,.26) !important;
  box-shadow: var(--shadow-sm) !important;
}

.workspace-intro {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  padding-top: .25rem;
  margin-bottom: 1rem;
}

.workspace-eyebrow {
  margin: 0 0 .55rem;
  color: var(--primary);
  font-size: .78rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .14em;
}

.workspace-heading {
  margin: 0;
  color: var(--text);
  font-size: clamp(1.3rem, 2vw, 1.7rem);
  line-height: 1.15;
  letter-spacing: -.04em;
}

.workspace-copy {
  margin: .3rem 0 0;
  max-width: 760px;
  color: var(--muted);
  font-size: .88rem;
  line-height: 1.6;
}

.workspace-card-copy {
  margin: 0;
  color: var(--muted);
  font-size: .92rem;
  line-height: 1.68;
}

.workspace-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: .6rem;
}

.workspace-chip {
  display: inline-flex;
  align-items: center;
  padding: .6rem .82rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: .82rem;
  font-weight: 700;
  box-shadow: var(--shadow-sm);
}

.search-hero-label,
.action-strip-label,
.manage-card-title {
  margin: 0 0 .55rem;
  color: var(--text);
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: -.02em;
  text-transform: none;
}

.results-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .9rem;
  margin-bottom: 1rem;
}

.results-kpi {
  display: flex;
  flex-direction: column;
  gap: .2rem;
  padding: 1rem;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.results-kpi-value {
  color: var(--text);
  font-size: 1.5rem;
  font-weight: 900;
}

.results-kpi-label {
  color: var(--muted);
  font-size: .8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 1.3rem 0 .95rem;
  padding-bottom: 0;
  border-bottom: none;
}

.section-header .section-heading { display: flex; align-items: center; gap: .75rem; }

.section-icon {
  width: 2rem;
  height: 2rem;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: .78rem;
  font-weight: 900;
}

.section-count {
  margin-left: 0;
  display: inline-flex;
  align-items: center;
  padding: .44rem .7rem;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: .8rem;
  font-weight: 700;
}

.cards-grid { grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 1rem; }

.book-card {
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 1rem;
  padding: 1rem;
  border-radius: 22px;
  border: 1px solid var(--border);
  background: var(--surface) !important;
  box-shadow: var(--shadow-sm) !important;
}

.book-cover-wrap {
  min-height: 164px;
  border-radius: 18px;
  border: 1px solid var(--border);
  background: var(--surface-alt);
}

.book-head {
  display: flex;
  justify-content: space-between;
  gap: .75rem;
  align-items: flex-start;
}

.book-score {
  min-width: 3rem;
  padding: .48rem .62rem;
  border-radius: 14px;
  background: var(--primary-soft);
  color: var(--primary);
  text-align: center;
  font-weight: 800;
}

.book-meta {
  display: flex;
  flex-wrap: wrap;
  gap: .55rem;
  align-items: center;
}

.book-footer {
  margin-top: auto;
  padding-top: .95rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: .75rem;
}

.book-signal { color: var(--muted); font-size: .82rem; line-height: 1.5; }
.src-badge { background: rgba(8,18,30,.78); font-weight: 800; }
.stars { color: var(--accent); font-weight: 800; }
.badge {
  padding: .35rem .6rem;
  border-radius: 999px;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  color: var(--muted);
  font-size: .78rem;
  font-weight: 700;
}

.empty-state,
.no-results {
  padding: 2.4rem 1.4rem;
  border-radius: 22px;
  border: 1px dashed var(--border-strong);
  background: var(--surface);
  text-align: center;
  color: var(--muted);
}

.empty-state h3 {
  margin: 0 0 .5rem;
  color: var(--text);
  font-size: 1.05rem;
  font-weight: 800;
}

.browse-wrap {
  border-radius: 22px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.browse-table {
  min-width: 760px;
  border-collapse: separate;
  border-spacing: 0;
  background: var(--surface);
}

.browse-table th {
  background: var(--surface-alt);
  color: var(--muted);
  font-size: .76rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .08em;
}

.browse-table td {
  padding: .9rem 1rem;
  color: var(--text);
  border-bottom: 1px solid var(--border);
}

.browse-table tr:hover td { background: var(--surface-alt); }

.table-book { display: flex; align-items: center; gap: .9rem; }

.table-cover {
  width: 48px;
  height: 68px;
  border-radius: 14px;
  overflow: hidden;
  background: var(--surface-alt);
  border: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.table-cover-image { width: 100%; height: 100%; object-fit: cover; }
.table-placeholder { padding: 0 .35rem; color: var(--subtle); font-size: .72rem; text-align: center; }
.table-title { color: var(--text); font-weight: 800; }
.table-subtle { margin-top: .2rem; color: var(--muted); font-size: .84rem; line-height: 1.5; }
.table-source {
  display: inline-flex;
  align-items: center;
  padding: .32rem .56rem;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: .76rem;
  font-weight: 800;
}

.table-link,
.more-link {
  color: var(--primary);
  text-decoration: none;
  font-weight: 800;
}

.stat-cards { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.stat-card {
  border-radius: 20px;
  border: 1px solid var(--border);
  background: var(--surface) !important;
  box-shadow: var(--shadow-sm) !important;
}

.msg-ok,
.msg-err,
.msg-info {
  padding: .9rem 1rem;
  border-radius: 18px;
  border: 1px solid var(--border);
  color: var(--text);
}

.msg-tag {
  display: inline-flex;
  align-items: center;
  margin-right: .65rem;
  padding: .2rem .5rem;
  border-radius: 999px;
  font-size: .74rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: .08em;
}

.msg-ok { background: var(--success-soft); border-color: rgba(22,163,74,.24); }
.msg-ok .msg-tag { background: rgba(22,163,74,.14); color: #15803D; }
.msg-err { background: var(--error-soft); border-color: rgba(190,24,93,.24); }
.msg-err .msg-tag { background: rgba(190,24,93,.14); color: #BE185D; }
.msg-info { background: var(--info-soft); border-color: rgba(14,116,144,.24); }
.msg-info .msg-tag { background: rgba(14,116,144,.14); color: #0E7490; }

.gradio-container label {
  color: var(--muted) !important;
  font-size: .82rem !important;
  font-weight: 700 !important;
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select {
  border: 1px solid var(--border) !important;
  background: var(--surface-alt) !important;
  color: var(--text) !important;
  border-radius: 14px !important;
}

.gradio-container input:focus,
.gradio-container textarea:focus,
.gradio-container select:focus {
  border-color: var(--primary) !important;
  box-shadow: 0 0 0 3px var(--primary-soft) !important;
}

.gradio-container button { border-radius: 14px !important; font-weight: 800 !important; }
.gradio-container ul[role="listbox"] { background: var(--surface) !important; border: 1px solid var(--border) !important; }
.gradio-container ul[role="listbox"] li:hover { background: var(--surface-alt) !important; }

.gradio-container .message.bot,
.gradio-container [class*="bot"] > .message,
.gradio-container [data-testid*="bot"] {
  background: var(--surface-alt) !important;
  border: 1px solid var(--border) !important;
  color: var(--text) !important;
}

.gradio-container .message.user,
.gradio-container [class*="user"] > .message,
.gradio-container [data-testid*="user"] {
  background: var(--primary-soft) !important;
  border: 1px solid rgba(15,118,110,.18) !important;
  color: var(--text) !important;
}

@media (max-width: 1180px) {
  .hero-grid { grid-template-columns: 1fr; }
  .workspace-intro { align-items: flex-start; flex-direction: column; }
  .workspace-chips { justify-content: flex-start; }
  .results-overview,
  .stat-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 760px) {
  .app-header-inner,
  .hero,
  .ai-panel,
  .status-ribbon,
  .tab-wrap,
  .gradio-container .tab-nav,
  .iqra-footer { padding-left: 1rem !important; padding-right: 1rem !important; }
  .app-header-inner { align-items: flex-start; flex-direction: column; }
  .header-tools { width: 100%; justify-content: flex-start; }
  .hero-grid { padding: 1.4rem; }
  .hero-stats,
  .results-overview,
  .stat-cards,
  .prompt-grid { grid-template-columns: 1fr; }
  .cards-grid { grid-template-columns: 1fr; }
  .book-card { grid-template-columns: 1fr; }
}
"""

# ---------------------------------------------------------------------------
# Helper — styled HTML feedback
# ---------------------------------------------------------------------------
def _msg_ok(text: str) -> str:
    safe = html_mod.escape(text)
    return f'<div class="msg-ok"><span class="msg-tag">Success</span>{safe}</div>'


def _msg_err(text: str) -> str:
    safe = html_mod.escape(text)
    return f'<div class="msg-err"><span class="msg-tag">Error</span>{safe}</div>'


def _msg_info(text: str) -> str:
    safe = html_mod.escape(text)
    return f'<div class="msg-info"><span class="msg-tag">Info</span>{safe}</div>'


def _workspace_intro_html(
    eyebrow: str,
    title: str,
    copy: str,
    chips: list[str] | None = None,
) -> str:
    chips_html = "".join(
        f"<span class='workspace-chip'>{html_mod.escape(chip)}</span>"
        for chip in (chips or [])
    )
    return f"""
<section class="workspace-intro">
  <div>
    <p class="workspace-eyebrow">{html_mod.escape(eyebrow)}</p>
    <h2 class="workspace-heading">{html_mod.escape(title)}</h2>
    <p class="workspace-copy">{html_mod.escape(copy)}</p>
  </div>
  <div class="workspace-chips">{chips_html}</div>
</section>
"""


def _empty_state_html(title: str, copy: str) -> str:
    return (
        f"<div class='empty-state'><h3>{html_mod.escape(title)}</h3>"
        f"<p>{html_mod.escape(copy)}</p></div>"
    )


# ---------------------------------------------------------------------------
# AI Settings handlers
# ---------------------------------------------------------------------------
def _update_model_choices(provider: str) -> gr.update:
    """Update the model dropdown when provider changes."""
    models = PROVIDER_MODELS.get(provider.lower(), [])
    return gr.update(choices=models, value=models[0] if models else None)


def _ai_connect(provider: str, model: str) -> str:
    """Connect to the AI provider and build the agent."""
    status_raw = llm.configure(provider, model)
    status = html_mod.escape(status_raw)

    if llm.is_enabled:
        ok = agent_mgr.build()
        suffix = ""
        if not ok:
            suffix = (
                "<br><small style='color:var(--muted)'>"
                "Agent build failed. Check LangChain packages are installed.</small>"
            )
        css_class = "ai-status-ok"
        return f'<span class="{css_class}">{status}</span>{suffix}'

    return f'<span class="ai-status-err">{status}</span>'


# ---------------------------------------------------------------------------
# Recommend tab handlers
# ---------------------------------------------------------------------------
def _do_recommend(
    prompt:    str,
    lang:      str,
    ln:        int,
    en:        int,
    mr:        float,
    sm:        str,
    sb:        str,
    use_ai:    bool,
    use_hyde:  bool,
    use_mq:    bool,
    use_rr:    bool,
    cat:       str = "Any",
) -> tuple[str, gr.update, list]:
    """Search, optionally expand query with AI, and return results."""
    if not prompt.strip():
        empty = _empty_state_html(
            "Start with a reading goal",
            "Describe a genre, theme, audience, or mood to generate ranked recommendations.",
        )
        return empty, gr.update(choices=[], value=None), []

    effective_query = llm.expand_query(prompt) if (use_ai and llm.is_enabled) else prompt
    if effective_query != prompt:
        logger.info("AI expanded query: '%s' → '%s'", prompt, effective_query)

    # External results always come from BookRecommender (Google Books + OpenLibrary)
    _, ext_r = reco.recommend(effective_query, lang, 0, en, mr, "External Only", sb)

    # Local results: KG+FAISS hybrid is the default (no AI required).
    # Advanced RAG stages (HyDE / multi-query / re-rank) layer on top when AI is on.
    local_r: list = []
    if sm in ("Both", "Local Only") and ln > 0:
        if use_ai and rag_pipeline.is_ready and (use_hyde or use_mq or use_rr):
            # Full RAG pipeline — adds HyDE / multi-query / cross-encoder rerank
            pipeline_results = rag_pipeline.search(
                effective_query,
                k=ln,
                use_hyde=use_hyde,
                use_multi_query=use_mq,
                use_rerank=use_rr,
            )
            local_r = pipeline_results if pipeline_results else []
        elif hybrid_ret.is_ready:
            # KG + FAISS hybrid (default — no AI needed)
            candidates = hybrid_ret.search(effective_query, k=ln * 4)
            lang_code  = settings.languages.get(lang, "")
            if lang_code:
                candidates = [b for b in candidates if b.get("language", "") in ("", lang_code)]
            if cat and cat != "Any":
                cat_filtered = [b for b in candidates if cat in [c.strip() for c in str(b.get("categories", "")).split(",")]]
                candidates = cat_filtered if cat_filtered else candidates
            if mr > 0:
                filtered = [b for b in candidates if float(b.get("average_rating", 0)) >= mr]
                candidates = filtered or candidates
            local_r = candidates[:ln]
        else:
            # Fallback: pure FAISS via BookRecommender
            local_r, _ = reco.recommend(effective_query, lang, ln, 0, mr, "Local Only", sb)

    if sm == "External Only":
        local_r = []

    html        = reco.format_books(local_r, ext_r)
    all_results = local_r + ext_r
    titles      = [b["title"] for b in all_results]

    return (
        html,
        gr.update(choices=titles, value=titles[0] if titles else None),
        all_results,
    )


def _save_to_rl(selected_title: str, results: list) -> str:
    if not selected_title:
        return _msg_err("Select a book first.")
    book = next((b for b in results if b.get("title") == selected_title), None)
    if not book:
        return _msg_err("Book not found in current results.")
    msg = reading_list_mgr.add(book)
    return _msg_ok(msg)


def _find_similar(selected_title: str) -> str:
    if not selected_title:
        return _msg_err("Select a book first.")
    local_r, _ = reco.recommend(selected_title, "Any", 6, 0, 0.0, "Local Only", "Similarity")
    if not local_r:
        return _msg_info("No similar books found in the local library.")
    return reco.format_books(local_r, [])


def _ai_explain(query_val: str, selected_title: str, results: list) -> str:
    if not llm.is_enabled:
        return _msg_err("AI is not connected. Open AI Configuration and connect a provider.")
    if not selected_title:
        return _msg_err("Select a book first.")
    book = next((b for b in results if b.get("title") == selected_title), None)
    if not book:
        return _msg_err("Book not found in current results.")
    explanation = llm.explain_match(query_val, book)
    if not explanation:
        return _msg_info("Could not generate an explanation. Please try again.")
    title_safe = html_mod.escape(selected_title)
    exp_safe   = html_mod.escape(explanation)
    return (
        f'<div class="msg-info">'
        f'<strong>Why "{title_safe}" matches your search:</strong><br><br>'
        f'{exp_safe}</div>'
    )


def _export_results_pdf(results: list) -> str | None:
    if not results:
        return None
    try:
        path = export_books_pdf(results, title="Iqra — Search Results")
        return path
    except Exception as exc:
        logger.error("PDF export failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# AI Librarian tab
# ---------------------------------------------------------------------------
def _chat(
    msg:       str,
    history:   list,
    thread_id: str,
) -> tuple[list, str]:
    if not msg.strip():
        return history, ""
    reply = agent_mgr.chat(msg.strip(), thread_id)
    history = history + [
        {"role": "user",      "content": msg.strip()},
        {"role": "assistant", "content": reply},
    ]
    return history, ""


def _clear_chat() -> list:
    return []


def _rl_titles_for_dd() -> gr.update:
    titles = [b.get("title", "") for b in reading_list_mgr.get_all()]
    return gr.update(choices=titles, value=None)


def _concierge_ai_status() -> str:
    if llm.is_enabled:
        return '<div class="msg-ok" style="margin:0 0 .75rem;">✓ AI connected — concierge is active.</div>'
    return '<div class="msg-err" style="margin:0 0 .75rem;">⚠ AI not connected. Open <strong>AI Configuration</strong> above to enable the full AI Concierge.</div>'


def _reset_follow_up() -> str:
    return _empty_state_html(
        "Follow-up insights will appear here",
        "Select a result to compare similar books or request an AI explanation for the match.",
    )


# ---------------------------------------------------------------------------
# Analytics tab
# ---------------------------------------------------------------------------
def _build_analytics() -> tuple:
    """Return (fig_rating, fig_cats, fig_year, stats_html)."""
    # Placeholder figures for error fallback
    def _empty_fig(msg: str) -> plt.Figure:
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.text(0.5, 0.5, msg, ha="center", va="center",
                transform=ax.transAxes, color="#7A8DA8", fontsize=12)
        ax.set_axis_off()
        fig.patch.set_facecolor("white")
        return fig

    try:
        df = pd.read_csv(settings.csv_path, dtype=str).fillna("")
    except FileNotFoundError:
        empty_html = _empty_state_html("No library data found", "Analytics will appear once the catalogue file is available.")
        return _empty_fig("No data"), _empty_fig("No data"), _empty_fig("No data"), empty_html

    df["average_rating"]  = pd.to_numeric(df["average_rating"],  errors="coerce")
    df["published_year"]  = pd.to_numeric(df["published_year"],  errors="coerce")
    df["ratings_count"]   = pd.to_numeric(df.get("ratings_count", pd.Series(dtype=str)), errors="coerce")
    df["num_pages"]       = pd.to_numeric(df.get("num_pages",     pd.Series(dtype=str)), errors="coerce")

    total       = len(df)
    avg_rating  = df["average_rating"].dropna().mean()
    total_pages = int(df["num_pages"].dropna().sum())
    n_cats      = df.get("categories", pd.Series(dtype=str)).dropna().str.split(",").explode().str.strip().nunique()

    # ── Rating histogram ────────────────────────────────────────────
    fig1, ax1 = plt.subplots(figsize=(7, 3.5))
    ratings = df["average_rating"].dropna()
    ax1.hist(ratings, bins=25, color="#0F766E", alpha=0.85, edgecolor="white", linewidth=0.5)
    ax1.set_xlabel("Average Rating", fontsize=10)
    ax1.set_ylabel("Number of Books", fontsize=10)
    ax1.set_title("Rating Distribution", fontsize=12, fontweight="bold")
    ax1.spines[["top", "right"]].set_visible(False)
    ax1.set_facecolor("#F8FAFC")
    fig1.patch.set_facecolor("white")
    fig1.tight_layout()

    # ── Top categories ──────────────────────────────────────────────
    cats = df.get("categories", pd.Series(dtype=str)).dropna()
    cats = cats.str.split(",").explode().str.strip()
    cats = cats[cats != ""]
    top_cats = cats.value_counts().head(12)

    fig2, ax2 = plt.subplots(figsize=(7, 3.8))
    colors = ["#0F766E"] * len(top_cats)
    colors[0] = "#0B5F58"
    top_cats.plot(kind="barh", ax=ax2, color=list(reversed(colors)), alpha=0.88)
    ax2.set_xlabel("Number of Books", fontsize=10)
    ax2.set_title("Top Categories", fontsize=12, fontweight="bold")
    ax2.invert_yaxis()
    ax2.spines[["top", "right"]].set_visible(False)
    ax2.set_facecolor("#F8FAFC")
    fig2.patch.set_facecolor("white")
    fig2.tight_layout()

    # ── Publication year trend ───────────────────────────────────────
    year_counts = (
        df["published_year"]
        .dropna()
        .astype(int)
        .pipe(lambda s: s[s > 1900])
        .value_counts()
        .sort_index()
    )

    fig3, ax3 = plt.subplots(figsize=(7, 3.5))
    ax3.fill_between(
        year_counts.index, year_counts.values,
        alpha=0.18, color="#C69235",
    )
    ax3.plot(
        year_counts.index, year_counts.values,
        color="#C69235", linewidth=2,
    )
    ax3.set_xlabel("Publication Year", fontsize=10)
    ax3.set_ylabel("Books Published", fontsize=10)
    ax3.set_title("Publication Trend", fontsize=12, fontweight="bold")
    ax3.spines[["top", "right"]].set_visible(False)
    ax3.set_facecolor("#F8FAFC")
    fig3.patch.set_facecolor("white")
    fig3.tight_layout()

    # ── Stats HTML ──────────────────────────────────────────────────
    stats_html = f"""
<div class="stat-cards">
  <div class="stat-card stat-blue">
    <div class="stat-value">{total:,}</div>
    <div class="stat-label">Total Books</div>
  </div>
  <div class="stat-card stat-amber">
    <div class="stat-value">{avg_rating:.2f}</div>
    <div class="stat-label">Avg Rating</div>
  </div>
  <div class="stat-card stat-green">
    <div class="stat-value">{n_cats}</div>
    <div class="stat-label">Categories</div>
  </div>
  <div class="stat-card stat-purple">
    <div class="stat-value">{total_pages:,}</div>
    <div class="stat-label">Total Pages</div>
  </div>
</div>"""

    return fig1, fig2, fig3, stats_html


# ---------------------------------------------------------------------------
# Reading List tab
# ---------------------------------------------------------------------------
def _load_reading_list() -> str:
    return reading_list_mgr.to_html()


def _rl_remove(title: str) -> tuple[str, str]:
    if not title.strip():
        return reading_list_mgr.to_html(), _msg_err("Enter a title to remove.")
    msg = reading_list_mgr.remove(title.strip())
    if "not found" in msg:
        return reading_list_mgr.to_html(), _msg_err(msg)
    return reading_list_mgr.to_html(), _msg_ok(msg)


def _rl_clear() -> tuple[str, str]:
    msg = reading_list_mgr.clear()
    return reading_list_mgr.to_html(), _msg_ok(msg)


def _rl_export_pdf() -> tuple[str | None, str]:
    books = reading_list_mgr.get_all()
    if not books:
        return None, _msg_err("Reading list is empty — nothing to export.")
    try:
        path = export_books_pdf(books, title="Iqra — My Reading List")
        return path, _msg_ok(f"PDF saved: {Path(path).name}")
    except Exception as exc:
        logger.error("Reading list PDF export error: %s", exc)
        return None, _msg_err(f"Export failed: {exc}")


# ---------------------------------------------------------------------------
# Add Book handler
# ---------------------------------------------------------------------------
def _add_book(
    isbn13:          str,
    isbn10:          str,
    title:           str,
    subtitle:        str,
    authors:         str,
    categories:      list[str],
    thumbnail:       str,
    description:     str,
    published_year:  int | float,
    average_rating:  float,
    num_pages:       int | float,
    ratings_count:   int | float,
) -> str:
    isbn13 = str(isbn13).strip()
    isbn10 = str(isbn10).strip()

    if not (isbn13.isdigit() and len(isbn13) == 13):
        return _msg_err("ISBN-13 must be exactly 13 digits.")
    _isbn10_body  = isbn10[:-1] if isbn10 else ""
    _isbn10_check = isbn10[-1].upper() if isbn10 else ""
    if not (
        len(isbn10) == 10
        and _isbn10_body.isdigit()
        and (_isbn10_check.isdigit() or _isbn10_check == "X")
    ):
        return _msg_err("ISBN-10 must be exactly 10 characters (digits, last may be 'X').")
    if not title.strip():
        return _msg_err("Title is required.")
    if not authors.strip():
        return _msg_err("Authors is required.")
    if not categories:
        return _msg_err("Select at least one category.")
    try:
        year = int(published_year)
        if not (1000 <= year <= 9999):
            raise ValueError
    except (ValueError, TypeError):
        return _msg_err("Published Year must be a 4-digit year (e.g. 2023).")
    try:
        rating = float(average_rating)
        if not (0.0 <= rating <= 5.0):
            raise ValueError
    except (ValueError, TypeError):
        return _msg_err("Average Rating must be between 0.0 and 5.0.")
    try:
        pages = int(num_pages)
        if pages < 1:
            raise ValueError
    except (ValueError, TypeError):
        return _msg_err("Pages must be a positive integer.")
    try:
        r_count = int(ratings_count)
        if r_count < 0:
            raise ValueError
    except (ValueError, TypeError):
        return _msg_err("Ratings Count must be 0 or greater.")

    record = {
        "isbn13":         isbn13,
        "isbn10":         isbn10,
        "title":          title.strip(),
        "subtitle":       subtitle.strip(),
        "authors":        authors.strip(),
        "categories":     ",".join(categories),
        "thumbnail":      thumbnail.strip(),
        "description":    description.strip(),
        "published_year": year,
        "average_rating": rating,
        "num_pages":      pages,
        "ratings_count":  r_count,
    }
    result = manager.add_book(record)
    reco.reload_index()
    hybrid_ret.reload(embed_fn=reco._embed)
    msg = result.replace("✅ ", "")

    thumb = thumbnail.strip()
    safe_thumb = thumb if thumb.startswith(("http://", "https://")) else ""
    preview = (
        f"<img src='{html_mod.escape(safe_thumb)}' style='max-height:180px;"
        f"margin-top:12px;border-radius:8px;border:1px solid var(--border)' />"
        if safe_thumb else ""
    )
    return _msg_ok(msg) + preview


# ---------------------------------------------------------------------------
# Remove Book handler
# ---------------------------------------------------------------------------
def _remove_book(title: str) -> str:
    result = manager.remove_book(title)
    if result.startswith("✅"):
        reco.reload_index()
        hybrid_ret.reload(embed_fn=reco._embed)
        return _msg_ok(result.replace("✅ ", ""))
    return _msg_err(result.replace("❌ ", ""))


# ---------------------------------------------------------------------------
# Browse handler
# ---------------------------------------------------------------------------
def _browse(search_query: str, page: int) -> tuple[str, int, int, str]:
    csv_path = settings.csv_path
    try:
        df = pd.read_csv(csv_path, dtype=str).fillna("")
    except FileNotFoundError:
        return _empty_state_html("Library data not found", "The catalogue file could not be loaded."), 1, 1, "Page 1 / 1"

    q = search_query.strip().lower()
    if q:
        mask = (
            df.get("title",       pd.Series(dtype=str)).str.lower().str.contains(q, na=False)
            | df.get("authors",   pd.Series(dtype=str)).str.lower().str.contains(q, na=False)
            | df.get("categories",pd.Series(dtype=str)).str.lower().str.contains(q, na=False)
        )
        df = df[mask]

    total       = len(df)
    total_pages = max(1, (total + _BROWSE_PAGE_SIZE - 1) // _BROWSE_PAGE_SIZE)
    page        = max(1, min(page, total_pages))
    start       = (page - 1) * _BROWSE_PAGE_SIZE
    df_page     = df.iloc[start: start + _BROWSE_PAGE_SIZE]

    if df_page.empty:
        return _empty_state_html("No books matched your filter", "Try a broader title, author, or category search."), 1, 1, "Page 1 / 1"

    rows = ""
    for _, row in df_page.iterrows():
        thumb = row.get("thumbnail", "")
        safe_thumb = html_mod.escape(thumb) if thumb.startswith(("http://", "https://")) else ""
        cover = (
            f"<img src='{safe_thumb}' class='table-cover-image' alt='Book cover' />"
            if safe_thumb else "<span class='table-placeholder'>No cover</span>"
        )
        rows += (
            f"<tr>"
            f"<td>"
            f"<div class='table-book'>"
            f"<div class='table-cover'>{cover}</div>"
            f"<div>"
            f"<div class='table-title'>{html_mod.escape(str(row.get('title', '')))}</div>"
            f"<div class='table-subtle'>{html_mod.escape(str(row.get('authors', '')))}</div>"
            f"</div>"
            f"</div>"
            f"</td>"
            f"<td>{html_mod.escape(str(row.get('categories', ''))[:44])}</td>"
            f"<td>{html_mod.escape(str(row.get('published_year', '')))}</td>"
            f"<td>{html_mod.escape(str(row.get('average_rating', '')))}</td>"
            f"<td>{html_mod.escape(str(row.get('num_pages', '')))}</td>"
            f"</tr>"
        )

    end_row = min(start + _BROWSE_PAGE_SIZE, total)
    table = (
        '<div class="results-overview">'
        f"<div class='results-kpi'><span class='results-kpi-value'>{total:,}</span><span class='results-kpi-label'>Matching titles</span></div>"
        f"<div class='results-kpi'><span class='results-kpi-value'>{page}</span><span class='results-kpi-label'>Current page</span></div>"
        f"<div class='results-kpi'><span class='results-kpi-value'>{total_pages}</span><span class='results-kpi-label'>Total pages</span></div>"
        "</div>"
        '<div class="browse-wrap">'
        '<table class="browse-table"><thead><tr>'
        "<th>Book</th><th>Categories</th><th>Year</th><th>Rating</th><th>Pages</th>"
        f"</tr></thead><tbody>{rows}</tbody></table></div>"
        f"<p style='text-align:center;margin-top:.65rem;color:var(--muted);font-size:.88rem;'>"
        f"Showing {start+1}-{end_row} of {total} books</p>"
    )
    return table, page, total_pages, f"Page {page} / {total_pages}"


# ---------------------------------------------------------------------------
# AI status helpers
# ---------------------------------------------------------------------------
def _initial_ai_status() -> str:
    if llm.is_enabled:
        safe_status = html_mod.escape(llm.status)
        return (
            '<div class="ai-pill-wrap">'
            f'<span class="ai-pill ai-pill-on">'
            f'<span class="ai-pill-dot"></span>AI connected: {safe_status}'
            f'</span></div>'
        )
    return (
        '<div class="ai-pill-wrap">'
        '<span class="ai-pill ai-pill-off">'
        '<span class="ai-pill-dot"></span>AI features are offline. Open AI configuration to enable them.</span>'
        '</div>'
    )


def _refresh_ai_status() -> str:
    return _initial_ai_status()


# ---------------------------------------------------------------------------
# Hero section HTML (reads live stats from CSV)
# ---------------------------------------------------------------------------
def _hero_html() -> str:
    try:
        df = pd.read_csv(settings.csv_path, dtype=str).fillna("")
        total   = f"{len(df):,}"
        avg_r   = pd.to_numeric(df["average_rating"], errors="coerce").dropna().mean()
        avg_str = f"{avg_r:.1f}"
        n_cats  = (
            df.get("categories", pd.Series(dtype=str))
            .dropna().str.split(",").explode().str.strip()
            .replace("", pd.NA).dropna().nunique()
        )
    except Exception:
        total, avg_str, n_cats = "6,800+", "4.1", "21"

    return f"""
<section class="hero">
  <div class="hero-grid">
    <div class="hero-copy">
      <div class="hero-kicker">Client-ready discovery workspace</div>
      <h1 class="hero-title">Modern library discovery<br><span>built to impress</span></h1>
      <p>
        Iqra brings semantic search, AI-assisted guidance, live collection insights,
        and library administration into one polished interface for demos, operators,
        and end users.
      </p>
      <div class="hero-chip-row">
        <span class="hero-chip">Semantic recommendations</span>
        <span class="hero-chip">AI librarian workflow</span>
        <span class="hero-chip">Live analytics</span>
        <span class="hero-chip">Collection management</span>
      </div>
    </div>
    <div class="hero-panel">
      <div class="hero-panel-heading">
        <div>
          <h3>Library snapshot</h3>
          <p>Live metrics from the local catalogue keep the interface grounded in real collection data.</p>
        </div>
      </div>
      <div class="hero-stats">
        <div class="hstat">
          <div class="hstat-val">{total}</div>
          <div class="hstat-lbl">Indexed books</div>
        </div>
        <div class="hstat">
          <div class="hstat-val">{n_cats}</div>
          <div class="hstat-lbl">Categories</div>
        </div>
        <div class="hstat">
          <div class="hstat-val">{avg_str}</div>
          <div class="hstat-lbl">Average rating</div>
        </div>
        <div class="hstat">
          <div class="hstat-val">4</div>
          <div class="hstat-lbl">AI providers</div>
        </div>
      </div>
      <p class="hero-note">
        The redesigned workspace makes recommendations, insights, and admin tasks
        feel cohesive instead of scattered across separate screens.
      </p>
    </div>
  </div>
</section>
"""


# =============================================================================
# Gradio Application
# =============================================================================
_JS_DARK_DEFAULT = """
() => {
  const root = document.documentElement;
  const saved = localStorage.getItem('theme') || 'light';
  root.classList.toggle('dark', saved === 'dark');
  requestAnimationFrame(() => {
    const btn = document.getElementById('theme-btn');
    if (btn) {
      btn.textContent = saved === 'dark' ? 'Switch to light' : 'Switch to dark';
    }
  });
}
"""

with gr.Blocks(css=_CSS, theme=_theme, js=_JS_DARK_DEFAULT, title="Iqra Digital Library") as app:

    # ── Header ───────────────────────────────────────────────────────────
    gr.HTML("""
<header class="app-header">
  <div class="app-header-inner">
    <div class="brand-lockup">
      <div class="brand-mark">
        <img src="https://diplotech-solutions.com/assets/img/Diplotech_Logo_2.png" alt="Iqra Digital Library" />
      </div>
      <div>
        <p class="brand-title">Iqra Digital Library</p>
        <p class="brand-tag">Professional discovery, analytics, and collection management workspace</p>
      </div>
    </div>
    <div class="header-tools">
      <button class="btn-theme" id="theme-btn" title="Toggle theme"
              onclick="
                const root = document.documentElement;
                const isDark = !root.classList.contains('dark');
                root.classList.toggle('dark', isDark);
                localStorage.setItem('theme', isDark ? 'dark' : 'light');
                this.textContent = isDark ? 'Switch to light' : 'Switch to dark';
              ">Switch to dark</button>
    </div>
  </div>
</header>
""")

    hero_out = gr.HTML(_hero_html())

    # ── AI Settings Accordion ─────────────────────────────────────────────
    with gr.Accordion("AI Configuration", open=False,
                      elem_classes="ai-panel"):
        gr.HTML("""<div style="padding:.4rem 0 .25rem;font-size:.88rem;color:var(--muted);">
          Connect Anthropic, OpenAI, Gemini, or local Ollama to enable AI query
          expansion, match explanations, and the conversational library assistant.
        </div>""")
        with gr.Row():
            ai_provider_radio = gr.Radio(
                choices=["claude", "openai", "gemini", "ollama"],
                value="ollama" if llm.is_enabled and llm._provider == "ollama" else "claude",
                label="Provider",
                scale=2,
            )
            _init_models = PROVIDER_MODELS.get(
                llm._provider if llm.is_enabled else "claude",
                PROVIDER_MODELS["claude"],
            )
            ai_model_dd = gr.Dropdown(
                choices=_init_models,
                value=llm._model if llm.is_enabled else _init_models[0],
                label="Model",
                scale=2,
            )
            ai_connect_btn = gr.Button("Connect", variant="primary", scale=1)
        ai_status_html = gr.HTML(
            f'<span class="ai-status-ok">{html_mod.escape(llm.status)}</span>'
            if llm.is_enabled else
            '<span class="ai-status-off">Not connected. AI features are currently disabled.</span>'
        )

        ai_provider_radio.change(
            fn=_update_model_choices,
            inputs=ai_provider_radio,
            outputs=ai_model_dd,
        )
        ai_connect_evt = ai_connect_btn.click(
            fn=_ai_connect,
            inputs=[ai_provider_radio, ai_model_dd],
            outputs=ai_status_html,
        )

    # AI status pill (always visible, reflects current connection)
    ai_pill_out = gr.HTML(_initial_ai_status(), elem_classes="status-ribbon")
    ai_connect_evt.then(fn=_refresh_ai_status, outputs=ai_pill_out)

    # ── Tabs ─────────────────────────────────────────────────────────────
    with gr.Tabs():

        # ── 1. Recommend ─────────────────────────────────────────────────
        with gr.TabItem("Discovery"):
            with gr.Column(elem_classes="tab-wrap"):
                gr.HTML(_workspace_intro_html(
                    "Reader Discovery",
                    "Design a recommendation journey that feels premium",
                    "Blend local holdings, external discovery, and optional AI retrieval upgrades in one focused workspace.",
                    ["Semantic search", "External discovery", "RAG enhancements", "Shortlist actions"],
                ))

                with gr.Row():
                    with gr.Column(scale=4):
                        with gr.Group(elem_classes="search-hero"):
                            gr.HTML('<div class="search-hero-label">Describe the kind of reading experience you want</div>')
                            gr.HTML('<p class="workspace-card-copy">Use audience, subject, tone, or context. The system will rank local and external matches side by side.</p>')
                            with gr.Row():
                                query_box = gr.Textbox(
                                    placeholder="e.g. Executive leadership books for first-time managers",
                                    label="",
                                    show_label=False,
                                    lines=1,
                                    scale=5,
                                )
                                search_btn = gr.Button("Generate Recommendations", variant="primary", scale=1)
                            with gr.Row():
                                search_prompt_1 = gr.Button("Leadership shortlist", variant="secondary")
                                search_prompt_2 = gr.Button("STEM books for teenagers", variant="secondary")
                            with gr.Row():
                                search_prompt_3 = gr.Button("Arabian mystery with strong atmosphere", variant="secondary")
                                search_prompt_4 = gr.Button("Beginner-friendly AI books", variant="secondary")

                        with gr.Group(elem_classes="filter-card"):
                            gr.HTML('<div class="search-hero-label">Search controls</div>')
                            with gr.Row():
                                lang_dd = gr.Dropdown(
                                    list(settings.languages.keys()), value="Any", label="Language", scale=1)
                                scope_dd = gr.Dropdown(
                                    list(settings.search_modes), value="Both", label="Search Scope", scale=1)
                                cat_dd = gr.Dropdown(
                                    ["Any"] + _CATEGORIES, value="Any", label="Category", scale=1)
                            with gr.Row():
                                sort_dd = gr.Dropdown(
                                    list(settings.sort_options), value="Rating", label="Sort By", scale=1)
                                ai_search_chk = gr.Checkbox(
                                    label="Enable AI Retrieval",
                                    value=llm.is_enabled,
                                    info="Use AI query expansion when a provider is connected.",
                                    scale=1,
                                )
                            with gr.Row():
                                local_sl = gr.Slider(1, 20, value=6, step=1, label="Local Results")
                                ext_sl = gr.Slider(1, 20, value=6, step=1, label="External Results")
                            rating_sl = gr.Slider(0.0, 5.0, value=0.0, step=0.5, label="Minimum Rating")

                        with gr.Accordion("Retrieval Enhancements", open=False):
                            gr.HTML("""<p style='font-size:.85rem;color:var(--muted);margin:.2rem 0 .8rem;'>
                              These options require a connected AI provider and add extra retrieval depth for more demanding searches.
                            </p>""")
                            with gr.Row():
                                use_hyde_chk = gr.Checkbox(
                                    label="HyDE",
                                    value=False,
                                    info="Generate an ideal book description before searching.",
                                )
                                use_mq_chk = gr.Checkbox(
                                    label="Multi-Query + RRF",
                                    value=False,
                                    info="Search several AI-generated query variations and merge the rankings.",
                                )
                                use_rr_chk = gr.Checkbox(
                                    label="Cross-Encoder Re-rank",
                                    value=False,
                                    info="Re-score shortlisted results for better precision.",
                                )

                        with gr.Group(elem_classes="action-strip"):
                            gr.HTML('<div class="action-strip-label">Selected title actions</div>')
                            book_dd = gr.Dropdown(
                                choices=[],
                                label="Choose a recommended book",
                                interactive=True,
                                allow_custom_value=False,
                            )
                            with gr.Row():
                                save_rl_btn = gr.Button("Save to Reading List", variant="secondary", scale=1)
                                similar_btn = gr.Button("Find Similar", scale=1)
                            with gr.Row():
                                explain_btn = gr.Button("Explain Match", variant="secondary", scale=1)
                                export_pdf_btn = gr.Button("Export Recommendations", scale=1)
                            action_msg = gr.HTML()
                            export_file = gr.File(label="Recommendation PDF")

                    with gr.Column(scale=8):
                        results_html = gr.HTML(_empty_state_html(
                            "Recommendation results will appear here",
                            "Start with a discovery brief on the left to generate curated local and external matches.",
                        ))
                        similar_html = gr.HTML(_empty_state_html(
                            "Follow-up insights will appear here",
                            "Select a result to compare similar books or request an AI explanation for the match.",
                        ))
                        results_state = gr.State([])

                # ── Event wiring ──────────────────────────────────────────
                _search_inputs = [
                    query_box, lang_dd, local_sl, ext_sl,
                    rating_sl, scope_dd, sort_dd, ai_search_chk,
                    use_hyde_chk, use_mq_chk, use_rr_chk,
                    cat_dd,
                ]

                _sp_outs = [results_html, book_dd, results_state]
                (search_prompt_1.click(fn=lambda: "Executive leadership books for first-time managers", outputs=query_box)
                    .then(fn=_do_recommend, inputs=_search_inputs, outputs=_sp_outs)
                    .then(fn=_reset_follow_up, outputs=similar_html)
                    .then(fn=lambda: "", outputs=action_msg)
                    .then(fn=lambda: None, outputs=export_file))
                (search_prompt_2.click(fn=lambda: "STEM books for teenagers who enjoy hands-on experiments", outputs=query_box)
                    .then(fn=_do_recommend, inputs=_search_inputs, outputs=_sp_outs)
                    .then(fn=_reset_follow_up, outputs=similar_html)
                    .then(fn=lambda: "", outputs=action_msg)
                    .then(fn=lambda: None, outputs=export_file))
                (search_prompt_3.click(fn=lambda: "An atmospheric mystery set in the Arab world", outputs=query_box)
                    .then(fn=_do_recommend, inputs=_search_inputs, outputs=_sp_outs)
                    .then(fn=_reset_follow_up, outputs=similar_html)
                    .then(fn=lambda: "", outputs=action_msg)
                    .then(fn=lambda: None, outputs=export_file))
                (search_prompt_4.click(fn=lambda: "Beginner-friendly books that explain artificial intelligence clearly", outputs=query_box)
                    .then(fn=_do_recommend, inputs=_search_inputs, outputs=_sp_outs)
                    .then(fn=_reset_follow_up, outputs=similar_html)
                    .then(fn=lambda: "", outputs=action_msg)
                    .then(fn=lambda: None, outputs=export_file))

                search_evt = search_btn.click(
                    fn=_do_recommend,
                    inputs=_search_inputs,
                    outputs=[results_html, book_dd, results_state],
                )
                search_evt.then(
                    fn=lambda: _empty_state_html(
                        "Follow-up insights will appear here",
                        "Select a result to compare similar books or request an AI explanation for the match.",
                    ),
                    outputs=similar_html,
                )
                search_evt.then(fn=lambda: "", outputs=action_msg)
                search_evt.then(fn=lambda: None, outputs=export_file)

                submit_search_evt = query_box.submit(
                    fn=_do_recommend,
                    inputs=_search_inputs,
                    outputs=[results_html, book_dd, results_state],
                )
                submit_search_evt.then(
                    fn=lambda: _empty_state_html(
                        "Follow-up insights will appear here",
                        "Select a result to compare similar books or request an AI explanation for the match.",
                    ),
                    outputs=similar_html,
                )
                submit_search_evt.then(fn=lambda: "", outputs=action_msg)
                submit_search_evt.then(fn=lambda: None, outputs=export_file)

                save_evt = save_rl_btn.click(
                    fn=_save_to_rl,
                    inputs=[book_dd, results_state],
                    outputs=action_msg,
                )
                similar_btn.click(
                    fn=_find_similar,
                    inputs=book_dd,
                    outputs=similar_html,
                )
                explain_btn.click(
                    fn=_ai_explain,
                    inputs=[query_box, book_dd, results_state],
                    outputs=action_msg,
                )
                export_pdf_btn.click(
                    fn=_export_results_pdf,
                    inputs=results_state,
                    outputs=export_file,
                )

        # ── 2. AI Librarian ───────────────────────────────────────────────
        with gr.TabItem("AI Concierge"):
            with gr.Column(elem_classes="tab-wrap"):
                gr.HTML(_workspace_intro_html(
                    "Conversational Help",
                    "Use the AI concierge for natural-language discovery",
                    "The assistant can search the catalogue, recommend titles, explain matches, and work with the reading list in plain language.",
                    ["Natural-language search", "Reading list actions", "Recommendation help", "AI-enabled"],
                ))

                with gr.Row():
                    with gr.Column(scale=4):
                        gr.HTML("""<div class="intro-banner">
                          <strong>How to use it</strong><br>
                          Ask for recommendations, follow-up questions, shortlist support, or library navigation help.
                          This workspace is best when an AI provider is connected in the configuration panel above.
                        </div>""")
                        with gr.Group(elem_classes="prompt-panel"):
                            gr.HTML('<div class="search-hero-label">Quick prompts</div>')
                            gr.HTML('<p class="workspace-card-copy">Use one of these starters, then refine the conversation naturally.</p>')
                            with gr.Row():
                                chat_prompt_1 = gr.Button("Find books about ethical AI", variant="secondary")
                                chat_prompt_2 = gr.Button("Suggest thrillers set in Cairo", variant="secondary")
                            with gr.Row():
                                chat_prompt_3 = gr.Button("What is similar to Dune?", variant="secondary")
                                chat_prompt_4 = gr.Button("Show my reading list", variant="secondary")

                    with gr.Column(scale=8):
                        ai_concierge_warn = gr.HTML(_concierge_ai_status())
                        chatbot = gr.Chatbot(
                            type="messages",
                            height=500,
                            label="Iqra AI Concierge",
                            show_copy_button=True,
                            avatar_images=(None, "https://diplotech-solutions.com/assets/img/Diplotech_Logo_2.png"),
                        )
                        thread_id_state = gr.State(str(uuid.uuid4()))

                        with gr.Row():
                            chat_msg = gr.Textbox(
                                placeholder="Try: Suggest a leadership book for new managers",
                                label="",
                                lines=1,
                                scale=5,
                                show_label=False,
                            )
                            chat_send_btn = gr.Button("Send", variant="primary", scale=1)

                        with gr.Row():
                            chat_clear_btn = gr.Button("Clear Conversation", variant="stop", scale=1)
                            gr.HTML("""<small style='color:var(--muted);align-self:center;padding:.25rem .5rem;font-size:.82rem;'>
                              You can ask for discovery help, explanations, similar books, or reading-list actions.
                            </small>""")

                def _chat_and_clear(msg, history, thread_id):
                    return _chat(msg, history, thread_id)

                _chat_inputs = [chat_msg, chatbot, thread_id_state]
                _chat_outs   = [chatbot, chat_msg]
                (chat_prompt_1.click(fn=lambda: "Find books about ethical AI", outputs=chat_msg)
                    .then(fn=_chat_and_clear, inputs=_chat_inputs, outputs=_chat_outs))
                (chat_prompt_2.click(fn=lambda: "Suggest thrillers set in Cairo", outputs=chat_msg)
                    .then(fn=_chat_and_clear, inputs=_chat_inputs, outputs=_chat_outs))
                (chat_prompt_3.click(fn=lambda: "What is similar to Dune?", outputs=chat_msg)
                    .then(fn=_chat_and_clear, inputs=_chat_inputs, outputs=_chat_outs))
                (chat_prompt_4.click(fn=lambda: "Show my reading list", outputs=chat_msg)
                    .then(fn=_chat_and_clear, inputs=_chat_inputs, outputs=_chat_outs))
                ai_connect_evt.then(fn=_concierge_ai_status, outputs=ai_concierge_warn)

                chat_send_btn.click(
                    fn=_chat_and_clear,
                    inputs=[chat_msg, chatbot, thread_id_state],
                    outputs=[chatbot, chat_msg],
                )
                chat_msg.submit(
                    fn=_chat_and_clear,
                    inputs=[chat_msg, chatbot, thread_id_state],
                    outputs=[chatbot, chat_msg],
                )
                chat_clear_btn.click(fn=_clear_chat, outputs=chatbot)

        # ── 3. Analytics ──────────────────────────────────────────────────
        with gr.TabItem("Analytics"):
            with gr.Column(elem_classes="tab-wrap"):
                gr.HTML(_workspace_intro_html(
                    "Collection Insights",
                    "Track the shape and quality of the catalogue",
                    "Use the analytics workspace to understand collection breadth, ratings quality, and publication history at a glance.",
                    ["Ratings distribution", "Category mix", "Publication trend"],
                ))
                analytics_stats_html = gr.HTML()

                with gr.Row():
                    analytics_plot1 = gr.Plot(label="Rating Distribution")
                    analytics_plot2 = gr.Plot(label="Top Categories")
                analytics_plot3 = gr.Plot(label="Publication Year Trend")

                analytics_refresh_btn = gr.Button("Refresh Insights", variant="secondary")

                _analytics_outputs = [
                    analytics_plot1, analytics_plot2,
                    analytics_plot3, analytics_stats_html,
                ]
                analytics_refresh_btn.click(fn=_build_analytics, outputs=_analytics_outputs)

        # ── 4. Reading List ───────────────────────────────────────────────
        with gr.TabItem("Reading List"):
            with gr.Column(elem_classes="tab-wrap"):
                gr.HTML(_workspace_intro_html(
                    "Shortlist Management",
                    "Turn promising discoveries into a polished reading list",
                    "Manage shortlisted titles, remove entries quickly, and export a client-facing PDF when the list is ready.",
                    ["Save from discovery", "Remove by title", "Export PDF"],
                ))

                with gr.Row():
                    with gr.Column(scale=4):
                        gr.HTML("""<div class="intro-banner">
                          Build a shortlist from recommendation results, then return here to refine it for review sessions or client handoff.
                        </div>""")
                        with gr.Group(elem_classes="manage-card"):
                            gr.HTML('<div class="manage-card-title">Reading list controls</div>')
                            rl_remove_dd = gr.Dropdown(
                                choices=[b.get("title", "") for b in reading_list_mgr.get_all()],
                                label="Select title to remove",
                                interactive=True,
                                allow_custom_value=False,
                            )
                            with gr.Row():
                                rl_remove_btn = gr.Button("Remove Title", variant="stop", scale=1)
                                rl_export_btn = gr.Button("Export PDF", variant="secondary", scale=1)
                            rl_clear_btn = gr.Button("Clear List", variant="stop")
                            rl_msg_out = gr.HTML()
                            rl_file_out = gr.File(label="Reading List PDF")

                    with gr.Column(scale=8):
                        rl_html_out = gr.HTML()

                (rl_remove_btn.click(fn=_rl_remove, inputs=rl_remove_dd, outputs=[rl_html_out, rl_msg_out])
                    .then(fn=_rl_titles_for_dd, outputs=rl_remove_dd))
                rl_export_btn.click(fn=_rl_export_pdf, outputs=[rl_file_out, rl_msg_out])
                (rl_clear_btn.click(fn=_rl_clear, outputs=[rl_html_out, rl_msg_out])
                    .then(fn=_rl_titles_for_dd, outputs=rl_remove_dd))
                save_evt.then(fn=_load_reading_list, outputs=rl_html_out)
                save_evt.then(fn=_rl_titles_for_dd, outputs=rl_remove_dd)

        # ── 5. Browse Library ─────────────────────────────────────────────
        with gr.TabItem("Catalogue"):
            with gr.Column(elem_classes="tab-wrap"):
                gr.HTML(_workspace_intro_html(
                    "Catalogue Review",
                    "Browse the full collection with cleaner catalogue controls",
                    "Use the catalogue view to scan titles, authors, categories, and quality indicators without leaving the app.",
                    ["Paged catalogue", "Quick filtering", "Collection review"],
                ))

                with gr.Row():
                    with gr.Column(scale=4):
                        with gr.Group(elem_classes="catalog-note"):
                            gr.HTML('<div class="manage-card-title">Catalogue filter</div>')
                            browse_q = gr.Textbox(
                                label="Search the catalogue",
                                placeholder="Filter by title, author, or category",
                            )
                            browse_btn = gr.Button("Apply Filter", variant="primary")
                            gr.HTML("<p class='workspace-card-copy'>Results update in the table on the right and keep pagination intact.</p>")

                    with gr.Column(scale=8):
                        browse_html = gr.HTML()
                        _cur_page = gr.State(1)
                        _tot_pages = gr.State(1)

                        with gr.Row():
                            prev_btn = gr.Button("Previous", scale=1)
                            page_lbl = gr.Textbox(value="Page 1 / 1", interactive=False,
                                                  label="", scale=2, show_label=False)
                            next_btn = gr.Button("Next", scale=1)

                def _browse_page1(q: str) -> tuple:
                    return _browse(q, 1)

                def _browse_prev(q: str, pg: int, tp: int) -> tuple:
                    return _browse(q, max(1, pg - 1))

                def _browse_next(q: str, pg: int, tp: int) -> tuple:
                    return _browse(q, min(tp, pg + 1))

                _browse_outs = [browse_html, _cur_page, _tot_pages, page_lbl]

        # ── 6. Manage Library ─────────────────────────────────────────────
        with gr.TabItem("Library Admin"):
            with gr.Column(elem_classes="tab-wrap"):
                gr.HTML(_workspace_intro_html(
                    "Catalogue Operations",
                    "Manage the collection with a cleaner administration surface",
                    "Add new records with the metadata needed for discovery quality, or remove outdated titles with clear operational guardrails.",
                    ["Structured add form", "Safe removal", "Index refresh"],
                ))

                with gr.Row():
                    with gr.Column(scale=8):
                        with gr.Group(elem_classes="manage-card"):
                            gr.HTML('<div class="manage-card-title">Add a book</div>')
                            with gr.Row():
                                isbn13_box = gr.Textbox(label="ISBN-13 * (13 digits)")
                                isbn10_box = gr.Textbox(label="ISBN-10 * (10 digits)")
                            title_box = gr.Textbox(label="Title *")
                            subtitle_box = gr.Textbox(label="Subtitle")
                            authors_box = gr.Textbox(label="Authors * (comma-separated)")
                            cats_box = gr.CheckboxGroup(_CATEGORIES, label="Categories * (select at least one)")
                            thumb_box = gr.Textbox(
                                label="Cover Image URL",
                                placeholder="https://... (leave blank if unavailable)",
                            )
                            desc_box = gr.Textbox(label="Description", lines=3)
                            with gr.Row():
                                year_box = gr.Number(label="Published Year *", value=2024, precision=0)
                                rating_box = gr.Slider(0.0, 5.0, step=0.1, value=0.0, label="Average Rating")
                                pages_box = gr.Number(label="Pages *", value=1, precision=0)
                                rcount_box = gr.Number(label="Ratings Count", value=0, precision=0)
                            add_out = gr.HTML()
                            add_book_btn = gr.Button("Add to Library", variant="primary")

                    with gr.Column(scale=4):
                        gr.HTML("""<div class="intro-banner">
                          Use this area for controlled catalogue updates. New records are written to the dataset and the retrieval index is refreshed automatically.
                        </div>""")
                        with gr.Group(elem_classes="manage-card"):
                            gr.HTML('<div class="manage-card-title">Remove a book</div>')
                            gr.HTML("""<p style='font-size:.88rem;color:var(--muted);margin:0 0 .75rem;'>
                              Enter the exact title. Removal is case-insensitive and refreshes the library index immediately.
                            </p>""")
                            rem_box = gr.Textbox(label="Book title", placeholder="Enter the exact book title")
                            rem_out = gr.HTML()
                            remove_book_btn = gr.Button("Remove Book", variant="stop")

                add_book_evt = add_book_btn.click(
                    fn=_add_book,
                    inputs=[
                        isbn13_box, isbn10_box, title_box, subtitle_box,
                        authors_box, cats_box, thumb_box, desc_box,
                        year_box, rating_box, pages_box, rcount_box,
                    ],
                    outputs=add_out,
                )
                remove_book_evt = remove_book_btn.click(
                    fn=_remove_book,
                    inputs=rem_box,
                    outputs=rem_out,
                )
                add_book_evt.then(fn=_hero_html, outputs=hero_out).then(fn=_build_analytics, outputs=_analytics_outputs).then(
                    fn=lambda: _browse("", 1),
                    outputs=_browse_outs,
                )
                remove_book_evt.then(fn=_hero_html, outputs=hero_out).then(fn=_build_analytics, outputs=_analytics_outputs).then(
                    fn=lambda: _browse("", 1),
                    outputs=_browse_outs,
                )

    # ── Browse event wiring (must be outside the tab block) ─────────────
    browse_btn.click(fn=_browse_page1, inputs=browse_q, outputs=_browse_outs)
    browse_q.submit(fn=_browse_page1, inputs=browse_q, outputs=_browse_outs)
    prev_btn.click(fn=_browse_prev, inputs=[browse_q, _cur_page, _tot_pages], outputs=_browse_outs)
    next_btn.click(fn=_browse_next, inputs=[browse_q, _cur_page, _tot_pages], outputs=_browse_outs)

    # ── Auto-load on startup ─────────────────────────────────────────────
    app.load(fn=lambda: _browse("", 1), outputs=_browse_outs)
    app.load(fn=_load_reading_list,     outputs=rl_html_out)
    app.load(fn=_rl_titles_for_dd,      outputs=rl_remove_dd)
    app.load(fn=_build_analytics,       outputs=_analytics_outputs)
    app.load(fn=_refresh_ai_status,     outputs=ai_pill_out)
    app.load(fn=_concierge_ai_status,   outputs=ai_concierge_warn)
    app.load(fn=_hero_html,             outputs=hero_out)

    # ── Footer ───────────────────────────────────────────────────────────
    # Gradio's autogenerated API schema crashes on some callback signatures in
    # this app, but the UI does not need those internal handlers exposed.
    for _fn in app.fns.values():
        _fn.show_api = False

    gr.HTML("""
<footer class="iqra-footer">
  Iqra Digital Library combines Gradio, FAISS, LangGraph, sentence-transformer search,
  and external book discovery into one client-ready platform by
  <a href="https://diplotech-solutions.com" target="_blank" rel="noopener noreferrer">DiploTech Solutions</a>.
</footer>""")


# =============================================================================
# Entry point
# =============================================================================
if __name__ == "__main__":
    launch_host = settings.server_host
    if launch_host == "0.0.0.0" and not settings.gradio_share:
        launch_host = "127.0.0.1"

    logger.info(
        "Starting Iqra Digital Library on %s:%d  (share=%s, launch_host=%s)",
        settings.server_host,
        settings.server_port,
        settings.gradio_share,
        launch_host,
    )
    app.launch(
        server_name=launch_host,
        server_port=settings.server_port,
        share=settings.gradio_share,
        allowed_paths=[str(settings.base_dir)],
        show_api=False,
    )
