from __future__ import annotations

import re
from typing import Iterator, List, Optional, TextIO, Tuple, Union, TypeVar, Callable

from .exceptions import EndOfTokens, RenderedError, ParserError, WrongToken
from .lexer import Eof, Lexer, Newline, Text, Token
from .utils import str_to_int

NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
VAL_RE = re.compile(r"^(0b[01_]+|0o[0-7_]+|[0-9_]+|0x[a-fA-F0-9_]+)$")

T = TypeVar("T")


class Node:
    __slots__ = ("toks",)

    toks: Tuple[Text, ...]  # type: ignore


class File(Node):
    __slots__ = ("stmts",)

    stmts: Tuple[Stmt, ...]

    def __init__(self, stmts: Tuple[Stmt, ...]):
        self.stmts = stmts

        toks = []
        for stmt in stmts:
            toks.extend(stmt.toks)

        self.toks = tuple(toks)

    def __repr__(self) -> str:  # pragma: no cover
        return f"File({repr(self.stmts)})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (self.stmts == other.stmts)


class Stmt(Node):
    __slots__ = tuple()


class Label(Stmt):
    __slots__ = ("name",)

    name: str

    def __init__(self, name: str, toks: Tuple[Text, ...]):
        self.name = name
        self.toks = toks

    def __repr__(self) -> str:  # pragma: no cover
        return f"Label({repr(self.name)})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (self.name == other.name)


class Op(Stmt):
    __slots__ = ("mnemonic", "args")

    mnemonic: str
    args: Tuple[Union[str, int], ...]

    def __init__(
        self, mnemonic: str, args: Tuple[Union[str, int], ...], toks: Tuple[Text, ...]
    ):
        self.mnemonic = mnemonic
        self.args = args
        self.toks = toks

    def __repr__(self) -> str:  # pragma: no cover
        return f"Op({repr(self.mnemonic)}, {repr(self.args)})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (
            self.mnemonic == other.mnemonic and self.args == other.args
        )


class Val(Stmt):
    __slots__ = ("val",)

    val: int

    def __init__(self, val: int, toks: Tuple[Text, ...]):
        self.val = val
        self.toks = toks

    def __repr__(self) -> str:  # pragma: no cover
        return f"Val({self.val})"

    def __eq__(self, other) -> bool:
        return type(self) is type(other) and (self.val == other.val)


def marked(
    old_method: Callable[[Parser], Optional[T]]
) -> Callable[[Parser], Optional[T]]:
    def new_method(self) -> Optional[T]:
        self.mark()

        try:
            res = old_method(self)
        except ParserError:
            res = None

        if res is None:
            self.reset()

        return res

    return new_method


class Parser:
    __slots__ = ("lexer", "tokens", "buf", "marks")

    lexer: Lexer
    tokens: Iterator[Token]
    buf: List[Token]

    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.tokens = iter(lexer)
        self.buf = []
        self.marks = []

    @classmethod
    def from_str(cls, text: str) -> Parser:
        lexer = Lexer.from_str(text)
        return cls(lexer)

    @classmethod
    def from_buf(cls, buf: TextIO) -> Parser:
        lexer = Lexer(buf)
        return cls(lexer)

    def mark(self) -> None:
        """
        Creates a new reset buffer.
        """
        self.marks.append([])

    def put(self, tok: Token) -> None:
        self.buf.append(tok)

    def get(self) -> Token:
        if len(self.buf) > 0:
            tok = self.buf.pop()
        else:
            try:
                tok = next(self.tokens)
            except StopIteration:
                raise EndOfTokens("end of tokens")

        if len(self.marks) > 0:
            self.marks[-1].append(tok)

        return tok

    def expect_text(self, tok_text: Optional[str] = None, fatal: bool = False) -> Text:
        tok = self.get()

        if not isinstance(tok, Text):
            if fatal:
                raise RenderedError("expected text", tok)
            else:
                raise WrongToken("expected text")
        if tok_text is not None and tok.text != tok_text:
            if fatal:
                raise RenderedError(f"expected '{tok_text}'", tok)
            else:
                raise WrongToken(f"expected '{tok_text}'")

        return tok

    def expect_newline(self, fatal: bool = False) -> Newline:
        tok = self.get()

        if not isinstance(tok, Newline):
            if fatal:
                raise RenderedError(f"expected end of line", tok)
            else:
                raise WrongToken("expected end of line")

        return tok

    def reset(self) -> None:
        if len(self.marks) == 0:
            raise ParserError("cannot reset if no marks")

        mark_toks = self.marks.pop()
        for tok in reversed(mark_toks):
            self.put(tok)

    def peek(self, n: int) -> List[Token]:
        toks = []
        try:
            for _ in range(n):
                toks.append(self.get())
        finally:
            for tok in reversed(toks):
                self.put(tok)

        return toks

    def drop(self, n: int) -> None:
        for _ in range(n):
            self.get()

    def parse_file(self) -> File:
        stmts = []
        while stmt := self.parse_stmt():
            stmts.append(stmt)

        self.parse_eof()

        return File(tuple(stmts))

    def parse_stmt(self) -> Optional[Stmt]:
        if label := self.parse_label():
            try:
                tok = self.peek(1)[0]
            except EndOfTokens:  # pragma: no cover
                return label

            # consume a newline if one exists
            if isinstance(tok, Newline):
                self.drop(1)

            return label
        elif nullary_or_val := self.parse_nullary_or_val():
            return nullary_or_val
        else:
            return self.parse_unary()

    @marked
    def parse_label(self) -> Optional[Label]:
        name = self.expect_text()
        colon = self.expect_text(":")

        return Label(name.text, (name, colon))

    @marked
    def parse_nullary_or_val(self) -> Union[Op, Val, None]:
        name_or_val = self.expect_text()
        _ = self.expect_newline()

        if NAME_RE.match(name_or_val.text):
            return Op(name_or_val.text, (), (name_or_val,))
        elif VAL_RE.match(name_or_val.text):
            return Val(str_to_int(name_or_val.text), (name_or_val,))
        else:
            raise RenderedError(
                f"{repr(name_or_val.text)} is not a valid mnemonic or integer",
                name_or_val,
            )

    @marked
    def parse_unary(self) -> Optional[Op]:
        mnemonic = self.expect_text()
        name_or_val = self.expect_text()
        _ = self.expect_newline(fatal=True)

        if not NAME_RE.match(mnemonic.text):
            raise RenderedError(
                f"{repr(mnemonic.text)} is not a valid mnemonic", mnemonic
            )

        if VAL_RE.match(name_or_val.text):
            arg = str_to_int(name_or_val.text)
        elif NAME_RE.match(name_or_val.text):
            arg = name_or_val.text
        else:
            raise RenderedError(
                f"{repr(name_or_val.text)} is not a valid label or integer", name_or_val
            )

        return Op(mnemonic.text, (arg,), (mnemonic, name_or_val))

    def parse_eof(self) -> None:
        tok = self.get()
        if not isinstance(tok, Eof):  # pragma: no cover
            raise RenderedError("expected end of file", tok)
