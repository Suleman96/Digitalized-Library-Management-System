"""Generate HOW_IT_WORKS.pdf — system explainer + scenario Q&A."""

from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fpdf import FPDF, XPos, YPos
from datetime import datetime

BLUE     = (43,  92, 230)
DARK     = (15,  23,  42)
MID      = (30,  58, 138)
LIGHT_BG = (238, 242, 255)
MUTED    = (100, 110, 130)
WHITE    = (255, 255, 255)
CODE_BG  = (245, 245, 245)
Q_BG     = (219, 234, 254)   # light blue for question
A_BG     = (240, 253, 244)   # light green for answer
AMBER    = (146,  64,  14)
GREEN    = (6,   95,  70)

PW = 190
LH = 5.8


def s(t: str) -> str:
    return str(t).encode("latin-1", errors="replace").decode("latin-1")


class Doc(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5,
                  s("Iqra Digital Library v2  |  System Explainer & Scenario Q/A"),
                  align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")

    # ── layout helpers ────────────────────────────────────────────────────
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
        self.line(10, self.get_y(), 110, self.get_y())
        self.ln(3)

    def body(self, text: str) -> None:
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 9)
        self.multi_cell(PW, LH, s(text))
        self.ln(1)

    def bullet(self, items: list[str], indent: int = 15) -> None:
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*DARK)
        for item in items:
            self.set_x(indent)
            self.cell(4, LH, s("-"))
            self.set_x(indent + 4)
            self.multi_cell(PW - indent - 4, LH, s(item))

    def code(self, text: str) -> None:
        self.set_fill_color(*CODE_BG)
        self.set_font("Courier", "", 7.5)
        self.set_text_color(50, 50, 50)
        self.multi_cell(PW, 4.5, s(text), fill=True)
        self.ln(2)

    def scenario_block(self, number: int, title: str) -> None:
        """Numbered scenario header bar."""
        self.ln(4)
        self.set_fill_color(*MID)
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 10)
        self.cell(PW, 9,
                  s(f"  Scenario {number}:  {title}"),
                  fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def question(self, text: str) -> None:
        """Blue question box."""
        self.set_fill_color(*Q_BG)
        self.set_text_color(*MID)
        self.set_font("Helvetica", "B", 9)
        y = self.get_y()
        self.multi_cell(PW, LH, s("Q:  " + text), fill=True)
        self.ln(1)

    def answer_label(self) -> None:
        self.set_text_color(*GREEN)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, LH, s("A:"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def answer_body(self, text: str) -> None:
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 8.5)
        self.multi_cell(PW, LH, s(text))
        self.ln(1)

    def rule(self) -> None:
        self.ln(2)
        self.set_draw_color(*LIGHT_BG)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)

    def kv(self, key: str, val: str) -> None:
        self.set_font("Helvetica", "B", 8.5)
        self.set_text_color(*BLUE)
        self.cell(38, LH, s(key + ":"))
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*DARK)
        self.multi_cell(PW - 38, LH, s(val))


# =============================================================================
pdf = Doc()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(10, 15, 10)

# ─────────────────────────────────────────────────────────────────────────────
# COVER
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.ln(20)
pdf.set_font("Helvetica", "B", 26)
pdf.set_text_color(*BLUE)
pdf.cell(PW, 14, s("How It Works"), align="C",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_font("Helvetica", "B", 15)
pdf.set_text_color(*MID)
pdf.cell(PW, 9, s("System Explainer  +  Scenario Q/A"), align="C",
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(3)
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*MUTED)
pdf.cell(PW, 6, s("Iqra Digital Library v2  |  LangGraph ReAct Orchestrator Architecture  |  " +
                   datetime.now().strftime("%B %Y")),
         align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.ln(8)
pdf.set_draw_color(*BLUE)
pdf.set_line_width(0.8)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(8)

# summary box
pdf.set_fill_color(*LIGHT_BG)
pdf.rect(10, pdf.get_y(), PW, 28, style="F")
pdf.ln(3)
pdf.set_x(12)
pdf.set_font("Helvetica", "B", 9)
pdf.set_text_color(*BLUE)
pdf.cell(PW, 5, s("What this document covers"),
         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
pdf.set_x(12)
pdf.set_font("Helvetica", "", 8.5)
pdf.set_text_color(*DARK)
pdf.multi_cell(PW - 4, LH,
    s("Part 1 — three plain-English paragraphs explaining the entire system from user input "
      "to final response. Part 2 — six scenario-based questions with detailed answers covering "
      "debugging, concurrency, memory, feature additions, and production failures."))
pdf.ln(10)

# contents
pdf.set_font("Helvetica", "B", 10)
pdf.set_text_color(*MID)
pdf.cell(PW, 7, s("Contents"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
toc = [
    ("Part 1", "How It Works — 3 Paragraphs"),
    ("Part 2", "Scenario 1 — Agent gives completely wrong answer"),
    ("",       "Scenario 2 — 'Save the book you just found' fails"),
    ("",       "Scenario 3 — Ollama shows connected but agent gives no response"),
    ("",       "Scenario 4 — Client wants memory to survive server restarts"),
    ("",       "Scenario 5 — Two users send messages at the same time"),
    ("",       "Scenario 6 — Add PDF export feature with minimal code change"),
]
pdf.set_font("Helvetica", "", 9)
pdf.set_text_color(*DARK)
for part, title in toc:
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B" if part else "", 9)
    pdf.cell(18, 6, s(part))
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(PW - 32, 6, s(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

# ─────────────────────────────────────────────────────────────────────────────
# PART 1 — HOW IT WORKS
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("Part 1  —  How It Works")

pdf.h2("Paragraph 1 — The Orchestrator is the Brain")
pdf.body(
    "Every time a user types a message in the AI Librarian tab, app.py calls "
    "agent_mgr.chat(message, thread_id). This sends the message into the Orchestrator's "
    "LangGraph graph as a HumanMessage. The Orchestrator's agent node passes the full "
    "conversation history to the LLM, which reads the system prompt and decides what to do. "
    "It has exactly two tools: search_worker and curator_worker. If the user asked about "
    "books, it calls search_worker. If the user asked about their reading list, it calls "
    "curator_worker. If the request involves both — find a book and save it — it calls "
    "both in sequence. Once the tools return, the LLM reads the results and writes a final "
    "AIMessage with no tool_calls. That is the signal to exit the graph and return the "
    "reply to the user. MemorySaver records every message under the session's thread_id, "
    "so on the next turn the LLM remembers everything said before."
)

pdf.rule()

pdf.h2("Paragraph 2 — Each Worker is a Specialist with its Own Loop")
pdf.body(
    "When the Orchestrator calls search_worker('mystery books set in Cairo'), it is not "
    "just calling a function — it is triggering a full independent ReAct graph inside "
    "SearchWorker. That graph's agent node looks at the query and picks from four tools: "
    "search_local_library (BM25 + FAISS + Knowledge Graph), search_google_books (live API), "
    "find_similar_books (semantic similarity), or search_by_rating (rating filter). It calls "
    "one, gets a ToolMessage back, and either calls another tool or writes its final answer. "
    "That final answer string is returned to the Orchestrator's tools node as a ToolMessage. "
    "The Curator Worker does the same thing independently for reading list operations — "
    "save_book, remove_book, view_reading_list, count_reading_list — reading and writing "
    "data/reading_list.json via the ReadingList class. Neither worker holds memory. "
    "They are stateless per call — every invocation starts from a clean slate."
)

pdf.rule()

pdf.h2("Paragraph 3 — The Message List is the Shared Truth")
pdf.body(
    "Everything — decisions, tool calls, tool results, final answers — lives as typed "
    "message objects in the MessagesState list. HumanMessage carries the user input. "
    "AIMessage with tool_calls carries the LLM's decision to act. ToolMessage carries "
    "what the tool returned. AIMessage without tool_calls is the final answer. The graph "
    "routing is purely mechanical: if the last message has tool_calls, go to the tools "
    "node; otherwise go to __end__. This cycle repeats until the LLM stops calling tools. "
    "The MemorySaver checkpointer snapshots this list after every node so the next user "
    "message appends to a full history, giving the agent natural multi-turn memory without "
    "any manual state management from the caller."
)

pdf.ln(3)

# quick reference table
pdf.h2("Quick Reference — Message Types")
pdf.set_fill_color(*BLUE)
pdf.set_text_color(*WHITE)
pdf.set_font("Helvetica", "B", 8)
mw = [48, 34, 108]
for col, w in zip(["Message Type", "Created by", "Contains / Purpose"], mw):
    pdf.cell(w, 7, s(col), border=1, fill=True)
pdf.ln()
rows = [
    ("HumanMessage",              "User",          "Raw user text. Added before __start__ on each chat() call."),
    ("AIMessage  (tool_calls)",   "agent LLM",     "Decision to call a tool. Contains tool name + arguments as JSON."),
    ("ToolMessage",               "tools node",    "Result returned by a tool function. One per tool_call."),
    ("AIMessage  (no tool_calls)","agent LLM",     "Final natural-language reply. Triggers exit to __end__."),
    ("SystemMessage",             "Graph init",    "System prompt at position 0 of every agent call. Not checkpointed."),
]
for i, (mt, creator, desc) in enumerate(rows):
    fill = i % 2 == 0
    pdf.set_fill_color(*(LIGHT_BG if fill else WHITE))
    pdf.set_text_color(*DARK)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(mw[0], 7, s(mt),      border=1, fill=True)
    pdf.cell(mw[1], 7, s(creator), border=1, fill=True)
    pdf.cell(mw[2], 7, s(desc),    border=1, fill=True)
    pdf.ln()

# ─────────────────────────────────────────────────────────────────────────────
# PART 2 — SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.h1("Part 2  —  Scenario-Based Questions & Answers")

# ── SCENARIO 1 ────────────────────────────────────────────────────────────────
pdf.scenario_block(1, "Agent gives completely wrong answer")
pdf.body(
    'User searched for "romance novels" and received programming books instead.'
)
pdf.question("How do you debug this?")
pdf.answer_label()
pdf.answer_body(
    "Pull the execution trace. The failure lives in exactly one of four places in the chain:"
)
pdf.bullet([
    "Orchestrator routed wrong — check whether it called search_worker('romance novels') "
    "or accidentally called curator_worker. If it called the wrong tool, the system prompt "
    "routing rules need to be more explicit.",

    "Search Worker picked the wrong tool — check if it called search_local_library('romance novels') "
    "or received a corrupted query. If the query was mangled, the Orchestrator's tool call schema "
    "sent bad input.",

    "Retrieval returned wrong results — the tool was called correctly but FAISS returned programming "
    "books for a romance query. The embedding space is poorly calibrated for this query type. "
    "Fix: add BM25 hybrid (catches the keyword 'romance') or add HyDE (generate a hypothetical "
    "romance novel description and embed that instead of the raw query).",

    "LLM ignored retrieved results — tools returned correct books but the LLM hallucinated from "
    "its training weights. Fix: strengthen the system prompt with 'Only use the results from tools. "
    "Do not add books from memory.'",
])
pdf.answer_body(
    "Add this exact query to the golden test set. Every production failure becomes a regression test."
)

# ── SCENARIO 2 ────────────────────────────────────────────────────────────────
pdf.scenario_block(2, "'Save the book you just found' fails")
pdf.body(
    'User says: "Save the first book you just found to my reading list." '
    'Agent replies: "I don\'t see any recent search results."'
)
pdf.question("What went wrong and how do you fix it?")
pdf.answer_label()
pdf.answer_body(
    "This is a memory scope bug. The user is referring to a result from a previous turn. "
    "The Orchestrator has MemorySaver so it should have the prior turn in state. Two likely causes:"
)
pdf.bullet([
    "Different thread_id: the session was refreshed or reconnected, generating a new UUID. "
    "The new session has no history. Fix: persist thread_id to browser session storage so "
    "reconnects resume the same thread.",

    "Worker was asked without a concrete title: the Orchestrator called "
    "curator_worker('save the first book from earlier') but the CuratorWorker is stateless — "
    "it has no memory of 'earlier'. Fix: the Orchestrator must extract the book title from "
    "its own message history BEFORE calling curator_worker, then call "
    "curator_worker('save Dune by Frank Herbert') with the concrete title.",
])
pdf.answer_body(
    "Correct Orchestrator behaviour: read the prior AIMessage in state, extract the first "
    "book title, then pass that specific title as the curator_worker argument."
)

# ── SCENARIO 3 ────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.scenario_block(3, "Ollama shows connected but AI Librarian gives no response")
pdf.question("Walk through exactly what you check, step by step.")
pdf.answer_label()
pdf.answer_body("Check four things in order:")
pdf.bullet([
    "Step 1 — agent_mgr.is_ready: if False, the agent was never built. This happens when "
    "LLM_PROVIDER / LLM_MODEL env vars trigger auto-connect at startup but agent_mgr.build() "
    "was not called after llm.configure(). Fix: ensure the auto-connect block calls "
    "agent_mgr.build() after a successful configure().",

    "Step 2 — Model supports tool calling: if the user selected gemma:2b or phi3, those "
    "models do not support function/tool calling. The ReAct loop requires the LLM to output "
    "structured tool_calls JSON. Without it the agent errors or loops silently. Fix: only "
    "expose models that support tool calling: llama3.2, qwen2.5, mistral, llama3.1, deepseek-r1:8b.",

    "Step 3 — Model is actually pulled: Ollama returns connected even if the specific model "
    "is not downloaded. The connection check must query /api/tags and verify the model name "
    "is in the pulled list. If not, show: 'Model not pulled yet. Run: ollama pull llama3.2'.",

    "Step 4 — Ollama timeout: if the model is loading into VRAM, the initial request can "
    "take longer than 10 seconds. Raise the connection timeout to 30 seconds and add a "
    "user-visible loading indicator.",
])

# ── SCENARIO 4 ────────────────────────────────────────────────────────────────
pdf.scenario_block(4, "Client wants memory to survive server restarts")
pdf.body(
    "A German enterprise client says: 'We want the AI to remember what employees "
    "searched last week, even if the server was restarted over the weekend.'"
)
pdf.question("How do you change the architecture to support this?")
pdf.answer_label()
pdf.answer_body(
    "MemorySaver is in-process RAM — it dies on restart. Replace it with SqliteSaver "
    "or PostgresSaver. No other code changes are needed."
)
pdf.code(
    "# SqliteSaver — file-based, survives restarts, zero infrastructure\n"
    "from langgraph.checkpoint.sqlite import SqliteSaver\n"
    "memory = SqliteSaver.from_conn_string('checkpoints.db')\n"
    "\n"
    "# PostgresSaver — production-grade, multi-instance safe\n"
    "from langgraph.checkpoint.postgres import PostgresSaver\n"
    "memory = PostgresSaver.from_conn_string(os.getenv('DATABASE_URL'))\n"
    "\n"
    "# Pass into the Orchestrator — everything else stays identical\n"
    "self._agent = create_react_agent(\n"
    "    lc_llm, tools, checkpointer=memory, prompt=_ORCHESTRATOR_SYSTEM_PROMPT\n"
    ")"
)
pdf.answer_body(
    "The thread_id key still works the same way. The chat() method and all tool logic "
    "are completely unchanged. For enterprise, also store the thread_id -> user_id mapping "
    "in a users table so employees see only their own history and cannot access another "
    "person's checkpointed conversations."
)

# ── SCENARIO 5 ────────────────────────────────────────────────────────────────
pdf.add_page()
pdf.scenario_block(5, "Two users send messages at exactly the same time")
pdf.question("Does the system break? How does concurrency work?")
pdf.answer_label()
pdf.answer_body(
    "It is safe because MemorySaver isolates by thread_id. Each Gradio session generates "
    "a unique UUID as its thread_id. When User A's request arrives simultaneously with "
    "User B's, they are two separate invoke() calls with different thread_ids — they access "
    "completely different checkpoints and never touch each other's state."
)
pdf.answer_body(
    "The Workers (SearchWorker, CuratorWorker) are stateless — each call is independent, "
    "so two simultaneous searches run in parallel without conflict."
)
pdf.answer_body(
    "The only shared mutable state is data/reading_list.json. If two users trigger "
    "save_book at the exact same millisecond, there is a race condition on the file write. "
    "Fix for production: replace the JSON file with SQLite (WAL mode) or PostgreSQL with "
    "row-level locking. For single-user Gradio deployments this is not an issue — Gradio's "
    "event queue serialises writes."
)
pdf.bullet([
    "Orchestrator state: isolated per thread_id — safe",
    "Worker state: none — safe",
    "reading_list.json: shared file — race condition risk in multi-user deployments",
    "FAISS index: read-only at query time — safe",
    "LLM API calls: independent per request — safe",
])

# ── SCENARIO 6 ────────────────────────────────────────────────────────────────
pdf.scenario_block(6, "Add PDF export with minimal code change")
pdf.body(
    'Product team request: "The agent should be able to export the reading list as a PDF '
    'when the user asks for it."'
)
pdf.question("What is the minimal change to the codebase?")
pdf.answer_label()
pdf.answer_body(
    "Add one tool to CuratorWorker only. Zero changes to the Orchestrator or SearchWorker. "
    "The exporter already exists at exporter.py — just expose it as a new tool."
)
pdf.code(
    "# In agents/curator_agent.py — inside _build_tools()\n"
    "\n"
    "@tool\n"
    "def export_reading_list_pdf(placeholder: str = '') -> str:\n"
    "    'Export the reading list to a PDF file and return the file path.'\n"
    "    from exporter import export_books_pdf\n"
    "    books = rl.get_all()\n"
    "    if not books:\n"
    "        return 'Reading list is empty — nothing to export.'\n"
    "    path = export_books_pdf(books, title='My Reading List')\n"
    "    return f'Reading list exported to: {path}'\n"
    "\n"
    "# Add to the return list:\n"
    "return [save_book, remove_book, view_reading_list,\n"
    "        count_reading_list, export_reading_list_pdf]"
)
pdf.answer_body(
    "Then call agent_mgr.build() to rebuild all three graphs with the new tool. "
    "The Orchestrator automatically routes 'export my reading list as a PDF' to "
    "CuratorWorker, which now has the export tool available. Total change: ~12 lines, "
    "one file. This is exactly why the worker pattern exists — extending one domain "
    "requires touching only that worker."
)
pdf.bullet([
    "Files changed:  agents/curator_agent.py only",
    "Lines added:    ~12",
    "Files NOT changed:  agent.py, agents/search_agent.py, app.py, exporter.py",
    "Rebuild required:   agent_mgr.build()  (called automatically on next AI connect)",
])

# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out = os.path.join(base_dir, "HOW_IT_WORKS.pdf")
pdf.output(out)
print("Saved:", out)
