import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from parsing.yalp_lexer import YalpLexer
from parsing.yalp_parser import parse_yalp, Grammar, Production
from grammar.first_follow import compute_first, compute_follow, EOF_MARKER
from grammar.lr0_builder import build_lr0_automaton, augment_grammar
from grammar.lr0_items import LR0Item
from grammar.lalr_builder import build_lalr_automaton
from slr.slr_table import build_slr_table
from lalr.lalr_table import build_lalr_table
from evaluator.string_evaluator import StringEvaluator


# Ruta de la gramática aritmética usada en las pruebas.
ARITHMETIC_YALP = os.path.join(
    os.path.dirname(__file__), "..", "examples", "arithmetic.yalp"
)


# Carga la gramática de prueba.
def get_grammar() -> Grammar:
    return parse_yalp(ARITHMETIC_YALP)


# Verifica el reconocimiento básico de tokens .yalp.
def test_yalp_lexer_tokens():
    text = "%token ID PLUS\nIGNORE WS\n%%\nexpr:\n    ID\n    ;"
    lexer = YalpLexer(text)
    tokens = lexer.tokenize()
    types = [t.type for t in tokens]
    assert "PERCENT_TOKEN" in types
    assert "UPPER_ID" in types
    assert "IGNORE" in types
    assert "SEPARATOR" in types
    assert "LOWER_ID" in types
    assert "COLON" in types
    assert "SEMICOLON" in types
    assert "EOF" in types
    print("  Correct: test_yalp_lexer_tokens")


# Verifica que los comentarios sean ignorados por el lexer.
def test_yalp_lexer_comments():
    text = "/* esto es un comentario */ %token ID\n%%\nexpr:\n    ID\n    ;"
    lexer = YalpLexer(text)
    tokens = lexer.tokenize()

    # Los comentarios no deben generar tokens.
    types = [t.type for t in tokens if t.type != "EOF"]

    assert "PERCENT_TOKEN" in types
    assert len([t for t in types if t == "UPPER_ID"]) == 2
    print("  Correct: test_yalp_lexer_comments")


# Comprueba la estructura general de la gramática.
def test_parse_grammar_structure():
    grammar = get_grammar()
    assert grammar.start_symbol == "expr"
    assert "ID" in grammar.terminals
    assert "PLUS" in grammar.terminals
    assert "TIMES" in grammar.terminals
    assert "expr" in grammar.non_terminals
    assert "term" in grammar.non_terminals
    assert "factor" in grammar.non_terminals
    assert "WS" in grammar.ignored
    print("  Correct: test_parse_grammar_structure")


# Verifica la cantidad de producciones cargadas.
def test_parse_productions_count():
    grammar = get_grammar()

    # La gramática aritmética contiene seis producciones.
    assert len(grammar.productions) == 6
    print("  Correct: test_parse_productions_count")


# Comprueba FIRST para símbolos terminales.
def test_first_terminals():
    grammar = get_grammar()
    aug = augment_grammar(grammar)
    first = compute_first(aug)

    # FIRST de un terminal es el propio terminal.
    assert first["ID"] == {"ID"}
    assert first["PLUS"] == {"PLUS"}
    print("  Correct: test_first_terminals")


# Comprueba FIRST para símbolos no terminales.
def test_first_nonterminals():
    grammar = get_grammar()
    aug = augment_grammar(grammar)
    first = compute_first(aug)

    # Los no terminales principales deben iniciar con ID o LPAREN.
    assert "ID" in first["expr"]
    assert "LPAREN" in first["expr"]
    assert "ID" in first["factor"]
    assert "LPAREN" in first["factor"]
    print("  Correct: test_first_nonterminals")


# Verifica FOLLOW del símbolo inicial.
def test_follow_start_symbol():
    grammar = get_grammar()
    aug = augment_grammar(grammar)
    first = compute_first(aug)
    follow = compute_follow(aug, first)

    # El símbolo inicial debe contener EOF en FOLLOW.
    assert EOF_MARKER in follow["expr"]
    assert "PLUS" in follow["term"] or "TIMES" in follow["term"]
    print("  Correct: test_follow_start_symbol")


# Comprueba la construcción básica del autómata LR(0).
def test_lr0_automaton_states():
    grammar = get_grammar()
    automaton = build_lr0_automaton(grammar)

    assert len(automaton.states) > 0
    assert automaton.initial_state is not None
    assert automaton.initial_state.id == 0
    print(f"  Correct: test_lr0_automaton_states ({len(automaton.states)} estados)")


# Verifica que exista el ítem inicial aumentado.
def test_lr0_initial_item():
    grammar = get_grammar()
    automaton = build_lr0_automaton(grammar)
    initial = automaton.initial_state

    # El estado inicial debe contener S' → · expr.
    items_str = [str(i) for i in initial.items]
    assert any("S'" in s for s in items_str), f"No S' item found: {items_str}"
    print("  Correct: test_lr0_initial_item")


# Verifica que la tabla SLR(1) no tenga conflictos.
def test_slr_table_no_conflicts():
    grammar = get_grammar()
    automaton = build_lr0_automaton(grammar)
    table = build_slr_table(automaton)

    if table.has_conflicts():
        print(f"  Conflictos: {table.conflicts}")

    assert not table.has_conflicts(), f"Conflictos inesperados: {table.conflicts}"
    print("  Correct: test_slr_table_no_conflicts")


# Verifica la existencia de un único estado de aceptación.
def test_slr_table_has_accept():
    grammar = get_grammar()
    automaton = build_lr0_automaton(grammar)
    table = build_slr_table(automaton)

    # Debe existir exactamente una acción accept.
    accept_states = [
        s for s, actions in table.action.items()
        if actions.get("$") == "accept"
    ]

    assert len(accept_states) == 1, f"Accept states: {accept_states}"
    print(f"  Correct: test_slr_table_has_accept (estado {accept_states[0]})")


# Construye un evaluador listo para las pruebas.
def _get_evaluator():
    grammar = get_grammar()
    automaton = build_lr0_automaton(grammar)
    table = build_slr_table(automaton)
    aug = automaton._grammar
    return StringEvaluator(table, aug), grammar.ignored


# Verifica que una expresión simple sea aceptada.
def test_evaluator_accepts_valid():
    evaluator, ignored = _get_evaluator()
    result = evaluator.evaluate(["ID", "PLUS", "ID"], ignored=ignored, trace=False)
    assert result.accepted, f"Debería aceptar: {result.message}"
    print("  Correct: test_evaluator_accepts_valid (ID PLUS ID)")


# Verifica que una expresión compleja sea aceptada.
def test_evaluator_accepts_complex():
    evaluator, ignored = _get_evaluator()
    tokens = ["LPAREN", "ID", "PLUS", "ID", "RPAREN", "TIMES", "ID"]
    result = evaluator.evaluate(tokens, ignored=ignored, trace=False)
    assert result.accepted, f"Debería aceptar: {result.message}"
    print("  Correct: test_evaluator_accepts_complex ((ID PLUS ID) TIMES ID)")


# Verifica que una secuencia inválida sea rechazada.
def test_evaluator_rejects_invalid():
    evaluator, ignored = _get_evaluator()
    result = evaluator.evaluate(["PLUS", "ID"], ignored=ignored, trace=False)
    assert not result.accepted, "Debería rechazar PLUS ID"
    print("  Correct: test_evaluator_rejects_invalid (PLUS ID)")


# Verifica que una expresión incompleta sea rechazada.
def test_evaluator_rejects_incomplete():
    evaluator, ignored = _get_evaluator()
    result = evaluator.evaluate(["ID", "PLUS"], ignored=ignored, trace=False)
    assert not result.accepted, "Debería rechazar ID PLUS (incompleto)"
    print("  Correct: test_evaluator_rejects_incomplete (ID PLUS)")


# Comprueba la construcción del autómata LALR(1).
def test_lalr_automaton_states():
    grammar = get_grammar()
    automaton = build_lalr_automaton(grammar)

    assert len(automaton.states) > 0
    assert automaton.initial_state is not None
    assert automaton.initial_state.id == 0
    print(f"  Correct: test_lalr_automaton_states ({len(automaton.states)} estados)")


# El autómata LALR debe tener el mismo número de estados que el LR(0).
def test_lalr_same_states_as_lr0():
    grammar = get_grammar()
    lr0 = build_lr0_automaton(grammar)
    lalr = build_lalr_automaton(grammar)

    assert len(lalr.states) == len(lr0.states)
    print(f"  Correct: test_lalr_same_states_as_lr0 ({len(lalr.states)} estados)")


# Verifica que la tabla LALR(1) no tenga conflictos.
def test_lalr_table_no_conflicts():
    grammar = get_grammar()
    automaton = build_lalr_automaton(grammar)
    table = build_lalr_table(automaton)

    if table.has_conflicts():
        print(f"  Conflictos: {table.conflicts}")

    assert not table.has_conflicts(), f"Conflictos inesperados: {table.conflicts}"
    print("  Correct: test_lalr_table_no_conflicts")


# Construye un evaluador LALR listo para las pruebas.
def _get_lalr_evaluator():
    grammar = get_grammar()
    automaton = build_lalr_automaton(grammar)
    table = build_lalr_table(automaton)
    aug = automaton._grammar
    return StringEvaluator(table, aug), grammar.ignored


# Verifica el reconocimiento de cadenas con el parser LALR(1).
def test_lalr_evaluator_accepts_and_rejects():
    evaluator, ignored = _get_lalr_evaluator()

    valid = evaluator.evaluate(["ID", "PLUS", "ID"], ignored=ignored, trace=False)
    assert valid.accepted, f"Debería aceptar: {valid.message}"

    complex_tokens = ["LPAREN", "ID", "PLUS", "ID", "RPAREN", "TIMES", "ID"]
    accepted = evaluator.evaluate(complex_tokens, ignored=ignored, trace=False)
    assert accepted.accepted, f"Debería aceptar: {accepted.message}"

    invalid = evaluator.evaluate(["PLUS", "ID"], ignored=ignored, trace=False)
    assert not invalid.accepted, "Debería rechazar PLUS ID"
    print("  Correct: test_lalr_evaluator_accepts_and_rejects")


# Los lookaheads de reduce LALR deben ser subconjunto de FOLLOW (más precisos que SLR).
def test_lalr_lookaheads_subset_of_follow():
    grammar = get_grammar()
    automaton = build_lalr_automaton(grammar)
    aug = automaton._grammar
    first = compute_first(aug)
    follow = compute_follow(aug, first)

    for state in automaton.states:
        for item in state.items:
            if item.is_complete and item.lhs != "S'":
                assert item.lookahead in follow[item.lhs], (
                    f"Lookahead {item.lookahead} fuera de FOLLOW({item.lhs})"
                )
    print("  Correct: test_lalr_lookaheads_subset_of_follow")


# Ejecuta todas las pruebas sin usar pytest.
if __name__ == "__main__":
    print("\n" + "="*50)
    print("YAPar – Tests Unitarios")
    print("="*50)

    tests = [
        test_yalp_lexer_tokens,
        test_yalp_lexer_comments,
        test_parse_grammar_structure,
        test_parse_productions_count,
        test_first_terminals,
        test_first_nonterminals,
        test_follow_start_symbol,
        test_lr0_automaton_states,
        test_lr0_initial_item,
        test_slr_table_no_conflicts,
        test_slr_table_has_accept,
        test_evaluator_accepts_valid,
        test_evaluator_accepts_complex,
        test_evaluator_rejects_invalid,
        test_evaluator_rejects_incomplete,
        test_lalr_automaton_states,
        test_lalr_same_states_as_lr0,
        test_lalr_table_no_conflicts,
        test_lalr_evaluator_accepts_and_rejects,
        test_lalr_lookaheads_subset_of_follow,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  Error: {test.__name__}: {e}")
            failed += 1

    print(f"\n  Resultado: {passed} passed, {failed} failed")