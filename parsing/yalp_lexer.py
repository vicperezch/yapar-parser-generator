from dataclasses import dataclass

# Representa un token generado por el lexer.
@dataclass
class Token:
    type: str
    value: str
    line: int

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, line={self.line})"


class YalpLexerError(Exception):
    pass


# Convierte un archivo .yalp en una secuencia de tokens.
class YalpLexer:

    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1

    # Tokeniza el texto completo de entrada.
    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.text):
            tok = self._next_token()
            if tok is not None:
                tokens.append(tok)
        tokens.append(Token("EOF", "", self.line))
        return tokens

    # Obtiene el siguiente token válido de la entrada.
    def _next_token(self) -> Token | None:
        self._skip_whitespace()
        if self.pos >= len(self.text):
            return None

        ch = self.text[self.pos]

        # Ignora comentarios de bloque.
        if self.text.startswith("/*", self.pos):
            self._skip_block_comment()
            return None

        # Reconoce el separador de secciones.
        if self.text.startswith("%%", self.pos):
            tok = Token("SEPARATOR", "%%", self.line)
            self.pos += 2
            return tok

        # Reconoce la directiva %token.
        if self.text.startswith("%token", self.pos) and (
            self.pos + 6 >= len(self.text) or not self.text[self.pos + 6].isalnum()
        ):
            tok = Token("PERCENT_TOKEN", "%token", self.line)
            self.pos += 6
            return tok

        # Maneja el símbolo % de forma individual.
        if ch == "%":
            tok = Token("PERCENT", "%", self.line)
            self.pos += 1
            return tok

        # Reconoce símbolos de puntuación.
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

        # Reconoce identificadores y palabras reservadas.
        if ch.isalpha() or ch == "_":
            return self._read_ident()

        raise YalpLexerError(
            f"Caracter inesperado {ch!r} en línea {self.line}"
        )

    # Avanza sobre espacios en blanco y saltos de línea.
    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            if self.text[self.pos] == "\n":
                self.line += 1
            self.pos += 1

    # Omite el contenido de un comentario de bloque.
    def _skip_block_comment(self):
        start_line = self.line
        self.pos += 2
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

    # Lee un identificador y determina su tipo.
    def _read_ident(self) -> Token:
        start = self.pos
        start_line = self.line
        while self.pos < len(self.text) and (
            self.text[self.pos].isalnum() or self.text[self.pos] == "_"
        ):
            self.pos += 1
        word = self.text[start : self.pos]

        # Reconoce palabras reservadas.
        if word == "IGNORE":
            return Token("IGNORE", word, start_line)

        # Clasifica identificadores terminales.
        if all(c.isupper() or c.isdigit() or c == "_" for c in word) and any(c.isalpha() for c in word):
            return Token("UPPER_ID", word, start_line)

        # Clasifica identificadores no terminales.
        return Token("LOWER_ID", word, start_line)