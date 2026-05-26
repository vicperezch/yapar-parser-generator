"""
Módulo 2 – YAPar Lexer
Tokeniza archivos .yalp (gramáticas YAPar).

Tokens reconocidos:
  COMMENT   /* ... */
  PERCENT_TOKEN  %token
  IGNORE    IGNORE
  SEPARATOR %%
  COLON     :
  PIPE      |
  SEMICOLON ;
  UPPER_ID  TOKEN en mayúsculas (terminal)
  LOWER_ID  produccion en minúsculas (no-terminal)
  EOF
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Token
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: str
    value: str
    line: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class YalpLexerError(Exception):
    pass


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class YalpLexer:
    """Convierte texto fuente de un archivo .yalp en una secuencia de tokens."""

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.text):
            tok = self._next_token()
            if tok is not None:
                tokens.append(tok)
        tokens.append(Token("EOF", "", self.line))
        return tokens

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _next_token(self) -> Token | None:
        self._skip_whitespace()
        if self.pos >= len(self.text):
            return None

        ch = self.text[self.pos]

        # Comentario /* ... */
        if self.text.startswith("/*", self.pos):
            self._skip_block_comment()
            return None

        # Separador %%
        if self.text.startswith("%%", self.pos):
            tok = Token("SEPARATOR", "%%", self.line)
            self.pos += 2
            return tok

        # Directiva %token
        if self.text.startswith("%token", self.pos) and (
            self.pos + 6 >= len(self.text) or not self.text[self.pos + 6].isalnum()
        ):
            tok = Token("PERCENT_TOKEN", "%token", self.line)
            self.pos += 6
            return tok

        # Símbolo %  (solo % suelto, no debería aparecer pero lo manejamos)
        if ch == "%":
            tok = Token("PERCENT", "%", self.line)
            self.pos += 1
            return tok

        # Puntuación
        if ch == ":":
            tok = Token("COLON", ":", self.line)
            self.pos += 1
            return tok

        if ch == "|":
            tok = Token("PIPE", "|", self.line)
            self.pos += 1
            return tok

        if ch == ";":
            tok = Token("SEMICOLON", ";", self.line)
            self.pos += 1
            return tok

        # Identificador o palabra clave
        if ch.isalpha() or ch == "_":
            return self._read_ident()

        raise YalpLexerError(
            f"Caracter inesperado {ch!r} en línea {self.line}"
        )

    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == "\n":
                self.line += 1
            self.pos += 1

    def _skip_block_comment(self):
        """Salta un comentario /* ... */."""
        start_line = self.line
        self.pos += 2  # salta /*
        while self.pos < len(self.text):
            if self.text.startswith("*/", self.pos):
                self.pos += 2
                return
            if self.text[self.pos] == "\n":
                self.line += 1
            self.pos += 1
        raise YalpLexerError(
            f"Comentario sin cerrar que inicia en línea {start_line}"
        )

    def _read_ident(self) -> Token:
        start = self.pos
        start_line = self.line
        while self.pos < len(self.text) and (
            self.text[self.pos].isalnum() or self.text[self.pos] == "_"
        ):
            self.pos += 1
        word = self.text[start : self.pos]

        # Palabras reservadas especiales (antes de checar mayúsculas)
        if word == "IGNORE":
            return Token("IGNORE", word, start_line)

        # Terminal: identificador donde TODOS los caracteres alfabéticos son mayúsculas
        # Ejemplos válidos: ID, PLUS, TOKEN_1, WS
        if all(c.isupper() or c.isdigit() or c == "_" for c in word) and any(c.isalpha() for c in word):
            return Token("UPPER_ID", word, start_line)

        # No-terminal: cualquier identificador con al menos una minúscula
        return Token("LOWER_ID", word, start_line)
