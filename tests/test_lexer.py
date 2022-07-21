from io import StringIO

from das.lexer import Lexer, Token, tokenize


def test_tokenize() -> None:
    assert list(tokenize("")) == []
    assert list(tokenize("a")) == ["a"]
    assert list(tokenize("\n")) == ["\n"]
    assert list(tokenize("a\n")) == ["a", "\n"]
    assert list(tokenize("\na")) == ["\n", "a"]
    assert list(tokenize("foo:\nbar")) == ["foo", ":", "\n", "bar"]
    assert list(tokenize("foo:bar   \n\rbaz\n\n")) == [
        "foo",
        ":",
        "bar",
        "   \n\r",
        "baz",
        "\n\n",
    ]


def test_token_is_newline() -> None:
    tok = Token("\n", 0, "", 0, 0, 0)
    assert tok.is_newline

    tok = Token("  \n", 0, "", 0, 0, 0)
    assert not tok.is_newline


def test_token_is_eof() -> None:
    tok = Token("", 0, "", 0, 0, 0)
    assert tok.is_eof

    tok = Token("  \n", 0, "", 0, 0, 0)
    assert not tok.is_eof


def test_lexer_simple() -> None:
    buf = StringIO(
        """
; test comment
    lda 1
42  ; test comment
"""
    )
    assert list(Lexer(buf)) == [
        Token("lda", 20, "    lda 1\n", 16, 3, 4),
        Token("1", 24, "    lda 1\n", 16, 3, 8),
        Token("\n", 25, "    lda 1\n", 16, 3, 9),
        Token("42", 26, "42  ; test comment\n", 26, 4, 0),
        Token("\n", 44, "42  ; test comment\n", 26, 4, 18),
        Token("", 45, "", 45, 5, 0),
    ]


def test_lexer_complex() -> None:
    buf = StringIO(
        """
; Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
; before halting

lda init

count_up:
  out
  add incr
  jc count_down  ; jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         ; jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )
    assert list(Lexer(buf)) == [
        Token("lda", 92, "lda init\n", 92, 5, 0),
        Token("init", 96, "lda init\n", 92, 5, 4),
        Token("\n", 100, "lda init\n", 92, 5, 8),
        Token("count_up", 102, "count_up:\n", 102, 7, 0),
        Token(":", 110, "count_up:\n", 102, 7, 8),
        Token("\n", 111, "count_up:\n", 102, 7, 9),
        Token("out", 114, "  out\n", 112, 8, 2),
        Token("\n", 117, "  out\n", 112, 8, 5),
        Token("add", 120, "  add incr\n", 118, 9, 2),
        Token("incr", 124, "  add incr\n", 118, 9, 6),
        Token("\n", 128, "  add incr\n", 118, 9, 10),
        Token(
            "jc",
            131,
            '  jc count_down  ; jump to "count_down" if we overflowed\n',
            129,
            10,
            2,
        ),
        Token(
            "count_down",
            134,
            '  jc count_down  ; jump to "count_down" if we overflowed\n',
            129,
            10,
            5,
        ),
        Token(
            "\n",
            185,
            '  jc count_down  ; jump to "count_down" if we overflowed\n',
            129,
            10,
            56,
        ),
        Token("jmp", 188, "  jmp count_up\n", 186, 11, 2),
        Token("count_up", 192, "  jmp count_up\n", 186, 11, 6),
        Token("\n", 200, "  jmp count_up\n", 186, 11, 14),
        Token("count_down", 202, "count_down:\n", 202, 13, 0),
        Token(":", 212, "count_down:\n", 202, 13, 10),
        Token("\n", 213, "count_down:\n", 202, 13, 11),
        Token("out", 216, "  out\n", 214, 14, 2),
        Token("\n", 219, "  out\n", 214, 14, 5),
        Token("sub", 222, "  sub incr\n", 220, 15, 2),
        Token("incr", 226, "  sub incr\n", 220, 15, 6),
        Token("\n", 230, "  sub incr\n", 220, 15, 10),
        Token(
            "jz",
            233,
            '  jz end         ; jump to "end" if we hit zero\n',
            231,
            16,
            2,
        ),
        Token(
            "end",
            236,
            '  jz end         ; jump to "end" if we hit zero\n',
            231,
            16,
            5,
        ),
        Token(
            "\n",
            278,
            '  jz end         ; jump to "end" if we hit zero\n',
            231,
            16,
            47,
        ),
        Token("jmp", 281, "  jmp count_down\n", 279, 17, 2),
        Token("count_down", 285, "  jmp count_down\n", 279, 17, 6),
        Token("\n", 295, "  jmp count_down\n", 279, 17, 16),
        Token("end", 297, "end: hlt\n", 297, 19, 0),
        Token(":", 300, "end: hlt\n", 297, 19, 3),
        Token("hlt", 302, "end: hlt\n", 297, 19, 5),
        Token("\n", 305, "end: hlt\n", 297, 19, 8),
        Token("init", 307, "init: 42\n", 307, 21, 0),
        Token(":", 311, "init: 42\n", 307, 21, 4),
        Token("42", 313, "init: 42\n", 307, 21, 6),
        Token("\n", 315, "init: 42\n", 307, 21, 8),
        Token("incr", 316, "incr: 1\n", 316, 22, 0),
        Token(":", 320, "incr: 1\n", 316, 22, 4),
        Token("1", 322, "incr: 1\n", 316, 22, 6),
        Token("\n", 323, "incr: 1\n", 316, 22, 7),
        Token("", 324, "", 324, 23, 0),
    ]
