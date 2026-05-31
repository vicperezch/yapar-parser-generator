import argparse
import os
import sys

from parsing.yalp_parser import parse_yalp
from grammar.lr0_builder import build_lr0_automaton
from grammar.lalr_builder import build_lalr_automaton
from grammar.first_follow import compute_first, compute_follow
from slr.slr_table import build_slr_table
from lalr.lalr_table import build_lalr_table
from visualizer.automaton_renderer import render_automaton_png, _node_label_lalr
from evaluator.string_evaluator import StringEvaluator, print_parse_trace
from yalex_adapter import invoke_yalex, load_generated_lexer, tokenize_with_lexer, tokenize_simple


# Imprime un separador con un título opcional.
def _sep(title: str = "", width: int = 60):
    if title:
        pad = (width - len(title) - 2) // 2
        print("\n" + "─" * pad + f" {title} " + "─" * pad)
    else:
        print("─" * width)


# Ejecuta el flujo principal de YAPar.
def main():
    parser = argparse.ArgumentParser(
        prog="yapar",
        description="YAPar – Generador de Analizadores Sintácticos SLR(1) / LALR(1)",
    )
    parser.add_argument("grammar", help="Archivo .yalp con la gramática")
    parser.add_argument("-l", "--lexer", help="Archivo .yal de YALex (opcional)")
    parser.add_argument("-i", "--input", help="Archivo con cadenas a evaluar")
    parser.add_argument("-o", "--output", default="output", help="Directorio de salida")
    parser.add_argument("--no-png", action="store_true", help="Omitir generación PNG")
    parser.add_argument("--lexer-py", help="Ruta al lexer .py ya generado por YALex")
    parser.add_argument("--entrypoint", default="token", help="Entrypoint del lexer")
    parser.add_argument("--method", choices=["slr", "lalr"], default="slr", help="Método de construcción de la tabla")
    args = parser.parse_args()

    if not os.path.exists(args.grammar):
        print(f"ERROR: archivo de gramática '{args.grammar}' no encontrado.")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    _sep("FASE 1 – YALex")
    lexer_module = None

    if args.lexer_py:
        # Carga un lexer generado previamente.
        print(f"  Cargando lexer generado: {args.lexer_py}")
        lexer_module = load_generated_lexer(args.lexer_py)

        if lexer_module:
            print("  Lexer cargado correctamente.")
        else:
            print("  No se pudo cargar el lexer. Se utilizará el modo standalone.")

    elif args.lexer:
        # Genera y carga el lexer desde un archivo .yal.
        print(f"  Archivo .yal: {args.lexer}")

        if not os.path.exists(args.lexer):
            print(f"  Archivo '{args.lexer}' no encontrado. Se utilizará el modo standalone.")
        else:
            generated_py = os.path.join(args.output, "thelexer.py")
            result_path = invoke_yalex(args.lexer, generated_py)

            if result_path:
                lexer_module = load_generated_lexer(result_path)

                if lexer_module:
                    print("  YALex ejecutado correctamente.")
                else:
                    print("  No fue posible cargar el lexer generado. Se utilizará el modo standalone.")
            else:
                print("  Error al ejecutar YALex. Se utilizará el modo standalone.")

    else:
        print("  Modo standalone: los tokens se leerán desde el archivo de entrada.")

    # Carga la gramática especificada.
    _sep("FASE 2 – Parser YAPar")
    print(f"  Archivo: {args.grammar}")

    grammar = parse_yalp(args.grammar)
    grammar.print_summary()

    is_lalr = args.method == "lalr"
    method_name = "LALR(1)" if is_lalr else "SLR(1)"

    # Construye el autómata y calcula FIRST/FOLLOW.
    automaton_name = "LALR" if is_lalr else "LR(0)"
    _sep(f"FASE 3 – Autómata {automaton_name}")
    print("  Construyendo gramática aumentada y colecciones canónicas...")

    if is_lalr:
        automaton = build_lalr_automaton(grammar)
    else:
        automaton = build_lr0_automaton(grammar)
    aug_grammar = automaton._grammar  # type: ignore[attr-defined]

    print(f"  {automaton}")

    first = compute_first(aug_grammar)

    print("\n  FIRST:")
    for nt in sorted(aug_grammar.non_terminals):
        print(f"    FIRST({nt}) = {sorted(first.get(nt, set()))}")

    # FOLLOW solo es relevante para SLR(1).
    if not is_lalr:
        follow = compute_follow(aug_grammar, first)
        print("\n  FOLLOW:")
        for nt in sorted(aug_grammar.non_terminals):
            print(f"    FOLLOW({nt}) = {sorted(follow.get(nt, set()))}")

    # Genera la tabla de parsing.
    _sep(f"FASE 4 – Tabla {method_name}")
    table = build_lalr_table(automaton) if is_lalr else build_slr_table(automaton)

    if table.has_conflicts():
        print("  Conflictos detectados:")
        for c in table.conflicts:
            print(f"    {c}")
    else:
        print(f"  No se detectaron conflictos {method_name}.")

    print()

    # Imprime la tabla usando la gramática original.
    table.print_table(grammar, ignored=grammar.ignored)

    # Genera la visualización del autómata.
    _sep("FASE 5 – Visualizador")

    if not args.no_png:
        png_path = os.path.join(args.output, "lr0_automaton.png")
        label_fn = _node_label_lalr if is_lalr else None
        if label_fn:
            result_png = render_automaton_png(automaton, png_path, label_fn)
        else:
            result_png = render_automaton_png(automaton, png_path)

        if result_png:
            print(f"  PNG generado: {result_png}")
        else:
            print("  No fue posible generar el PNG. Verifique la instalación de pydot y Graphviz.")

    # Evalúa las cadenas de entrada.
    if not args.input:
        _sep()
        print("\nProceso finalizado. No se proporcionó un archivo de entrada.")
        return

    _sep("FASE 6 – Evaluación de Cadenas")

    if not os.path.exists(args.input):
        print(f"  ERROR: archivo de entrada '{args.input}' no encontrado.")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as fh:
        lines = [l.lstrip('\ufeff').rstrip("\n") for l in fh if l.strip().lstrip('\ufeff') and not l.strip().lstrip('\ufeff').startswith("#")]

    evaluator = StringEvaluator(table, aug_grammar)
    ignore_set = grammar.ignored

    results_path = os.path.join(args.output, "parse_results.txt")

    with open(results_path, "w", encoding="utf-8") as out_file:
        for idx, line in enumerate(lines, 1):
            print(f"\n  Cadena {idx}: {line!r}")
            out_file.write(f"\nCadena {idx}: {line!r}\n")

            # Obtiene los tokens de la cadena de entrada.
            if lexer_module:
                try:
                    tokens = tokenize_with_lexer(
                        line, lexer_module, args.entrypoint, ignore_set
                    )
                    token_types = [t[0] for t in tokens]

                except Exception as e:
                    print(f"    Error léxico: {e}")
                    out_file.write(f"  ERROR LÉXICO: {e}\n")
                    continue
            else:
                # Interpreta la línea como una secuencia de tokens.
                token_types = tokenize_simple(line, ignore_set=ignore_set)

            print(f"  Tokens: {token_types}")

            result = evaluator.evaluate(token_types, trace=True)
            print_parse_trace(result)

            verdict = str(result)
            print(f"  {verdict}")

            out_file.write(f"  Tokens: {token_types}\n")
            out_file.write(f"  Resultado: {verdict}\n")

    print(f"\n  Resultados guardados en: {results_path}")

    _sep()
    print("\nEjecución finalizada.")


if __name__ == "__main__":
    main()