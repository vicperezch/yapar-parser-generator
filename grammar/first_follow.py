from __future__ import annotations
from parsing.yalp_parser import Grammar

EPSILON = ""
EOF_MARKER = "$"


# Calcula FIRST (X) para todos los símbolos de la gramática
def compute_first(grammar: Grammar) -> dict[str, set[str]]:
    first: dict[str, set[str]] = {}

    # Inicializar terminales
    for t in grammar.terminals:
        first[t] = {t}
    first[EOF_MARKER] = {EOF_MARKER}
    first[EPSILON] = {EPSILON}

    # Inicializar no-terminales con conjuntos vacíos
    for nt in grammar.non_terminals:
        first[nt] = set()

    changed = True
    while changed:
        changed = False
        for prod in grammar.productions:
            lhs = prod.lhs
            before = len(first[lhs])

            if not prod.rhs:
                # producción vacía
                first[lhs].add(EPSILON)
            else:
                all_have_epsilon = True
                for sym in prod.rhs:
                    sym_first = first.get(sym, {sym})
                    # Añadir FIRST(sym) \ {ε}
                    first[lhs] |= sym_first - {EPSILON}
                    if EPSILON not in sym_first:
                        all_have_epsilon = False
                        break
                if all_have_epsilon:
                    first[lhs].add(EPSILON)

            if len(first[lhs]) != before:
                changed = True

    return first


# Calcula FOLLOW(A) para todos los no terminales
def compute_follow(grammar: Grammar, first: dict[str, set[str]]) -> dict[str, set[str]]:
    follow: dict[str, set[str]] = {nt: set() for nt in grammar.non_terminals}
    follow[grammar.start_symbol].add(EOF_MARKER)

    changed = True
    while changed:
        changed = False
        for prod in grammar.productions:
            trailer: set[str] = set(follow[prod.lhs])
            # recorrer RHS de derecha a izquierda
            for sym in reversed(prod.rhs):
                if sym in grammar.non_terminals:
                    before = len(follow[sym])
                    follow[sym] |= trailer
                    if len(follow[sym]) != before:
                        changed = True
                    # actualizar trailer
                    sym_first = first.get(sym, set())
                    if EPSILON in sym_first:
                        trailer = (trailer | sym_first) - {EPSILON}
                    else:
                        trailer = sym_first - {EPSILON}
                else:
                    # terminal
                    trailer = first.get(sym, {sym}) - {EPSILON}

    return follow


# Calcula FIRST para una secuancia de símbolos
def first_of_sequence(sequence: list[str], first: dict[str, set[str]]) -> set[str]:
    result: set[str] = set()
    for sym in sequence:
        sym_first = first.get(sym, {sym})
        result |= sym_first - {EPSILON}
        if EPSILON not in sym_first:
            return result
    result.add(EPSILON)
    return result
