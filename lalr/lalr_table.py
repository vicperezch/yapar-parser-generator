from __future__ import annotations
from grammar.lr1_items import LALRAutomaton
from grammar.lr0_builder import AUGMENTED_START
from grammar.first_follow import EOF_MARKER
from parsing.yalp_parser import Grammar
from slr.slr_table import SLRTable


# Construye una tabla LALR(1) a partir de un autómata LALR.
class LALRTableBuilder:

    def __init__(self, automaton: LALRAutomaton):
        self.automaton = automaton
        self.grammar: Grammar = automaton._grammar  # type: ignore[attr-defined]

    # Genera las tablas ACTION y GOTO del parser.
    def build(self) -> SLRTable:
        table = SLRTable()

        # Relaciona cada producción con su índice original.
        prod_index = {
            (p.lhs, tuple(p.rhs)): i
            for i, p in enumerate(self.grammar.productions)
        }

        for state in self.automaton.states:
            sid = state.id
            table.action[sid] = {}
            table.goto[sid] = {}

            for item in state.items:
                sym = item.next_symbol

                # Procesa transiciones shift y goto.
                if sym is not None:
                    dest = self.automaton.transitions.get(sid, {}).get(sym)
                    if dest is None:
                        continue

                    if sym in self.grammar.terminals:
                        action_str = f"shift {dest}"
                        self._set_action(table, sid, sym, action_str)

                    elif sym in self.grammar.non_terminals:
                        table.goto[sid][sym] = dest

                # Procesa acciones reduce y accept.
                else:
                    if item.lhs == AUGMENTED_START:
                        # Marca la aceptación de la entrada.
                        self._set_action(table, sid, EOF_MARKER, "accept")
                    else:
                        key = (item.lhs, item.rhs)
                        prod_idx = prod_index.get(key)
                        if prod_idx is None:
                            continue
                        action_str = f"reduce {prod_idx}"
                        # El lookahead LALR del ítem es preciso por estado.
                        self._set_action(table, sid, item.lookahead, action_str)

        return table

    # Registra una acción y reporta conflictos cuando aparecen.
    def _set_action(self, table: SLRTable, state: int, symbol: str, action: str):
        existing = table.action[state].get(symbol)
        if existing is None:
            table.action[state][symbol] = action
        elif existing != action:
            conflict_msg = (
                f"CONFLICTO en estado {state}, símbolo '{symbol}': "
                f"'{existing}' vs '{action}'"
            )
            table.conflicts.append(conflict_msg)

            # Prioriza shift cuando existe un conflicto.
            if action.startswith("shift"):
                table.action[state][symbol] = action


# Construye una tabla LALR(1) desde un autómata LALR.
def build_lalr_table(automaton: LALRAutomaton) -> SLRTable:
    builder = LALRTableBuilder(automaton)
    return builder.build()
