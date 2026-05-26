from __future__ import annotations
from parsing.yalp_parser import Grammar, Production
from grammar.lr0_items import LR0Item, LR0State, LR0Automaton


AUGMENTED_START = "S'"


# Crea la gramática aumentada añadiendo un símbolo inicial
def augment_grammar(grammar: Grammar) -> Grammar:
    aug_prod = Production(AUGMENTED_START, [grammar.start_symbol])
    new_productions = [aug_prod] + list(grammar.productions)
    new_non_terminals = frozenset(grammar.non_terminals | {AUGMENTED_START})

    return Grammar(
        terminals=grammar.terminals,
        non_terminals=new_non_terminals,
        productions=new_productions,
        start_symbol=AUGMENTED_START,
        ignored=grammar.ignored,
        token_table=grammar.token_table,
    )


# Calcula el closure de un conjunto de ítems
def closure(items: frozenset[LR0Item], grammar: Grammar) -> frozenset[LR0Item]:
    result: set[LR0Item] = set(items)
    worklist: list[LR0Item] = list(items)

    while worklist:
        item = worklist.pop()
        sym = item.next_symbol
        if sym is None or sym not in grammar.non_terminals:
            continue
        for prod in grammar.productions:
            if prod.lhs == sym:
                new_item = LR0Item(prod.lhs, tuple(prod.rhs), 0)
                if new_item not in result:
                    result.add(new_item)
                    worklist.append(new_item)

    return frozenset(result)


# Calcula GOTO(I, X)
def goto(state_items: frozenset[LR0Item], symbol: str, grammar: Grammar) -> frozenset[LR0Item]:
    kernel: set[LR0Item] = set()
    for item in state_items:
        if item.next_symbol == symbol:
            kernel.add(item.advance())
    if not kernel:
        return frozenset()
    return closure(frozenset(kernel), grammar)


# Constuye el autómata LR(0)
def build_lr0_automaton(grammar: Grammar) -> LR0Automaton:
    aug_grammar = augment_grammar(grammar)

    start_prod = aug_grammar.productions[0]
    start_item = LR0Item(start_prod.lhs, tuple(start_prod.rhs), 0)
    initial_items = closure(frozenset({start_item}), aug_grammar)

    items_to_id: dict[frozenset, int] = {}
    automaton = LR0Automaton()

    def get_or_create_state(items: frozenset[LR0Item]) -> LR0State:
        if items in items_to_id:
            return automaton.states[items_to_id[items]]
        state_id = len(automaton.states)
        state = LR0State(id=state_id, items=items)
        automaton.states.append(state)
        items_to_id[items] = state_id
        return state

    initial_state = get_or_create_state(initial_items)
    automaton.initial_state = initial_state

    # BFS sobre los estados
    worklist: list[LR0State] = [initial_state]
    visited_ids: set[int] = set()

    # Todos los símbolos de la gramática (terminales + no-terminales)
    all_symbols = aug_grammar.terminals | aug_grammar.non_terminals

    while worklist:
        current = worklist.pop(0)
        if current.id in visited_ids:
            continue
        visited_ids.add(current.id)

        for sym in all_symbols:
            goto_items = goto(current.items, sym, aug_grammar)
            if not goto_items:
                continue
            dest = get_or_create_state(goto_items)
            automaton.add_transition(current.id, sym, dest.id)
            if dest.id not in visited_ids:
                worklist.append(dest)

    automaton._grammar = aug_grammar

    return automaton
