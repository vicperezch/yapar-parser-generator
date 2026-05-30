from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .yalp_lexer import Token, YalpLexer, YalpLexerError

# Representa una producción de la gramática.
@dataclass
class Production:
    lhs: str
    rhs: list[str]

    def __repr__(self) -> str:
        rhs_str = " ".join(self.rhs) if self.rhs else "ε"
        return f"{self.lhs} → {rhs_str}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Production):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs)))


# Almacena la información completa de una gramática.
@dataclass
class Grammar:
    terminals: frozenset[str] = field(default_factory=frozenset)
    non_terminals: frozenset[str] = field(default_factory=frozenset)
    productions: list[Production] = field(default_factory=list)
    start_symbol: str = ""
    ignored: frozenset[str] = field(default_factory=frozenset)
    token_table: Optional[dict] = None

    # Retorna las producciones asociadas a un no terminal.
    def productions_for(self, nt: str) -> list[Production]:
        return [p for p in self.productions if p.lhs == nt]

    # Imprime un resumen de la gramática.
    def print_summary(self):
        print(f"  Símbolo inicial : {self.start_symbol}")
        print(f"  Terminales      : {sorted(self.terminals)}")
        print(f"  No-terminales   : {sorted(self.non_terminals)}")
        print(f"  Ignorados       : {sorted(self.ignored)}")
        print(f"  Producciones ({len(self.productions)}):")
        for p in self.productions:
            print(f"    {p}")


class YalpParserError(Exception):
    pass


# Analiza un archivo .yalp y construye una gramática.
class YalpParser:

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # Retorna el token actual.
    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token("EOF", "", -1)

    # Avanza al siguiente token.
    def _advance(self) -> Token:
        tok = self._current()
        self.pos += 1
        return tok

    # Verifica si el token actual coincide con alguno de los tipos dados.
    def _match(self, *types: str) -> bool:
        return self._current().type in types

    # Consume un token del tipo esperado o lanza un error.
    def _expect(self, type_: str) -> Token:
        tok = self._current()
        if tok.type != type_:
            raise YalpParserError(
                f"Se esperaba {type_!r}, pero se encontró {tok.type!r} "
                f"({tok.value!r}) en línea {tok.line}"
            )
        return self._advance()

    # Construye la gramática a partir de la secuencia de tokens.
    def parse(self) -> Grammar:
        tokens_declared: list[str] = []
        ignored: set[str] = set()

        # Procesa la sección de tokens declarados.
        while not self._match("SEPARATOR", "EOF"):
            if self._match("PERCENT_TOKEN"):
                self._advance()

                # Lee los tokens declarados en una línea.
                while self._match("UPPER_ID"):
                    tokens_declared.append(self._advance().value)

            elif self._match("IGNORE"):
                self._advance()
                name = self._expect("UPPER_ID").value
                ignored.add(name)

            else:
                tok = self._current()
                raise YalpParserError(
                    f"Token inesperado {tok.type!r} ({tok.value!r}) "
                    f"en sección de TOKENS, línea {tok.line}"
                )

        # Consume el separador entre secciones.
        self._expect("SEPARATOR")

        productions: list[Production] = []
        start_symbol: str = ""

        # Procesa todas las producciones de la gramática.
        while not self._match("EOF"):
            lhs_tok = self._expect("LOWER_ID")
            lhs = lhs_tok.value

            if not start_symbol:
                start_symbol = lhs

            self._expect("COLON")

            # Lee la primera alternativa de producción.
            rhs = self._parse_rhs()
            productions.append(Production(lhs, rhs))

            # Lee alternativas separadas por PIPE.
            while self._match("PIPE"):
                self._advance()
                rhs = self._parse_rhs()
                productions.append(Production(lhs, rhs))

            self._expect("SEMICOLON")

        # Construye la estructura final de la gramática.
        non_terminals = frozenset(p.lhs for p in productions)
        terminals = frozenset(t for t in tokens_declared if t not in non_terminals)

        return Grammar(
            terminals=terminals,
            non_terminals=non_terminals,
            productions=productions,
            start_symbol=start_symbol,
            ignored=frozenset(ignored),
        )

    # Lee una secuencia de símbolos del lado derecho de una producción.
    def _parse_rhs(self) -> list[str]:
        symbols: list[str] = []
        while self._match("UPPER_ID", "LOWER_ID"):
            symbols.append(self._advance().value)
        return symbols


# Carga un archivo .yalp y retorna una gramática estructurada.
def parse_yalp(file_path: str, token_table: Optional[dict] = None) -> Grammar:
    with open(file_path, "r", encoding="utf-8") as fh:
        text = fh.read().lstrip('\ufeff')

    lexer = YalpLexer(text)
    tokens = lexer.tokenize()
    parser = YalpParser(tokens)
    grammar = parser.parse()
    grammar.token_table = token_table
    return grammar