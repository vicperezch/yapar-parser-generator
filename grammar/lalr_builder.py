from __future__ import annotations
from parsing.yalp_parser import Grammar
from grammar.lr0_builder import augment_grammar, AUGMENTED_START
from grammar.first_follow import compute_first, first_of_sequence, EPSILON
from grammar.lr1_items import LR1Item, LR1State, LALRAutomaton


# Calcula el closure de un conjunto de ítems LR(1)
def closure_lr1(
    items: frozenset[LR1Item],
    grammar: Grammar,
    first: dict[str, set[str]],
) -> frozenset[LR1Item]:
    result: set[LR1Item] = set(items)
    worklist: list[LR1Item] = list(items)

    while worklist:
        item = worklist.pop()
        sym = item.next_symbol
        if sym is None or sym not in grammar.non_terminals:
            continue
        # Lookaheads = FIRST(resto · lookahead)
        suffix = list(item.rhs[item.dot + 1:]) + [item.lookahead]
        lookaheads = first_of_sequence(suffix, first) - {EPSILON}
        for prod in grammar.productions:
            if prod.lhs != sym:
                continue
            for la in lookaheads:
                new_item = LR1Item(prod.lhs, tuple(prod.rhs), 0, la)
                if new_item not in result:
                    result.add(new_item)
                    worklist.append(new_item)

    return frozenset(result)


# Calcula GOTO(I, X) sobre ítems LR(1)
def goto_lr1(
    state_items: frozenset[LR1Item],
    symbol: str,
    grammar: Grammar,
    first: dict[str, set[str]],
) -> frozenset[LR1Item]:
    kernel: set[LR1Item] = set()
    for item in state_items:
        if item.next_symbol == symbol:
            kernel.add(item.advance())
    if not kernel:
        return frozenset()
    return closure_lr1(frozenset(kernel), grammar, first)


# Construye la colección canónica LR(1)
def build_lr1_automaton(grammar: Grammar) -> LALRAutomaton:
    aug_grammar = augment_grammar(grammar)
    first = compute_first(aug_grammar)

    start_prod = aug_grammar.productions[0]
    start_item = LR1Item(start_prod.lhs, tuple(start_prod.rhs), 0, "$")
    initial_items = closure_lr1(frozenset({start_item}), aug_grammar, first)

    items_to_id: dict[frozenset, int] = {}
    automaton = LALRAutomaton()

    def get_or_create_state(items: frozenset[LR1Item]) -> LR1State:
        if items in items_to_id:
            return automaton.states[items_to_id[items]]
        state_id = len(automaton.states)
        state = LR1State(id=state_id, items=items)
        automaton.states.append(state)
        items_to_id[items] = state_id
        return state

    initial_state = get_or_create_state(initial_items)
    automaton.initial_state = initial_state

    worklist: list[LR1State] = [initial_state]
    visited_ids: set[int] = set()

    all_symbols = aug_grammar.terminals | aug_grammar.non_terminals

    while worklist:
        current = worklist.pop(0)
        if current.id in visited_ids:
            continue
        visited_ids.add(current.id)

        for sym in all_symbols:
            goto_items = goto_lr1(current.items, sym, aug_grammar, first)
            if not goto_items:
                continue
            dest = get_or_create_state(goto_items)
            automaton.add_transition(current.id, sym, dest.id)
            if dest.id not in visited_ids:
                worklist.append(dest)

    automaton._grammar = aug_grammar

    return automaton


# Construye el autómata LALR(1) fusionando estados LR(1) con el mismo núcleo LR(0)
def build_lalr_automaton(grammar: Grammar) -> LALRAutomaton:
    lr1 = build_lr1_automaton(grammar)

    # Agrupa los estados LR(1) por su núcleo LR(0).
    groups: dict[frozenset, list[int]] = {}
    for state in lr1.states:
        groups.setdefault(state.core, []).append(state.id)

    # Ordena por el menor id original para mantener el estado inicial en 0.
    ordered_cores = sorted(groups, key=lambda c: min(groups[c]))
    old_to_new: dict[int, int] = {}
    for new_id, core in enumerate(ordered_cores):
        for old_id in groups[core]:
            old_to_new[old_id] = new_id

    automaton = LALRAutomaton()

    # Crea los estados fusionados uniendo los ítems de cada grupo.
    for new_id, core in enumerate(ordered_cores):
        merged_items: set[LR1Item] = set()
        for old_id in groups[core]:
            merged_items |= lr1.states[old_id].items
        automaton.states.append(LR1State(id=new_id, items=frozenset(merged_items)))

    # Reasigna las transiciones a los nuevos ids.
    for from_id, trans in lr1.transitions.items():
        for sym, to_id in trans.items():
            automaton.add_transition(old_to_new[from_id], sym, old_to_new[to_id])

    automaton.initial_state = automaton.states[old_to_new[lr1.initial_state.id]]
    automaton._grammar = lr1._grammar  # type: ignore[attr-defined]

    return automaton
