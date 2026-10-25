"""
Tiny Compiler - Phase 1: Lexical Analyzer (Scanner)
Fundamentals of Programming Languages (CS314) - Future University in Egypt

Usage:
    python lexer.py "y=x*2.0+z*3.0*r"      # source passed as an argument
    python lexer.py -f program.txt         # source read from a file
    python lexer.py                        # prompts for the source code
    python lexer.py --show-comments ...    # also list the comments found

Token classes (from the project sheet):
    Reserved words : if then else end repeat until read write
    Special symbols: + - * /  =  <  (  )  ;  :=  { }
    Numbers        : unsigned integers (INT_NUM)  -> also unsigned floats (FLOAT_NUM),
                     because the source must contain both int and float
    Identifiers    : letter followed by letters, digits or _
    Comments       : %% ... (to end of line)   and   { ... }
"""

import sys
from dataclasses import dataclass

# --------------------------------------------------------------------------- #
# Token definitions
# --------------------------------------------------------------------------- #
RESERVED_WORDS = {"if", "then", "else", "end", "repeat", "until", "read", "write"}

SINGLE_CHAR_TOKENS = {
    "+": "PLUS",
    "-": "MINUS",
    "*": "MULT",
    "/": "DIV",
    "=": "EQUAL",
    "<": "LESSTHAN",
    "(": "LPAREN",
    ")": "RPAREN",
    ";": "SEMICOLON",
}


# --------------------------------------------------------------------------- #
# Finite automaton (the DFA this scanner implements)
#   FA_STATES      : name -> (description, accepted token class or None)
#   FA_TRANSITIONS : (from, label, to)
# Characters with no transition from a state are lexical errors.
# A word accepted in q1 is looked up in RESERVED_WORDS to decide
# between a reserved word and an identifier.
# --------------------------------------------------------------------------- #
FA_START = "q0"

FA_STATES = {
    "q0": ("start", None),
    "q1": ("identifier / reserved word", "IDENTIFIER"),
    "q2": ("integer", "INT_NUM"),
    "q3": ("digit '.' (digit needed)", None),
    "q4": ("float", "FLOAT_NUM"),
    "q5": ("':' seen", None),
    "q6": ("assignment", "ASSIGN"),
    "q7": ("single-char symbol", "+ - * / = < ( ) ;"),
    "q8": ("'%' seen", None),
    "q9": ("line comment", "COMMENT"),
    "q10": ("inside { } comment", None),
    "q11": ("block comment closed", "COMMENT"),
}

FA_TRANSITIONS = [
    ("q0", "letter", "q1"),
    ("q1", "letter | digit | _", "q1"),
    ("q0", "digit", "q2"),
    ("q2", "digit", "q2"),
    ("q2", ".", "q3"),
    ("q3", "digit", "q4"),
    ("q4", "digit", "q4"),
    ("q0", ":", "q5"),
    ("q5", "=", "q6"),
    ("q0", "+ - * / = < ( ) ;", "q7"),
    ("q0", "%", "q8"),
    ("q8", "%", "q9"),
    ("q9", "any except newline", "q9"),
    ("q0", "{", "q10"),
    ("q10", "any except }", "q10"),
    ("q10", "}", "q11"),
]


@dataclass
class Token:
    type: str
    lexeme: str
    line: int
    col: int


@dataclass
class LexError:
    message: str
    line: int
    col: int
    length: int = 1  # how many characters of source the error covers (used by the GUI)


# --------------------------------------------------------------------------- #
# Scanner
# --------------------------------------------------------------------------- #
class Lexer:
    def __init__(self, source: str):
        self.src = source
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []
        self.comments: list[Token] = []
        self.errors: list[LexError] = []

    # -- helpers ----------------------------------------------------------- #
    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.src[i] if i < len(self.src) else ""

    def _advance(self) -> str:
        ch = self.src[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _emit(self, type_: str, lexeme: str, line: int, col: int):
        self.tokens.append(Token(type_, lexeme, line, col))

    def _error(self, msg: str, line: int, col: int, length: int = 1):
        self.errors.append(LexError(msg, line, col, length))

    @staticmethod
    def _is_letter(ch: str) -> bool:
        return ch.isascii() and ch.isalpha()

    @staticmethod
    def _is_digit(ch: str) -> bool:
        return ch.isascii() and ch.isdigit()

    # -- main loop --------------------------------------------------------- #
    def tokenize(self):
        while self.pos < len(self.src):
            ch = self._peek()
            line, col = self.line, self.col

            # whitespace
            if ch in " \t\r\n":
                self._advance()

            # line comment:  %% ....
            elif ch == "%":
                if self._peek(1) == "%":
                    start = self.pos
                    while self.pos < len(self.src) and self._peek() != "\n":
                        self._advance()
                    self.comments.append(Token("COMMENT", self.src[start:self.pos], line, col))
                else:
                    self._advance()
                    self._error("Illegal character '%' (a comment must start with '%%')", line, col)

            # block comment:  { .... }
            elif ch == "{":
                start = self.pos
                self._advance()
                while self.pos < len(self.src) and self._peek() != "}":
                    self._advance()
                if self.pos >= len(self.src):
                    self._error("Unterminated comment: missing '}'", line, col, self.pos - start)
                else:
                    self._advance()  # consume '}'
                    self.comments.append(Token("COMMENT", self.src[start:self.pos], line, col))

            elif ch == "}":
                self._advance()
                self._error("Unexpected '}' with no matching '{'", line, col)

            # identifier / reserved word:  letter (letter | digit | _)*
            elif self._is_letter(ch):
                start = self.pos
                while self._is_letter(self._peek()) or self._is_digit(self._peek()) or self._peek() == "_":
                    self._advance()
                lexeme = self.src[start:self.pos]
                if lexeme in RESERVED_WORDS:
                    self._emit(lexeme.upper(), lexeme, line, col)
                else:
                    self._emit("IDENTIFIER", lexeme, line, col)

            # number:  digit+ [ . digit+ ]
            elif self._is_digit(ch):
                self._scan_number(line, col)

            # assignment  :=
            elif ch == ":":
                self._advance()
                if self._peek() == "=":
                    self._advance()
                    self._emit("ASSIGN", ":=", line, col)
                else:
                    self._error("Illegal character ':' (did you mean ':=' ?)", line, col)

            # single-character symbols
            elif ch in SINGLE_CHAR_TOKENS:
                self._advance()
                self._emit(SINGLE_CHAR_TOKENS[ch], ch, line, col)

            # anything else
            else:
                self._advance()
                self._error(f"Illegal character {ch!r}", line, col)

        return self.tokens

    def _scan_number(self, line: int, col: int):
        start = self.pos
        while self._is_digit(self._peek()):
            self._advance()

        is_float = False
        if self._peek() == ".":
            if self._is_digit(self._peek(1)):
                is_float = True
                self._advance()  # '.'
                while self._is_digit(self._peek()):
                    self._advance()
            else:
                # "2." or "2.x" is not a valid number
                self._advance()
                self._error(f"Malformed number '{self.src[start:self.pos]}' (digit expected after '.')", line, col, self.pos - start)
                return

        # a number glued to a letter / underscore, e.g. 3abc or 2.0x
        if self._is_letter(self._peek()) or self._peek() == "_":
            while self._is_letter(self._peek()) or self._is_digit(self._peek()) or self._peek() == "_":
                self._advance()
            self._error(f"Malformed token '{self.src[start:self.pos]}' (identifiers cannot start with a digit)", line, col, self.pos - start)
            return

        self._emit("FLOAT_NUM" if is_float else "INT_NUM", self.src[start:self.pos], line, col)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def identifier_ids(tokens: list[Token]) -> dict[str, str]:
    """Name each distinct identifier id1, id2, id3 ... in order of first appearance."""
    ids: dict[str, str] = {}
    for t in tokens:
        if t.type == "IDENTIFIER" and t.lexeme not in ids:
            ids[t.lexeme] = f"id{len(ids) + 1}"
    return ids


def display_type(t: Token, ids: dict[str, str]) -> str:
    """Token type as shown to the user: identifiers appear as id1, id2, ..."""
    return ids[t.lexeme] if t.type == "IDENTIFIER" else t.type


def print_tokens(tokens: list[Token]):
    ids = identifier_ids(tokens)
    print("=" * 56)
    print(" PHASE 1: LEXICAL ANALYZER - TOKENS")
    print("=" * 56)
    print(f"{'#':<4}{'LEXEME':<14}{'TOKEN TYPE':<16}{'LINE:COL'}")
    print("-" * 56)
    for i, t in enumerate(tokens, 1):
        print(f"{i:<4}{t.lexeme:<14}{display_type(t, ids):<16}{t.line}:{t.col}")
    print("-" * 56)
    print(f"Total tokens: {len(tokens)}")


def print_stream(tokens: list[Token]):
    ids = identifier_ids(tokens)

    print("\nToken stream:")
    print("  " + "".join(
        ids[t.lexeme] if t.type == "IDENTIFIER" else t.lexeme
        for t in tokens
    ))



def print_symbol_table(tokens: list[Token]):
    ids = identifier_ids(tokens)
    print("\nSymbol table (identifiers):")
    if not ids:
        print("  (none)")
    for name, id_ in ids.items():
        print(f"  {id_:<6}{name}")


def print_fa():
    print("\nFinite automaton (scanner DFA), start state: " + FA_START)
    print(f"  {'STATE':<7}{'ACCEPTS':<22}MEANING")
    for state, (meaning, accepts) in FA_STATES.items():
        print(f"  {state:<7}{accepts or '-':<22}{meaning}")
    print(f"\n  {'FROM':<7}{'ON':<24}TO")
    for src, label, dst in FA_TRANSITIONS:
        print(f"  {src:<7}{label:<24}{dst}")
    print("  (an accepted word in q1 that is in the reserved-word list becomes that keyword)")


def main(argv: list[str]) -> int:
    show_comments = "--show-comments" in argv
    argv = [a for a in argv if a != "--show-comments"]

    if len(argv) >= 2 and argv[0] == "-f":
        with open(argv[1], encoding="utf-8") as f:
            source = f.read()
    elif argv:
        source = " ".join(argv)
    else:
        source = input("Enter source code: ")

    print(f"Source code: {source!r}\n")

    lexer = Lexer(source)
    tokens = lexer.tokenize()

    print_tokens(tokens)
    print_stream(tokens)
    print_symbol_table(tokens)
    print_fa()

    if show_comments:
        print("\nComments (ignored by the scanner):")
        for c in lexer.comments or []:
            print(f"  {c.line}:{c.col}  {c.lexeme}")
        if not lexer.comments:
            print("  (none)")

    if lexer.errors:
        print(f"\n{len(lexer.errors)} lexical error(s):")
        for e in lexer.errors:
            print(f"  Line {e.line}, col {e.col}: {e.message}")
        return 1

    print("\nLexical analysis completed with no errors.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))