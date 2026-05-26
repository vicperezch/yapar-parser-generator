"""
Módulo 2 – YAPar Parser
Convierte la secuencia de tokens del .yalp en una estructura de gramática.

Estructura producida:
  Grammar
    terminals    : frozenset[str]          — tokens declarados con %token
    non_terminals: frozenset[str]          — lados izquierdos de producciones
    productions  : list[Production]        — reglas de la gramática
    start_symbol : str                     — primer no-terminal declarado
    ignored      : frozenset[str]          — tokens con IGNORE
    token_table  : dict[str, str] | None   — tabla del lexer (nombre → patrón)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from .yalp_lexer import Token, YalpLexer, YalpLexerError


# ---------------------------------------------------------------------------
# Estructuras de datos de la gramática
# ---------------------------------------------------------------------------

@dataclass
class Production:
    """Representa una producción A → α."""
    lhs: str                        # lado izquierdo (no-terminal)
    rhs: list[str]                  # lado derecho (lista de símbolos)

    def __repr__(self) -> str:
        rhs_str = " ".join(self.rhs) if self.rhs else "ε"
        return f"{self.lhs} → {rhs_str}"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Production):
            return False
        return self.lhs == other.lhs and self.rhs == other.rhs

    def __hash__(self):
        return hash((self.lhs, tuple(self.rhs)))


@dataclass
class Grammar:
    """Gramática libre de contexto estructurada."""
    terminals: frozenset[str] = field(default_factory=frozenset)
    non_terminals: frozenset[str] = field(default_factory=frozenset)
    productions: list[Production] = field(default_factory=list)
    start_symbol: str = ""
    ignored: frozenset[str] = field(default_factory=frozenset)
    token_table: Optional[dict] = None          # inyectado desde el Módulo 1

    def productions_for(self, nt: str) -> list[Production]:
        """Retorna todas las producciones cuyo LHS es nt."""
        return [p for p in self.productions if p.lhs == nt]

    def print_summary(self):
        print(f"  Símbolo inicial : {self.start_symbol}")
        print(f"  Terminales      : {sorted(self.terminals)}")
        print(f"  No-terminales   : {sorted(self.non_terminals)}")
        print(f"  Ignorados       : {sorted(self.ignored)}")
        print(f"  Producciones ({len(self.productions)}):")
        for p in self.productions:
            print(f"    {p}")


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

class YalpParserError(Exception):
    pass


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class YalpParser:
    """
    Parser descendente recursivo para archivos .yalp.

    Gramática del formato:
        file          → token_section SEPARATOR production_section
        token_section → (%token UPPER_ID+  | IGNORE UPPER_ID)*
        production_section → production*
        production    → LOWER_ID COLON rule (PIPE rule)* SEMICOLON
        rule          → symbol*
        symbol        → UPPER_ID | LOWER_ID
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos = 0

    # ------------------------------------------------------------------
    # Utilidades de navegación
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token("EOF", "", -1)

    def _advance(self) -> Token:
        tok = self._current()
        self.pos += 1
        return tok

    def _match(self, *types: str) -> bool:
        return self._current().type in types

    def _expect(self, type_: str) -> Token:
        tok = self._current()
        if tok.type != type_:
            raise YalpParserError(
                f"Se esperaba {type_!r}, pero se encontró {tok.type!r} "
                f"({tok.value!r}) en línea {tok.line}"
            )
        return self._advance()

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------

    def parse(self) -> Grammar:
        tokens_declared: list[str] = []
        ignored: set[str] = set()

        # ---- Sección de TOKENS ----
        while not self._match("SEPARATOR", "EOF"):
            if self._match("PERCENT_TOKEN"):
                self._advance()
                # puede haber uno o más UPPER_ID en la misma línea
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

        # ---- %% separador ----
        self._expect("SEPARATOR")

        # ---- Sección de PRODUCCIONES ----
        productions: list[Production] = []
        start_symbol: str = ""

        while not self._match("EOF"):
            lhs_tok = self._expect("LOWER_ID")
            lhs = lhs_tok.value
            if not start_symbol:
                start_symbol = lhs

            self._expect("COLON")

            # primera alternativa
            rhs = self._parse_rhs()
            productions.append(Production(lhs, rhs))

            # alternativas adicionales separadas por |
            while self._match("PIPE"):
                self._advance()
                rhs = self._parse_rhs()
                productions.append(Production(lhs, rhs))

            self._expect("SEMICOLON")

        # ---- Construir gramática ----
        non_terminals = frozenset(p.lhs for p in productions)
        terminals = frozenset(t for t in tokens_declared if t not in non_terminals)

        return Grammar(
            terminals=terminals,
            non_terminals=non_terminals,
            productions=productions,
            start_symbol=start_symbol,
            ignored=frozenset(ignored),
        )

    def _parse_rhs(self) -> list[str]:
        """Lee una secuencia de símbolos hasta encontrar | ; o EOF."""
        symbols: list[str] = []
        while self._match("UPPER_ID", "LOWER_ID"):
            symbols.append(self._advance().value)
        return symbols


# ---------------------------------------------------------------------------
# Función de conveniencia
# ---------------------------------------------------------------------------

def parse_yalp(file_path: str, token_table: Optional[dict] = None) -> Grammar:
    """
    Lee un archivo .yalp y retorna una Grammar estructurada.

    Args:
        file_path  : ruta al archivo .yalp
        token_table: tabla de tokens del Módulo 1 (opcional)
    """
    with open(file_path, "r", encoding="utf-8") as fh:
        text = fh.read()

    lexer = YalpLexer(text)
    tokens = lexer.tokenize()
    parser = YalpParser(tokens)
    grammar = parser.parse()
    grammar.token_table = token_table
    return grammar
