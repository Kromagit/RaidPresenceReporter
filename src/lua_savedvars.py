from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LuaParseError(ValueError):
    pass


@dataclass
class Token:
    kind: str
    value: Any
    pos: int


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.i = 0
        self.n = len(text)

    def _skip(self) -> None:
        while self.i < self.n:
            if self.text[self.i].isspace() or self.text[self.i] in ",;":
                self.i += 1
                continue
            if self.text.startswith("--", self.i):
                end = self.text.find("\n", self.i)
                self.i = self.n if end < 0 else end + 1
                continue
            break

    def next(self) -> Token:
        self._skip()
        if self.i >= self.n:
            return Token("EOF", None, self.i)

        start = self.i
        ch = self.text[self.i]

        if ch in "{}[]=.":
            self.i += 1
            return Token(ch, ch, start)

        if ch in "'\"":
            quote = ch
            self.i += 1
            out = []
            while self.i < self.n:
                ch = self.text[self.i]
                self.i += 1
                if ch == quote:
                    return Token("STRING", "".join(out), start)
                if ch == "\\" and self.i < self.n:
                    escaped = self.text[self.i]
                    self.i += 1
                    mapping = {"n": "\n", "r": "\r", "t": "\t"}
                    out.append(mapping.get(escaped, escaped))
                else:
                    out.append(ch)
            raise LuaParseError(f"Chaîne non terminée à {start}")

        if ch.isdigit() or (ch == "-" and self.i + 1 < self.n and self.text[self.i + 1].isdigit()):
            self.i += 1
            while self.i < self.n and (self.text[self.i].isdigit() or self.text[self.i] in ".eE+-"):
                self.i += 1
            raw = self.text[start:self.i]
            try:
                value = float(raw) if any(c in raw for c in ".eE") else int(raw)
            except ValueError as exc:
                raise LuaParseError(f"Nombre invalide {raw!r}") from exc
            return Token("NUMBER", value, start)

        if ch.isalpha() or ch == "_":
            self.i += 1
            while self.i < self.n and (self.text[self.i].isalnum() or self.text[self.i] == "_"):
                self.i += 1
            raw = self.text[start:self.i]
            return Token("IDENT", raw, start)

        raise LuaParseError(f"Caractère inattendu {ch!r} à {start}")


class Parser:
    def __init__(self, text: str):
        self.lex = Lexer(text)
        self.current = self.lex.next()

    def eat(self, kind: str) -> Token:
        if self.current.kind != kind:
            raise LuaParseError(
                f"Attendu {kind}, reçu {self.current.kind} à {self.current.pos}"
            )
        token = self.current
        self.current = self.lex.next()
        return token

    def parse_file(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        while self.current.kind != "EOF":
            name = self.eat("IDENT").value
            self.eat("=")
            result[name] = self.parse_value()
        return result

    def parse_value(self) -> Any:
        token = self.current
        if token.kind == "{":
            return self.parse_table()
        if token.kind == "STRING":
            return self.eat("STRING").value
        if token.kind == "NUMBER":
            return self.eat("NUMBER").value
        if token.kind == "IDENT":
            value = self.eat("IDENT").value
            if value == "true":
                return True
            if value == "false":
                return False
            if value == "nil":
                return None
            return value
        raise LuaParseError(f"Valeur inattendue à {token.pos}")

    def parse_table(self) -> dict[Any, Any]:
        self.eat("{")
        result: dict[Any, Any] = {}
        auto_index = 1

        while self.current.kind != "}":
            if self.current.kind == "[":
                self.eat("[")
                key = self.parse_value()
                self.eat("]")
                self.eat("=")
                value = self.parse_value()
            elif self.current.kind == "IDENT":
                ident = self.eat("IDENT").value
                if self.current.kind == "=":
                    self.eat("=")
                    key = ident
                    value = self.parse_value()
                else:
                    key = auto_index
                    auto_index += 1
                    value = {"identifier": ident}
            else:
                key = auto_index
                auto_index += 1
                value = self.parse_value()

            result[key] = value

        self.eat("}")
        return result


def load_saved_variables(path: str | Path) -> dict[str, Any]:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8-sig", errors="replace")
    parsed = Parser(text).parse_file()
    db = parsed.get("RaidPresenceDB")
    if not isinstance(db, dict):
        raise LuaParseError("RaidPresenceDB est introuvable ou invalide.")
    return db
