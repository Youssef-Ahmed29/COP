"""
Tiny Compiler - Phase 1: Lexical Analyzer  (PyQt5 GUI)
Fundamentals of Programming Languages (CS314) - Future University in Egypt

Run:      python lexer_gui.py
Needs:    PyQt5   (pip install PyQt5)   and   lexer.py in the same folder

Left  : source code input, quick examples, token reference
Right : Tokens, Token Stream, Symbol Table, Comments, Errors and FA tabs
        - click a row to highlight that text in the source
        - lexical errors are underlined in red in the source
"""

from __future__ import annotations

import contextlib
import io
import math
import sys

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor, QFont, QKeySequence, QPainter, QPainterPath, QPalette, QPen,
    QPolygonF, QTextCharFormat, QTextCursor
)
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QShortcut, QSplitter, QStatusBar, QTabWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget
)

from Lexer import (
    FA_START, FA_STATES, FA_TRANSITIONS, SINGLE_CHAR_TOKENS, Lexer, display_type,
    identifier_ids, print_fa, print_stream, print_symbol_table, print_tokens
)

# ─────────────────────────────────────────────────────────────
# Style
# ─────────────────────────────────────────────────────────────

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #0f0f1a;
    color: #e0e0f0;
    font-family: 'Segoe UI', 'Ubuntu', sans-serif;
}
QTabWidget::pane {
    border: 1px solid #2a2a4a;
    background-color: #12121f;
    border-radius: 4px;
}
QTabBar::tab {
    background: #1a1a2e;
    color: #888899;
    padding: 8px 14px;
    border: 1px solid #2a2a4a;
    border-bottom: none;
    font-size: 12px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #12121f;
    color: #00ff88;
    border-top: 2px solid #00ff88;
}
QTabBar::tab:hover {
    color: #ccccee;
    background: #1e1e35;
}
QPushButton {
    background-color: #1e1e35;
    color: #00ff88;
    border: 1px solid #00ff88;
    border-radius: 5px;
    padding: 8px 18px;
    font-size: 12px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #00ff88;
    color: #0f0f1a;
}
QPushButton:pressed {
    background-color: #00cc66;
}
QPushButton#danger {
    color: #ff4444;
    border-color: #ff4444;
}
QPushButton#danger:hover {
    background-color: #ff4444;
    color: white;
}
QPushButton#secondary {
    color: #8888ff;
    border-color: #8888ff;
}
QPushButton#secondary:hover {
    background-color: #8888ff;
    color: white;
}
QTextEdit {
    background-color: #1a1a2e;
    color: #e0e0f0;
    border: 1px solid #2a2a4a;
    border-radius: 4px;
    padding: 6px;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    selection-background-color: #00ff88;
    selection-color: #0f0f1a;
}
QTextEdit:focus {
    border: 1px solid #00ff88;
}
QLabel {
    color: #c0c0d0;
}
QLabel#header {
    font-size: 14px;
    font-weight: 700;
    color: #00ff88;
    padding: 4px 0;
}
QLabel#section {
    font-size: 11px;
    color: #888899;
    font-weight: 600;
}
QCheckBox {
    color: #c0c0d0;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #2a2a4a;
    border-radius: 3px;
    background: #1a1a2e;
}
QCheckBox::indicator:checked {
    background: #00ff88;
    border: 1px solid #00ff88;
}
QTableWidget {
    background-color: #12121f;
    color: #e0e0f0;
    border: 1px solid #2a2a4a;
    gridline-color: #2a2a4a;
    selection-background-color: #1e3a1e;
    font-family: 'Courier New', monospace;
    font-size: 12px;
}
QTableWidget::item:selected {
    background-color: #1e3a1e;
}
QHeaderView::section {
    background-color: #1a1a2e;
    color: #00ff88;
    border: 1px solid #2a2a4a;
    padding: 5px;
    font-weight: 600;
    font-size: 11px;
}
QScrollBar:vertical {
    background: #12121f;
    width: 8px;
}
QScrollBar::handle:vertical {
    background: #2a2a4a;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #00ff88;
}
QScrollBar:horizontal {
    background: #12121f;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #2a2a4a;
    border-radius: 4px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0px;
    height: 0px;
}
QStatusBar {
    background: #0a0a15;
    color: #888899;
    border-top: 1px solid #2a2a4a;
    font-size: 11px;
}
QSplitter::handle {
    background: #2a2a4a;
}
"""

# colours used for the "Token type" column
COLOR_RESERVED = "#00ff88"
COLOR_IDENT = "#8888ff"
COLOR_NUMBER = "#ffcc66"
COLOR_OTHER = "#e0e0f0"
RESERVED_ORDER = ["if", "then", "else", "end", "repeat", "until", "read", "write"]
RESERVED_TYPES = {w.upper() for w in RESERVED_ORDER}


def type_color(token_type: str) -> str:
    if token_type in RESERVED_TYPES:
        return COLOR_RESERVED
    if token_type == "IDENTIFIER":
        return COLOR_IDENT
    if token_type in ("INT_NUM", "FLOAT_NUM"):
        return COLOR_NUMBER
    return COLOR_OTHER


EXAMPLES = [
    ("Project example", "y=x*2.0+z*3.0*r"),
    ("Keywords", "if x < 10 then\n  write x\nelse\n  read y\nend"),
    ("Assignment :=", "x := 5;\ny := x + 2.5;"),
    ("Comments", "x := 1;  %% line comment\n{ block\n  comment }\ny := 2;"),
    ("Repeat / until", "repeat\n  read n;\n  n := n - 1\nuntil n = 0"),
    ("Lexical errors", "a = 3abc + 2. @ b : c"),
]


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def make_table(headers, widths=()):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setDefaultSectionSize(26)
    for i, w in enumerate(widths):
        table.setColumnWidth(i, w)
    return table


def add_row(table, values, span=None, colors=None):
    r = table.rowCount()
    table.insertRow(r)
    for c, value in enumerate(values):
        item = QTableWidgetItem(str(value))
        if colors and c in colors:
            item.setForeground(QColor(colors[c]))
        if span is not None and c == 0:
            item.setData(Qt.UserRole, list(span))
        table.setItem(r, c, item)


def titled(title: str, widget: QWidget) -> QWidget:
    """Wrap a widget with a green header label, like the other panels."""
    box = QWidget()
    lay = QVBoxLayout(box)
    label = QLabel(title)
    label.setObjectName("header")
    lay.addWidget(label)
    lay.addWidget(widget)
    return box


# ─────────────────────────────────────────────────────────────
# Finite automaton diagram
# ─────────────────────────────────────────────────────────────

class FADiagram(QWidget):
    """Draws the scanner's DFA (Lexer.FA_STATES / FA_TRANSITIONS) with QPainter."""

    W, H, R = 960, 800, 27  # logical canvas size and state radius
    TOP = 40                # extra room above q1 for its self-loop label

    POS = {
        "q0": (95, 370),
        "q1": (380, 85),
        "q2": (380, 205),
        "q3": (620, 205),
        "q4": (860, 205),
        "q5": (380, 325),
        "q6": (620, 325),
        "q7": (380, 440),
        "q8": (380, 550),
        "q9": (620, 550),
        "q10": (380, 665),
        "q11": (620, 665),
    }
    # which side a self-loop is drawn on: +1 above the state, -1 below it
    LOOP_SIDE = {"q1": 1, "q2": 1, "q4": 1, "q9": 1, "q10": -1}
    # where the accepted token class is written next to an accepting state
    TOKEN_NOTE = {
        "q1": ("right", "IDENTIFIER → id1, id2, … / keyword"),
        "q2": ("below", "INT_NUM"),
        "q4": ("below", "FLOAT_NUM"),
        "q6": ("right", "ASSIGN"),
        "q7": ("right", "PLUS MINUS MULT DIV EQUAL …"),
        "q9": ("right", "COMMENT (skipped)"),
        "q11": ("right", "COMMENT (skipped)"),
    }

    BG = QColor("#12121f")
    EDGE = QColor("#8888ff")
    TEXT = QColor("#e0e0f0")
    ACCEPT = QColor("#00ff88")
    NOTE = QColor("#ffcc66")

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 520)

    # ── drawing helpers ──────────────────────────────────────
    def _label(self, p, x, y, text, color=None, size=17):
        font = QFont("Courier New")
        font.setPixelSize(size)
        font.setBold(True)
        p.setFont(font)
        rect = QRectF(p.fontMetrics().boundingRect(text))
        rect.moveCenter(QPointF(x, y))
        rect.adjust(-4, -1, 4, 1)
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(self.BG)
        p.drawRect(rect)
        p.restore()
        p.setPen(color or self.TEXT)
        p.drawText(rect, Qt.AlignCenter, text)

    def _arrow_head(self, p, tip, ux, uy):
        size = 11
        nx, ny = -uy, ux
        poly = QPolygonF([
            tip,
            QPointF(tip.x() - ux * size + nx * size * 0.45, tip.y() - uy * size + ny * size * 0.45),
            QPointF(tip.x() - ux * size - nx * size * 0.45, tip.y() - uy * size - ny * size * 0.45),
        ])
        p.setBrush(self.EDGE)
        p.drawPolygon(poly)

    def _edge(self, p, a, b, label):
        (x1, y1), (x2, y2) = self.POS[a], self.POS[b]
        d = math.hypot(x2 - x1, y2 - y1)
        ux, uy = (x2 - x1) / d, (y2 - y1) / d
        start = QPointF(x1 + ux * self.R, y1 + uy * self.R)
        end = QPointF(x2 - ux * self.R, y2 - uy * self.R)
        p.setPen(QPen(self.EDGE, 2))
        p.drawLine(start, end)
        self._arrow_head(p, end, ux, uy)
        t = 0.55 if a == "q0" else 0.5
        self._label(p, start.x() + (end.x() - start.x()) * t,
                    start.y() + (end.y() - start.y()) * t, label)

    def _loop(self, p, state, label):
        x, y = self.POS[state]
        s = self.LOOP_SIDE.get(state, 1)
        r = self.R
        start = QPointF(x - 13, y - s * r * 0.9)
        end = QPointF(x + 13, y - s * r * 0.9)
        c1 = QPointF(x - 38, y - s * (r + 46))
        c2 = QPointF(x + 38, y - s * (r + 46))
        path = QPainterPath(start)
        path.cubicTo(c1, c2, end)
        p.setPen(QPen(self.EDGE, 2))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)
        ux, uy = end.x() - c2.x(), end.y() - c2.y()
        n = math.hypot(ux, uy)
        self._arrow_head(p, end, ux / n, uy / n)
        self._label(p, x, y - s * (r + 44), label)

    def _state(self, p, name):
        x, y = self.POS[name]
        accepting = FA_STATES[name][1] is not None
        p.setPen(QPen(self.ACCEPT if accepting else self.EDGE, 2.5))
        p.setBrush(QColor("#1a1a2e"))
        p.drawEllipse(QPointF(x, y), self.R, self.R)
        if accepting:
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(x, y), self.R - 5, self.R - 5)
        font = QFont("Courier New")
        font.setPixelSize(17)
        font.setBold(True)
        p.setFont(font)
        p.setPen(self.TEXT)
        p.drawText(QRectF(x - self.R, y - self.R, 2 * self.R, 2 * self.R), Qt.AlignCenter, name)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.fillRect(self.rect(), self.BG)

        scale = min(self.width() / self.W, self.height() / self.H)
        p.translate((self.width() - self.W * scale) / 2, (self.height() - self.H * scale) / 2)
        p.scale(scale, scale)
        p.translate(0, self.TOP)

        # transitions
        for src, label, dst in FA_TRANSITIONS:
            if src == dst:
                self._loop(p, src, label)
            else:
                self._edge(p, src, dst, label)

        # start arrow into q0
        x, y = self.POS[FA_START]
        p.setPen(QPen(self.EDGE, 2))
        p.drawLine(QPointF(20, y), QPointF(x - self.R, y))
        self._arrow_head(p, QPointF(x - self.R, y), 1, 0)
        self._label(p, 48, y - 16, "start", self.NOTE, 14)

        # states and token notes
        for name in FA_STATES:
            self._state(p, name)
        for name, (where, text) in self.TOKEN_NOTE.items():
            x, y = self.POS[name]
            font = QFont("Courier New")
            font.setPixelSize(16)
            p.setFont(font)
            p.setPen(self.NOTE)
            if where == "right":
                p.drawText(QPointF(x + self.R + 12, y + 5), text)
            else:
                p.drawText(QRectF(x - 80, y + self.R + 4, 160, 20), Qt.AlignCenter, text)

        # legend
        font = QFont("Segoe UI")
        font.setPixelSize(15)
        p.setFont(font)
        p.setPen(QColor("#888899"))
        for i, line in enumerate((
            "double green circle = accepting state",
            "a character with no transition = lexical error",
            "a word accepted in q1 is checked against the reserved words",
        )):
            p.drawText(QPointF(560, 4 + i * 18), line)


# ─────────────────────────────────────────────────────────────
# Results Panel
# ─────────────────────────────────────────────────────────────

class ResultsPanel(QWidget):
    span_selected = pyqtSignal(int, int, int)  # line, col, length

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.tabs = QTabWidget()

        self.tok_table = make_table(["#", "Lexeme", "Token type", "Line:Col"], [60, 220, 220])
        self.stream_output = QTextEdit()
        self.stream_output.setReadOnly(True)
        self.stream_output.setFont(QFont("Courier New", 13))
        self.sym_table = make_table(["ID", "Identifier", "First seen (Line:Col)", "Occurrences"],
                                    [60, 260, 200])
        self.com_table = make_table(["Line:Col", "Comment  (newlines shown as \\n)"], [100])
        self.err_table = make_table(["Line:Col", "Message"], [100])

        # finite automaton: diagram on top, transition table below
        self.fa_diagram = FADiagram()
        fa_scroll = QScrollArea()
        fa_scroll.setWidgetResizable(True)
        fa_scroll.setWidget(self.fa_diagram)
        self.fa_table = make_table(["From", "On", "To", "To accepts"], [80, 240, 80])
        for src, label, dst in FA_TRANSITIONS:
            accepts = FA_STATES[dst][1]
            add_row(self.fa_table, (src, label, dst, accepts or "-"),
                    colors={3: COLOR_RESERVED if accepts else "#888899"})
        fa_split = QTabWidget()
        fa_split.addTab(fa_scroll, "Diagram")
        fa_split.addTab(self.fa_table, "Transition table")

        self.tabs.addTab(titled("Token List", self.tok_table), "⬡  Tokens")
        self.tabs.addTab(titled("Token Stream", self.stream_output), "≡  Stream")
        self.tabs.addTab(titled("Symbol Table", self.sym_table), "𝑆  Symbols")
        self.tabs.addTab(titled("Comments (ignored by the scanner)", self.com_table), "//  Comments")
        self.tabs.addTab(titled("Lexical Errors", self.err_table), "⚠  Errors")
        self.tabs.addTab(titled("Finite Automaton (FA) of the scanner", fa_split), "◎  FA")
        layout.addWidget(self.tabs)

        for table in (self.tok_table, self.sym_table, self.com_table, self.err_table):
            table.itemSelectionChanged.connect(lambda t=table: self._row_selected(t))

    def _row_selected(self, table):
        rows = table.selectionModel().selectedRows()
        if not rows:
            return
        item = table.item(rows[0].row(), 0)
        span = item.data(Qt.UserRole) if item else None
        if span:
            self.span_selected.emit(int(span[0]), int(span[1]), int(span[2]))

    def show_results(self, lexer: Lexer):
        tokens = lexer.tokens
        ids = identifier_ids(tokens)  # identifier name -> id1, id2, ...

        for table in (self.tok_table, self.sym_table, self.com_table, self.err_table):
            table.setRowCount(0)

        # tokens (identifiers are shown as id1, id2, ...)
        for i, t in enumerate(tokens, 1):
            add_row(self.tok_table, (i, t.lexeme, display_type(t, ids), f"{t.line}:{t.col}"),
                    span=(t.line, t.col, len(t.lexeme)), colors={2: type_color(t.type)})

        # token stream
        stream = " ".join(f"<{ids[t.lexeme]}>" if t.type == "IDENTIFIER"
                          else f"<{t.type}, {t.lexeme}>" if t.type in ("INT_NUM", "FLOAT_NUM")
                          else f"<{t.type}>" for t in tokens)
        self.stream_output.setPlainText(stream)

        # symbol table (first appearance order)
        symbols: dict[str, list] = {}
        for t in tokens:
            if t.type == "IDENTIFIER":
                entry = symbols.setdefault(t.lexeme, [t, 0])
                entry[1] += 1
        for name, (first, count) in symbols.items():
            add_row(self.sym_table, (ids[name], name, f"{first.line}:{first.col}", count),
                    span=(first.line, first.col, len(name)),
                    colors={0: COLOR_IDENT, 1: COLOR_IDENT})

        # comments
        for c in lexer.comments:
            add_row(self.com_table, (f"{c.line}:{c.col}", c.lexeme.replace("\n", "\\n")),
                    span=(c.line, c.col, len(c.lexeme)), colors={1: "#888899"})

        # errors
        for e in lexer.errors:
            add_row(self.err_table, (f"{e.line}:{e.col}", e.message),
                    span=(e.line, e.col, e.length), colors={1: "#ff6666"})

        self.tabs.setTabText(0, f"⬡  Tokens ({len(tokens)})")
        self.tabs.setTabText(2, f"𝑆  Symbols ({len(symbols)})")
        self.tabs.setTabText(3, f"//  Comments ({len(lexer.comments)})")
        self.tabs.setTabText(4, f"⚠  Errors ({len(lexer.errors)})")


# ─────────────────────────────────────────────────────────────
# Main Window
# ─────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lexical Analyzer")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)

        self.lexer: Lexer | None = None
        self.error_spans: list[tuple[int, int, int]] = []
        self.hl_span: tuple[int, int, int] | None = None
        self._line_starts = [0]

        self.live_timer = QTimer(self)
        self.live_timer.setSingleShot(True)
        self.live_timer.setInterval(300)
        self.live_timer.timeout.connect(lambda: self.analyze(auto_tab=False))

        self._setup_ui()
        self._setup_statusbar()
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=lambda: self.analyze())

        self.source_edit.setPlainText(EXAMPLES[0][1])
        self.analyze()

    # ── UI ───────────────────────────────────────────────────
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 8)
        root.setSpacing(8)

        # header
        header = QHBoxLayout()
        title = QLabel("Cookies 🍪")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        title.setStyleSheet("color: #00ff88;")
        subtitle = QLabel("Phase 1  ·  Lexical Analyzer")
        subtitle.setStyleSheet("color: #555577; font-size: 11px;")
        header.addWidget(title)
        header.addSpacing(16)
        header.addWidget(subtitle)
        header.addStretch()
        root.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("color: #2a2a4a;")
        root.addWidget(line)

        splitter = QSplitter(Qt.Horizontal)

        # ── left panel: input ──
        left = QWidget()
        left.setMaximumWidth(440)
        left.setMinimumWidth(340)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)

        input_label = QLabel("INPUT")
        input_label.setObjectName("section")
        left_layout.addWidget(input_label)

        self.input_tabs = QTabWidget()

        # source tab
        src_tab = QWidget()
        st = QVBoxLayout(src_tab)
        st.setSpacing(8)
        sl = QLabel("Source Code")
        sl.setObjectName("header")
        st.addWidget(sl)
        st.addWidget(QLabel("Enter the equation / program to scan:"))

        self.source_edit = QTextEdit()
        self.source_edit.setAcceptRichText(False)
        self.source_edit.setFont(QFont("Courier New", 14))
        self.source_edit.setPlaceholderText("e.g.  y=x*2.0+z*3.0*r")
        self.source_edit.setMinimumHeight(130)
        self.source_edit.textChanged.connect(self._on_text_changed)
        st.addWidget(self.source_edit, 1)

        ex_label = QLabel("Quick Examples:")
        ex_label.setObjectName("section")
        st.addWidget(ex_label)
        grid = QGridLayout()
        grid.setSpacing(4)
        for i, (name, code) in enumerate(EXAMPLES):
            btn = QPushButton(name)
            btn.setObjectName("secondary")
            btn.setFont(QFont("Segoe UI", 10))
            btn.clicked.connect(lambda checked, c=code: self._load_example(c))
            grid.addWidget(btn, i // 2, i % 2)
        st.addLayout(grid)

        live_row = QHBoxLayout()
        self.live_check = QCheckBox("Live analysis (re-scan as you type)")
        self.live_check.setChecked(True)
        live_row.addWidget(self.live_check)
        live_row.addStretch()
        st.addLayout(live_row)

        analyze_btn = QPushButton("Analyze  →")
        analyze_btn.setFont(QFont("Segoe UI", 13, QFont.Bold))
        analyze_btn.setMinimumHeight(40)
        analyze_btn.setToolTip("Ctrl+Enter")
        analyze_btn.clicked.connect(lambda: self.analyze())
        st.addWidget(analyze_btn)

        btn_row = QHBoxLayout()
        open_btn = QPushButton("Open file…")
        open_btn.setObjectName("secondary")
        open_btn.clicked.connect(self.open_file)
        save_btn = QPushButton("Save results…")
        save_btn.setObjectName("secondary")
        save_btn.clicked.connect(self.save_results)
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self.clear)
        btn_row.addWidget(open_btn)
        btn_row.addWidget(save_btn)
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        st.addLayout(btn_row)

        # reference tab
        ref_table = make_table(["Class", "Lexeme / pattern", "Token"], [110, 150])
        for w in RESERVED_ORDER:
            add_row(ref_table, ("Reserved word", w, w.upper()), colors={2: COLOR_RESERVED})
        for ch, name in SINGLE_CHAR_TOKENS.items():
            add_row(ref_table, ("Special symbol", ch, name))
        add_row(ref_table, ("Special symbol", ":=", "ASSIGN"))
        add_row(ref_table, ("Number", "digit+", "INT_NUM"), colors={2: COLOR_NUMBER})
        add_row(ref_table, ("Number", "digit+ . digit+", "FLOAT_NUM"), colors={2: COLOR_NUMBER})
        add_row(ref_table, ("Identifier", "letter (letter|digit|_)*", "id1, id2, id3, …"), colors={2: COLOR_IDENT})
        add_row(ref_table, ("Comment", "%% … end of line", "(skipped)"), colors={2: "#888899"})
        add_row(ref_table, ("Comment", "{ … }", "(skipped)"), colors={2: "#888899"})
        ref_table.setSelectionMode(QAbstractItemView.NoSelection)
        ref_tab = QWidget()
        rt = QVBoxLayout(ref_tab)
        rt.addWidget(titled("Token Reference", ref_table))

        self.input_tabs.addTab(src_tab, "Source")
        self.input_tabs.addTab(ref_tab, "Token Table")
        left_layout.addWidget(self.input_tabs)

        # ── right panel: results ──
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(4, 0, 0, 0)

        out_label = QLabel("OUTPUT")
        out_label.setObjectName("section")
        right_layout.addWidget(out_label)

        self.results = ResultsPanel()
        self.results.span_selected.connect(self._highlight)
        right_layout.addWidget(self.results)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([400, 840])
        root.addWidget(splitter, 1)

    def _setup_statusbar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready — enter source code to begin.")

    # ── source handling ──────────────────────────────────────
    def _load_example(self, code: str):
        self.source_edit.setPlainText(code)
        self.analyze()
        self.source_edit.setFocus()

    def clear(self):
        self.source_edit.clear()
        self.analyze()
        self.source_edit.setFocus()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open source file", "", "Text files (*.txt *.src *.tiny);;All files (*)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                self.source_edit.setPlainText(f.read())
        except OSError as exc:
            QMessageBox.critical(self, "Open file", f"Could not read the file:\n{exc}")
            return
        self.analyze()

    def _on_text_changed(self):
        if self.live_check.isChecked():
            self.live_timer.start()
        else:
            # the old error marks no longer line up with the text
            self.live_timer.stop()
            self.error_spans = []
            self.hl_span = None
            self.source_edit.setExtraSelections([])

    # ── analysis ─────────────────────────────────────────────
    def analyze(self, auto_tab: bool = True):
        self.live_timer.stop()

        src = self.source_edit.toPlainText()
        lexer = Lexer(src)
        tokens = lexer.tokenize()
        self.lexer = lexer

        self._line_starts = [0] + [i + 1 for i, ch in enumerate(src) if ch == "\n"]
        self.error_spans = [(e.line, e.col, e.length) for e in lexer.errors]
        self.hl_span = None
        self.results.show_results(lexer)
        self._refresh_selections()

        n_tok, n_err = len(tokens), len(lexer.errors)
        n_sym = len({t.lexeme for t in tokens if t.type == "IDENTIFIER"})
        if n_err:
            self.status.showMessage(
                f"✗  {n_err} lexical error(s)  |  {n_tok} tokens — see the Errors tab")
            if auto_tab:
                self.results.tabs.setCurrentIndex(4)
        elif n_tok == 0:
            self.status.showMessage("Ready — enter source code to begin.")
        else:
            self.status.showMessage(
                f"✓  Done — {n_tok} tokens, {n_sym} distinct identifiers  |  no lexical errors")
            if auto_tab and self.results.tabs.currentIndex() == 4:
                self.results.tabs.setCurrentIndex(0)

    # ── highlighting in the source ───────────────────────────
    def _offset(self, line: int, col: int) -> int:
        line = max(1, min(line, len(self._line_starts)))
        return self._line_starts[line - 1] + col - 1

    def _selection(self, span, fmt):
        line, col, length = span
        doc = self.source_edit.document()
        end_limit = max(doc.characterCount() - 1, 0)
        start = min(self._offset(line, col), end_limit)
        end = min(start + max(length, 1), end_limit)
        cursor = QTextCursor(doc)
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.KeepAnchor)
        sel = QTextEdit.ExtraSelection()
        sel.cursor = cursor
        sel.format = fmt
        return sel

    def _refresh_selections(self):
        err_fmt = QTextCharFormat()
        err_fmt.setBackground(QColor("#3a1a22"))
        err_fmt.setForeground(QColor("#ff8888"))
        err_fmt.setUnderlineStyle(QTextCharFormat.WaveUnderline)
        err_fmt.setUnderlineColor(QColor("#ff4444"))

        hl_fmt = QTextCharFormat()
        hl_fmt.setBackground(QColor("#00ff88"))
        hl_fmt.setForeground(QColor("#0f0f1a"))

        selections = [self._selection(s, err_fmt) for s in self.error_spans]
        if self.hl_span:
            selections.append(self._selection(self.hl_span, hl_fmt))
        self.source_edit.setExtraSelections(selections)

    def _highlight(self, line: int, col: int, length: int):
        self.hl_span = (line, col, length)
        self._refresh_selections()
        # bring the text into view without taking focus away
        cursor = self.source_edit.textCursor()
        cursor.setPosition(min(self._offset(line, col), max(self.source_edit.document().characterCount() - 1, 0)))
        self.source_edit.setTextCursor(cursor)
        self.source_edit.ensureCursorVisible()

    # ── save ─────────────────────────────────────────────────
    def report_text(self) -> str:
        lexer = self.lexer
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print(f"Source code: {self.source_edit.toPlainText()!r}\n")
            print_tokens(lexer.tokens)
            print_stream(lexer.tokens)
            print_symbol_table(lexer.tokens)
            print_fa()
            if lexer.errors:
                print(f"\n{len(lexer.errors)} lexical error(s):")
                for e in lexer.errors:
                    print(f"  Line {e.line}, col {e.col}: {e.message}")
            else:
                print("\nLexical analysis completed with no errors.")
        return buf.getvalue()

    def save_results(self):
        self.analyze()
        path, _ = QFileDialog.getSaveFileName(
            self, "Save results", "lexer_output.txt", "Text files (*.txt)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.report_text())
        except OSError as exc:
            QMessageBox.critical(self, "Save results", f"Could not save the file:\n{exc}")
            return
        self.status.showMessage(f"✓  Results saved to {path}")


# ─────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Lexical Analyzer")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0f0f1a"))
    palette.setColor(QPalette.WindowText, QColor("#e0e0f0"))
    palette.setColor(QPalette.Base, QColor("#1a1a2e"))
    palette.setColor(QPalette.Text, QColor("#e0e0f0"))
    palette.setColor(QPalette.Button, QColor("#1e1e35"))
    palette.setColor(QPalette.ButtonText, QColor("#00ff88"))
    palette.setColor(QPalette.Highlight, QColor("#00ff88"))
    palette.setColor(QPalette.HighlightedText, QColor("#0f0f1a"))
    app.setPalette(palette)
    app.setStyleSheet(DARK_STYLE)

    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()