"""Generate AGENT_STATE_GRAPH_DETAILED.pdf — state graph + full documentation."""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF, XPos, YPos
from datetime import datetime
from PIL import Image as PILImage

# ── Palette ───────────────────────────────────────────────────────────────────
BLUE      = (43,  92, 230)
DARK      = (15,  23,  42)
MID       = (30,  58, 138)
LIGHT_BG  = (238, 242, 255)
MUTED     = (100, 110, 130)
WHITE     = (255, 255, 255)
TEAL      = (14, 165, 233)
VIOLET    = (139, 92, 246)
CODE_BG   = (245, 245, 245)
CODE_TEXT = (50,  50,  50)

PW = 190
LH = 5.5


def s(t: str) -> str:
    return str(t).encode("latin-1", errors="replace").decode("latin-1")


class Doc(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5, s("Iqra Digital Library v2  |  LangGraph ReAct Architecture"), align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")

    def h1(self, text: str) -> None:
        self.ln(3)
        self.set_fill_color(*BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 14)
        self.cell(PW, 10, s("  " + text), fill=True,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def h2(self, text: str, color: tuple = MID) -> None:
        self.ln(2)
        self.set_text_color(*color)
        self.set_font("Helvetica", "B", 11)
        self.multi_cell(PW, 7, s(text))
        self.set_draw_color(*color)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 100, self.get_y())
        self.ln(3)

    def h3(self, text: str, color: tuple = BLUE) -> None:
        self.ln(1)
        self.set_text_color(*color)
        self.set_font("Helvetica", "B", 9.5)
        self.multi_cell(PW, 6, s(text))
        self.ln(1)

    def body(self, text: str) -> None:
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 8.5)
        self.multi_cell(PW, LH, s(text))
        self.ln(1)

    def bullet(self, items: list[str], indent: int = 14) -> None:
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 8.5)
        for item in items:
            self.set_x(indent)
            self.cell(4, LH, s("-"))
            self.set_x(indent + 4)
            self.multi_cell(PW - indent - 4, LH, s(item))

    def kv(self, key: str, val: str, key_color: tuple = BLUE) -> None:
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*key_color)
        self.cell(42, LH, s(key + ":"))
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*DARK)
        self.multi_cell(PW - 42, LH, s(val))

    def code(self, text: str) -> None:
        self.set_fill_color(*CODE_BG)
        self.set_font("Courier", "", 7.5)
        self.set_text_color(*CODE_TEXT)
        self.multi_cell(PW, 4.5, s(text), fill=True)
        self.ln(1)

    def table_header(self, cols: list[str], widths: list[float]) -> None:
        self.set_fill_color(*BLUE)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 8)
        for col, w in zip(cols, widths):
            self.cell(w, 7, s(col), border=1, fill=True)
        self.ln()

    def table_row(self, cells: list[str], widths: list[float], even: bool = False) -> None:
        self.set_fill_color(*(LIGHT_BG if even else WHITE))
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 8)
        for cell, w in zip(cells, widths):
            self.cell(w, 7, s(cell), border=1, fill=True)
        self.ln()

    def rule(self) -> None:
        self.ln(2)
        self.set_draw_color(*LIGHT_BG)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)


# =============================================================================
pdf = Doc()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(10, 15, 10)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 1 — COVER
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.ln(18)
pdf.set_font("Helvetica", "B", 24)
pdf.set_text_color(*BLUE)
pdf.cell(PW, 14, s("LangGraph ReAct Architecture"),
         align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "B", 16)
pdf.set_text_color(*MID)
pdf.cell(PW, 10, s("Orchestrator + Worker State Graphs"),
         align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(4)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*MUTED)
pdf.cell(PW, 6,
         s("Iqra Digital Library v2  |  " + datetime.now().strftime("%B %Y")),
         align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(10)
pdf.set_draw_color(*BLUE)
pdf.set_line_width(0.8)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(6)

# overview box
pdf.set_fill_color(*LIGHT_BG)
pdf.rect(10, pdf.get_y(), PW, 38, style="F")
pdf.ln(4)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*BLUE)
pdf.cell(PW, 6, s("  System Overview"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "", 8.5)
pdf.set_text_color(*DARK)
pdf.set_x(10)
pdf.multi_cell(PW, LH, s(
    "  The Iqra Digital Library uses a three-layer LangGraph ReAct hierarchy. A central "
    "Orchestrator receives every user message and routes it to two specialist Worker agents "
    "— SearchWorker for book discovery and CuratorWorker for reading list management. Each "
    "layer is an independent ReAct graph: __start__ -> agent -> tools -> agent -> ... -> "
    "__end__. The Orchestrator holds MemorySaver conversation memory per session. Workers "
    "are stateless — each call is a fresh graph invocation."
))
pdf.ln(10)

# table of contents
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(*MID)
pdf.cell(PW, 7, s("Contents"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
toc = [
    ("1", "State Graph  —  Visual Diagram (all three agents)"),
    ("2", "Graph Anatomy  —  Nodes, Edges & Message Types"),
    ("3", "Orchestrator (LibraryAgent)  —  Role, Logic, Design"),
    ("4", "Search Worker  —  Role, 4 Tools, Decision Tree, Retrieval Stack"),
    ("5", "Curator Worker  —  Role, 4 Tools, Decision Tree, Data Schema"),
    ("6", "Message Flow  —  End-to-end walkthroughs"),
    ("7", "Memory & State  —  MemorySaver, thread_id, Checkpoints"),
    ("8", "Design Decisions  —  Why this architecture"),
]
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*DARK)
for num, title in toc:
    pdf.set_x(14)
    pdf.cell(8, 6, s(num + "."))
    pdf.cell(PW - 22, 6, s(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 2 — STATE GRAPH IMAGE
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("1.  State Graph  —  All Three Agents")
pdf.body(
    "The diagram below shows the actual LangGraph-generated state graph topology for the "
    "Orchestrator and both Worker agents. Every graph follows the same ReAct loop structure. "
    "What differs is only the tools available inside the 'tools' execution node."
)
pdf.ln(2)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
img_path = os.path.join(base_dir, "agent_state_graph.png")
with PILImage.open(img_path) as im:
    iw, ih = im.size
img_w = float(PW)
img_h = img_w * (ih / iw)
if img_h > 145:
    img_h = 145.0
    img_w = img_h * (iw / ih)

pdf.image(img_path, x=(210 - img_w) / 2, y=None, w=img_w, h=img_h)
pdf.ln(3)
pdf.set_font("Helvetica", "I", 7.5)
pdf.set_text_color(*MUTED)
pdf.cell(PW, 5,
         s("Figure 1 — Orchestrator (left)  |  Search Worker (centre)  |  Curator Worker (right)"),
         align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(3)
pdf.rule()

pdf.h3("Node Colour Legend")
legend = [
    ("Purple  __start__",    "Entry point — where the user input arrives"),
    ("Blue    agent",        "LLM node — reads message history, decides next action"),
    ("Teal    tools",        "Executor node — runs whichever tool the LLM chose"),
    ("Violet  __end__",      "Exit point — emits the final response to the caller"),
    ("Solid arrow",          "Always taken  (tools -> agent loops unconditionally)"),
    ("Dashed arrow",         "Conditional  (agent -> __end__ only when no tool_calls)"),
]
pdf.set_font("Helvetica", "", 8.5)
for label, desc in legend:
    pdf.set_text_color(*DARK)
    pdf.set_x(12)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(46, LH, s(label))
    pdf.set_font("Helvetica", "", 8.5)
    pdf.multi_cell(PW - 46, LH, s(desc))

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 3 — GRAPH ANATOMY
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("2.  Graph Anatomy  —  Nodes, Edges & Message Types")

pdf.h2("2.1  The Four Nodes (present in every graph)")
nw = [28, 30, 65, 67]
pdf.table_header(["Node", "Type", "What it does", "When it runs"], nw)
nodes = [
    ("__start__", "Entry",
     "Injects the incoming HumanMessage into graph state.",
     "Once per invoke() call, before anything else."),
    ("agent", "LLM call",
     "Passes full message history to the LLM. Returns AIMessage with tool_calls OR a plain AIMessage (final answer).",
     "Every iteration: first to decide, then again after each tool result."),
    ("tools", "Executor",
     "Executes every tool_call from the last AIMessage. Appends a ToolMessage per call.",
     "Only when agent node outputs tool_calls. Skipped when LLM answers directly."),
    ("__end__", "Exit",
     "Terminates the graph. Returns final state (all messages) to the caller.",
     "When agent produces an AIMessage with NO tool_calls."),
]
for i, row in enumerate(nodes):
    pdf.table_row(list(row), nw, even=(i % 2 == 0))

pdf.ln(4)

pdf.h2("2.2  The Four Edges")
ew = [52, 33, 105]
pdf.table_header(["Edge", "Type", "Condition / Reason"], ew)
edges = [
    ("__start__  ->  agent", "Static",
     "Always. Graph always starts by asking the LLM what to do next."),
    ("agent  ->  tools", "Conditional",
     "Taken when LLM last message contains tool_calls (it wants to run a tool)."),
    ("agent  ->  __end__", "Conditional",
     "Taken when LLM last message has NO tool_calls (producing final answer)."),
    ("tools  ->  agent", "Static",
     "Always. After every tool run, control returns to LLM to decide the next step."),
]
for i, row in enumerate(edges):
    pdf.table_row(list(row), ew, even=(i % 2 == 0))

pdf.ln(4)

pdf.h2("2.3  Message Types in State  (MessagesState list)")
pdf.body(
    "The graph state is a single list of BaseMessage objects. Every node reads "
    "the full list and appends its output. The LLM always receives the complete "
    "list as conversation context."
)
mw = [40, 34, 116]
pdf.table_header(["Message Type", "Created by", "Contains"], mw)
msgs = [
    ("HumanMessage", "User / invoke()",
     "Raw user text. Added before __start__ on every chat() call."),
    ("AIMessage (tool_calls)", "agent LLM",
     "Decision to call tools. Includes tool name + arguments as structured JSON."),
    ("ToolMessage", "tools node",
     "String result from a tool function. One ToolMessage per tool_call in the list."),
    ("AIMessage (final)", "agent LLM",
     "Natural-language reply with no tool_calls. Triggers transition to __end__."),
    ("SystemMessage (prompt=)", "Graph init",
     "System prompt injected at position 0 of every agent call. NOT stored in checkpoint."),
]
for i, row in enumerate(msgs):
    pdf.table_row(list(row), mw, even=(i % 2 == 0))

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 4 — ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("3.  Orchestrator  —  LibraryAgent  (agent.py)")

pdf.h2("3.1  Role")
pdf.body(
    "The Orchestrator is the single entry point for all user messages. app.py calls "
    "agent_mgr.chat(message, thread_id) — that method invokes this graph. The Orchestrator "
    "does NOT answer directly. Its job is to classify the user's intent and route to the "
    "correct specialist worker, then synthesise the worker result into a coherent reply."
)

pdf.h2("3.2  Key Properties")
props = [
    ("File",           "agent.py"),
    ("Class",          "LibraryAgent"),
    ("LangGraph",      "create_react_agent  with  MemorySaver  checkpointer"),
    ("Tools visible",  "search_worker(query: str),  curator_worker(instruction: str)"),
    ("Memory",         "MemorySaver — full message history persisted per thread_id"),
    ("Called from",    "app.py  _ai_connect() builds it;  _chat() invokes it each turn"),
    ("Stateful?",      "Yes — conversation history survives across multiple turns"),
]
for k, v in props:
    pdf.kv(k, v)

pdf.ln(2)
pdf.h2("3.3  Decision Logic")
pdf.body("The Orchestrator LLM routes with these rules (from the system prompt):")
pdf.bullet([
    "Search / discovery / recommendations  ->  call search_worker(query)",
    "Reading list: save / remove / view / count  ->  call curator_worker(instruction)",
    "Compound ('find X and save it')  ->  call search_worker, then curator_worker with result",
    "Conversational (greeting, clarification)  ->  respond directly, no worker needed",
])

pdf.ln(2)
pdf.h2("3.4  System Prompt")
pdf.code(
    'You are Iqra, a friendly digital library assistant.\n'
    '\n'
    'Two specialist workers you MUST delegate to:\n'
    '  search_worker  -> book discovery, recommendations, similar books, Google Books\n'
    '  curator_worker -> save / remove / view / count reading list\n'
    '\n'
    'Rules:\n'
    '  - Any book question -> search_worker\n'
    '  - Any reading list op -> curator_worker\n'
    '  - Compound request -> search_worker THEN curator_worker\n'
    '  - Never answer book questions from memory alone. Always delegate.'
)

pdf.h2("3.5  Why Use an Orchestrator?")
pdf.bullet([
    "Single responsibility per agent: each worker has a focused prompt optimised for its task",
    "Fewer tools = fewer mistakes: with 2 tools the LLM almost never routes incorrectly",
    "Compound requests handled naturally: 'find X and save it' calls both workers in sequence",
    "Easier debugging: isolate whether failure is at routing, search, or curation",
    "Scalability: add a new worker (AnalyticsWorker, ExportWorker) without touching others",
])

pdf.ln(2)
pdf.h2("3.6  Build Sequence")
pdf.bullet([
    "1. llm_provider.get_langchain_llm()  ->  LangChain BaseChatModel",
    "2. SearchWorker.build()  ->  builds inner ReAct graph with 4 search tools",
    "3. CuratorWorker.build()  ->  builds inner ReAct graph with 4 list tools",
    "4. create_react_agent(llm, [search_worker_tool, curator_worker_tool], checkpointer=MemorySaver(), prompt=...)",
    "5. Stored as agent_mgr._agent — ready for chat()",
])

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 5 — SEARCH WORKER
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("4.  Search Worker  (agents/search_agent.py)")

pdf.h2("4.1  Role")
pdf.body(
    "SearchWorker is a focused ReAct agent whose only job is to find books. It is invoked "
    "by the Orchestrator via the search_worker @tool wrapper. It runs its own complete "
    "ReAct loop — decides which search tool to call, calls it, reads the result, and returns "
    "a formatted book list string back to the Orchestrator. It has no memory: every call starts fresh."
)

pdf.h2("4.2  Key Properties")
sprops = [
    ("File",        "agents/search_agent.py"),
    ("Class",       "SearchWorker"),
    ("Tools",       "4 (search_local_library, search_google_books, find_similar_books, search_by_rating)"),
    ("Memory",      "None — stateless. Orchestrator holds all conversation memory."),
    ("Called by",   "Orchestrator  @tool  search_worker(query: str) -> str"),
    ("Returns",     "Formatted numbered book list string back to Orchestrator's tools node"),
]
for k, v in sprops:
    pdf.kv(k, v)

pdf.ln(2)
pdf.h2("4.3  Tools")
tw = [52, 48, 90]
pdf.table_header(["Tool", "Triggered when...", "Retrieval method"], tw)
search_tools = [
    ("search_local_library",
     "General book query",
     "HybridRetriever: BM25 + FAISS + KG 1-hop expansion. Top 6 results."),
    ("search_google_books",
     "Local results insufficient / user asks for new releases",
     "Live Google Books API. Up to 6 external results with covers + links."),
    ("find_similar_books",
     "'Books like X'  /  'Similar to X'",
     "BookRecommender FAISS cosine similarity on reference title embedding."),
    ("search_by_rating",
     "'Top rated'  /  'Highly rated X'",
     "HybridRetriever k=20 -> filter average_rating >= min_rating (default 4.0) -> top 6."),
]
for i, row in enumerate(search_tools):
    pdf.table_row(list(row), tw, even=(i % 2 == 0))

pdf.ln(3)
pdf.h2("4.4  Decision Tree")
pdf.bullet([
    "User: 'find me a fantasy book'       ->  search_local_library('fantasy')",
    "User: 'books like Dune'              ->  find_similar_books('Dune')",
    "User: 'top rated mystery novels'     ->  search_by_rating('mystery novels', 4.0)",
    "User: 'any new sci-fi releases?'     ->  search_google_books('new sci-fi 2025')",
    "Local returns nothing                ->  agent may chain to search_google_books",
])

pdf.ln(2)
pdf.h2("4.5  Hybrid Retrieval Stack  (what happens inside search_local_library)")
pdf.bullet([
    "Stage 1 — FAISS dense search: query embedded with SentenceTransformer -> cosine similarity "
    "over book_index.faiss -> top k*4 candidates.",
    "Stage 2 — Knowledge Graph expansion: each candidate expands 1 hop through the NetworkX KG. "
    "Edges: SAME_AUTHOR (w=1.00), SAME_CATEGORY (w=0.75), SEMANTIC_SIM cosine>=0.82. "
    "Expanded neighbours get graph_score = edge_weight.",
    "Stage 3 — Score fusion: min-max normalise both streams, "
    "fuse: final_score = 0.65 * faiss_score + 0.35 * graph_score. Re-rank. Return top k.",
])

pdf.ln(2)
pdf.h2("4.6  Why No Memory?")
pdf.body(
    "Workers are tools from the Orchestrator's perspective — semantically equivalent to "
    "search_local_library. Tools don't hold memory. The Orchestrator already has full "
    "conversation history in MemorySaver. If workers also held memory, state would be "
    "duplicated at two layers. The clean design: memory lives at one layer only."
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 6 — CURATOR WORKER
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("5.  Curator Worker  (agents/curator_agent.py)")

pdf.h2("5.1  Role")
pdf.body(
    "CuratorWorker is a focused ReAct agent whose only job is to manage the user's personal "
    "reading list. Invoked by the Orchestrator via the curator_worker @tool. Runs its own "
    "complete ReAct loop and is stateless per call. Reads/writes data/reading_list.json "
    "via the ReadingList class."
)

pdf.h2("5.2  Key Properties")
cprops = [
    ("File",      "agents/curator_agent.py"),
    ("Class",     "CuratorWorker"),
    ("Tools",     "4 (save_book, remove_book, view_reading_list, count_reading_list)"),
    ("Storage",   "data/reading_list.json  — JSON array, persisted to disk"),
    ("Memory",    "None — stateless. State lives in the JSON file, not the agent."),
    ("Called by", "Orchestrator  @tool  curator_worker(instruction: str) -> str"),
    ("Returns",   "Confirmation / list string back to Orchestrator's tools node"),
]
for k, v in cprops:
    pdf.kv(k, v)

pdf.ln(2)
pdf.h2("5.3  Tools")
cw2 = [48, 52, 90]
pdf.table_header(["Tool", "Triggered when...", "What it does"], cw2)
cur_tools = [
    ("save_book",
     "'Save this book'  /  'Add X to my list'",
     "ReadingList.add(book_dict). Deduplicates by title. Writes JSON. Returns confirmation."),
    ("remove_book",
     "'Remove X'  /  'Delete X from my list'",
     "ReadingList.remove(title). Exact title match. Returns confirmation or 'not found'."),
    ("view_reading_list",
     "'Show my list'  /  'What have I saved?'",
     "ReadingList.get_all(). Returns numbered list: title, author, rating, date saved."),
    ("count_reading_list",
     "'How many books?'  /  'How big is my list?'",
     "ReadingList.count. Returns 'You have N books in your reading list.'"),
]
for i, row in enumerate(cur_tools):
    pdf.table_row(list(row), cw2, even=(i % 2 == 0))

pdf.ln(3)
pdf.h2("5.4  Decision Tree")
pdf.bullet([
    "User: 'save Harry Potter'               ->  save_book(title='Harry Potter')",
    "User: 'save Dune by Frank Herbert 4.8'  ->  save_book('Dune', 'Frank Herbert', 4.8)",
    "User: 'remove Dune from my list'        ->  remove_book('Dune')",
    "User: 'show my reading list'            ->  view_reading_list()",
    "User: 'how many books have I saved?'    ->  count_reading_list()",
])

pdf.ln(2)
pdf.h2("5.5  Reading List Data Schema  (data/reading_list.json)")
pdf.code(
    '[\n'
    '  {\n'
    '    "title":          "Dune",\n'
    '    "authors":        "Frank Herbert",\n'
    '    "average_rating": 4.8,\n'
    '    "source":         "AI Agent",\n'
    '    "info_link":      "#",\n'
    '    "added_at":       "2025-05-28T09:13:00.000000"\n'
    '  }\n'
    ']'
)

pdf.h2("5.6  Why a Separate Curator?")
pdf.bullet([
    "Focused prompt: curator LLM instructed only on list operations — never confuses 'save' with 'search'",
    "Separation of concerns: search and list management have different failure modes and edge cases",
    "Testability: CuratorWorker can be unit-tested with a mock ReadingList, no retrieval stack needed",
    "Extensibility: add export-to-PDF, share-list, or rate-a-book as new tools here without touching search",
])

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 7 — MESSAGE FLOW
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("6.  Message Flow  —  End-to-End Walkthroughs")

pdf.h2("6.1  Simple Search Request")
pdf.body('User: "Find me a mystery book set in Cairo"')
pdf.code(
    "invoke({'messages': [HumanMessage('Find me a mystery book set in Cairo')]})\n"
    "\n"
    "[ORCHESTRATOR — agent node]\n"
    "  In:  [SystemMsg, HumanMsg]\n"
    "  Out: AIMessage(tool_calls=[search_worker('mystery book set in Cairo')])\n"
    "\n"
    "[ORCHESTRATOR — tools node]\n"
    "  Executes: search_worker('mystery book set in Cairo')\n"
    "    |\n"
    "    +-- [SEARCH WORKER — agent node]\n"
    "    |     In:  [SearchSystemMsg, HumanMsg]\n"
    "    |     Out: AIMessage(tool_calls=[search_local_library('mystery Cairo')])\n"
    "    |\n"
    "    +-- [SEARCH WORKER — tools node]\n"
    "    |     Runs: search_local_library('mystery Cairo')\n"
    "    |     Returns: ToolMessage('1. Death on the Nile...  2. ...')\n"
    "    |\n"
    "    +-- [SEARCH WORKER — agent node]\n"
    "          In:  [SystemMsg, Human, AI+tools, ToolMsg]\n"
    "          Out: AIMessage('Here are great mysteries set in Cairo...')  <- no tool_calls\n"
    "          -> __end__  (SearchWorker returns this string)\n"
    "\n"
    "  Returns: ToolMessage('Here are great mysteries set in Cairo...')\n"
    "\n"
    "[ORCHESTRATOR — agent node]\n"
    "  In:  [SysMsg, Human, AI+tools, ToolMsg(worker result)]\n"
    "  Out: AIMessage('Here are some brilliant mystery books set Cairo!')  <- no tool_calls\n"
    "  -> __end__\n"
    "\n"
    "User sees: 'Here are some brilliant mystery books set in Cairo!'"
)

pdf.ln(2)
pdf.h2("6.2  Compound Request  (Find + Save)")
pdf.body('User: "Find me a fantasy book and save the first one to my list"')
pdf.code(
    "[ORCHESTRATOR — agent node]\n"
    "  Out: AIMessage(tool_calls=[search_worker('fantasy book')])\n"
    "\n"
    "[ORCHESTRATOR — tools node]\n"
    "  Runs: search_worker -> '1. The Name of the Wind by Patrick Rothfuss (4.5)...'\n"
    "\n"
    "[ORCHESTRATOR — agent node]\n"
    "  Sees search result. User also asked to save first book.\n"
    "  Out: AIMessage(tool_calls=[curator_worker('Save The Name of the Wind by Patrick Rothfuss')])\n"
    "\n"
    "[ORCHESTRATOR — tools node]\n"
    "  Runs: curator_worker -> save_book('The Name of the Wind', 'Patrick Rothfuss')\n"
    "  Returns: 'The Name of the Wind added to your reading list.'\n"
    "\n"
    "[ORCHESTRATOR — agent node]\n"
    "  Out: AIMessage('Found great fantasy books! I also saved the first one...')  <- final\n"
    "  -> __end__"
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 8 — MEMORY & STATE
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("7.  Memory & State  —  MemorySaver, thread_id, Checkpoints")

pdf.h2("7.1  How MemorySaver Works")
pdf.body(
    "MemorySaver is a LangGraph checkpointer. After every node execution, it serialises "
    "the current graph state (the messages list) and stores it in RAM keyed by "
    "thread_id + checkpoint_id. On the next invoke() call with the same thread_id, "
    "LangGraph restores the last checkpoint and prepends it — giving the agent full "
    "conversation history without the caller needing to manage it."
)
pdf.bullet([
    "Thread ID: set per user session in app.py. Each Gradio session generates a unique UUID.",
    "Scope: only the Orchestrator has a checkpointer. Workers are stateless (no thread_id).",
    "Persistence: MemorySaver is in-process RAM only. App restart clears all sessions.",
    "Production upgrade: replace with SqliteSaver or PostgresSaver for cross-restart durability.",
])

pdf.ln(2)
pdf.h2("7.2  State Schema")
pdf.code(
    "# LangGraph MessagesState — used by all three graphs\n"
    "class MessagesState(TypedDict):\n"
    "    messages: Annotated[list[BaseMessage], add_messages]\n"
    "\n"
    "# add_messages reducer: new messages are appended, never overwritten.\n"
    "# The agent node reads messages[-N:] as LLM context (full history).\n"
    "# The tools node appends one ToolMessage per tool_call."
)

pdf.h2("7.3  Multi-Turn Conversation  (same thread_id)")
pdf.code(
    "Turn 1:  state = [System, Human('find mystery')]\n"
    "         agent -> search_worker -> ToolMsg -> agent\n"
    "         Final: AIMessage('Here are mysteries...') -- checkpoint saved\n"
    "\n"
    "Turn 2:  state = [...Turn1..., Human('save the first one')]\n"
    "         agent -> curator_worker('Save Death on the Nile') -> ToolMsg -> agent\n"
    "         Final: AIMessage('Saved!')  -- checkpoint saved\n"
    "         'the first one' refers to Turn 1 result -- possible via MemorySaver\n"
    "\n"
    "Turn 3:  state = [...Turn1...Turn2..., Human('show my reading list')]\n"
    "         agent -> curator_worker('view reading list') -> ToolMsg -> agent\n"
    "         Final: AIMessage('Your list has 1 book: Death on the Nile...')"
)

pdf.h2("7.4  Resetting State")
pdf.body(
    "agent_mgr.reset() sets self._agent = None and calls reset() on both workers. "
    "Called before re-configuring the LLM. All MemorySaver checkpoints are discarded. "
    "New Gradio sessions start with a fresh thread_id, naturally giving them no history."
)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE 9 — DESIGN DECISIONS
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("8.  Design Decisions")

pdf.h2("8.1  Why LangGraph over LangChain Chains?")
dw = [52, 65, 73]
pdf.table_header(["Dimension", "LangChain (chains)", "LangGraph (graphs)"], dw)
compare = [
    ("Control flow",    "Linear — A then B then C",            "Cyclic — can loop, branch, retry"),
    ("Agentic loops",   "Requires manual while-loops",          "Native: agent->tools->agent is the graph"),
    ("State",           "Passed explicitly between steps",      "Shared TypedDict, every node reads/writes"),
    ("Memory",          "Manual injection per call",            "Checkpointers built in (MemorySaver, SQLite)"),
    ("Debugging",       "Chain is opaque",                      "Every node transition traceable in LangSmith"),
    ("Multi-agent",     "Not native",                           "Supervisor: workers as tools of orchestrator"),
]
for i, row in enumerate(compare):
    pdf.table_row(list(row), dw, even=(i % 2 == 0))

pdf.ln(4)
pdf.h2("8.2  Why Orchestrator + Workers vs. One Big Agent?")
pdf.bullet([
    "Focus: one agent with 8 tools will sometimes pick the wrong one. Two agents with 4 each almost never do.",
    "Prompt quality: search prompt can say 'always call a tool' without conflicting with curation prompt.",
    "Failure isolation: if search breaks, curation still works. Single-agent failure cascades everywhere.",
    "Scalability: new worker (AnalyticsWorker) = new file + one @tool in agent.py. Zero changes elsewhere.",
    "Testability: each worker is independently callable via worker.run('query') with no other dependencies.",
])

pdf.ln(2)
pdf.h2("8.3  Why Stateless Workers?")
pdf.bullet([
    "Memory at multiple layers creates inconsistency: which layer's version of Turn 1 wins?",
    "Workers are tools: search_worker('mystery') is semantically a tool call, not a conversation.",
    "Simpler debugging: worker behaviour depends only on its input, not prior invocations.",
    "Session isolation: two concurrent users have isolated MemorySavers via thread_id. Workers have nothing to isolate.",
])

pdf.ln(2)
pdf.h2("8.4  Why  prompt=  instead of  state_modifier= / messages_modifier=?")
pdf.body(
    "LangGraph 1.x changed the create_react_agent API. In LangGraph 0.2.x the parameter "
    "was state_modifier=SystemMessage(...). In LangGraph 1.0 it was briefly messages_modifier=. "
    "From LangGraph 1.2 onwards the parameter is prompt= (accepts a plain string or SystemMessage). "
    "The prompt is injected at position 0 of every agent call. It is NOT stored in the checkpoint "
    "— keeping state lean and allowing prompt updates without invalidating existing sessions."
)

pdf.ln(2)
pdf.h2("8.5  Multi-Provider LLM Support")
pdf.body(
    "All three agents call llm_provider.get_langchain_llm() which returns a LangChain "
    "BaseChatModel (ChatAnthropic, ChatOpenAI, ChatGoogleGenerativeAI, or ChatOllama). "
    "Because create_react_agent accepts any BaseChatModel, the entire three-graph hierarchy "
    "works identically regardless of which provider is connected."
)
pdf.bullet([
    "Claude (claude-sonnet-4-6) — best reasoning and tool accuracy. Needs ANTHROPIC_API_KEY.",
    "OpenAI (gpt-4o) — strong tool-calling, widely known. Needs OPENAI_API_KEY.",
    "Gemini (gemini-1.5-pro) — Google infrastructure. Needs GEMINI_API_KEY.",
    "Ollama (llama3.2, qwen2.5, mistral) — fully local, free, no key. Needs Ollama server running.",
    "Note: only models supporting function/tool calling work with ReAct. gemma and phi3 excluded.",
])

# ─────────────────────────────────────────────────────────────────────────────
out = os.path.join(base_dir, "AGENT_STATE_GRAPH_DETAILED.pdf")
pdf.output(out)
print("Saved:", out)
