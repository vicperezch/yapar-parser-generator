"""
main.py – Punto de entrada de YAPar

Uso:
  python main.py parser.yalp -l lexer.yal -i cadenas.txt -o output/ [--html] [--no-png]

Argumentos:
  parser.yalp       Archivo con especificaciones gramaticales (requerido)
  -l / --lexer      Archivo .yal de YALex (opcional, activa integración léxica)
  -i / --input      Archivo con cadenas a evaluar (una por línea)
  -o / --output     Directorio de salida (default: output/)
  --no-png          Omite la generación del PNG (útil si graphviz no está instalado)
  --lexer-py        Ruta al lexer .py ya generado (omite ejecutar yalex)
  --entrypoint      Nombre del entrypoint del lexer (default: 'token')
"""

import argparse
import os
import sys

from parsing.yalp_parser import parse_yalp
from grammar.lr0_builder import build_lr0_automaton
from grammar.first_follow import compute_first, compute_follow
from slr.slr_table import build_slr_table
from visualizer.automaton_renderer import render_automaton_png
from evaluator.string_evaluator import StringEvaluator, print_parse_trace
from yalex_adapter import invoke_yalex, load_generated_lexer, tokenize_with_lexer, tokenize_simple


# ---------------------------------------------------------------------------
# Helpers de salida
# ---------------------------------------------------------------------------

def _sep(title: str = "", width: int = 60):
    if title:
        pad = (width - len(title) - 2) // 2
        print("\n" + "─" * pad + f" {title} " + "─" * pad)
    else:
        print("─" * width)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog="yapar",
        description="YAPar – Generador de Analizadores Sintácticos SLR(1)",
    )
    parser.add_argument("grammar", help="Archivo .yalp con la gramática")
    parser.add_argument("-l", "--lexer", help="Archivo .yal de YALex (opcional)")
    parser.add_argument("-i", "--input", help="Archivo con cadenas a evaluar")
    parser.add_argument("-o", "--output", default="output", help="Directorio de salida")
    parser.add_argument("--no-png", action="store_true", help="Omitir generación PNG")
    parser.add_argument("--lexer-py", help="Ruta al lexer .py ya generado por YALex")
    parser.add_argument("--entrypoint", default="token", help="Entrypoint del lexer")
    args = parser.parse_args()

    if not os.path.exists(args.grammar):
        print(f"ERROR: archivo de gramática '{args.grammar}' no encontrado.")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    # ── FASE 1: YALex ────────────────────────────────────────────
    _sep("FASE 1 – YALex (Integración Léxica)")
    lexer_module = None

    if args.lexer_py:
        # Modo B: lexer .py ya generado
        print(f"  Cargando lexer generado: {args.lexer_py}")
        lexer_module = load_generated_lexer(args.lexer_py)
        if lexer_module:
            print("  ✓ Lexer cargado correctamente.")
        else:
            print("  ✗ No se pudo cargar el lexer — modo standalone.")

    elif args.lexer:
        # Modo A: invocar YALex automáticamente desde el .yal
        print(f"  Archivo .yal: {args.lexer}")
        if not os.path.exists(args.lexer):
            print(f"  ✗ Archivo '{args.lexer}' no encontrado — modo standalone.")
        else:
            generated_py = os.path.join(args.output, "thelexer.py")
            result_path = invoke_yalex(args.lexer, generated_py)
            if result_path:
                lexer_module = load_generated_lexer(result_path)
                if lexer_module:
                    print("  ✓ YALex ejecutado y lexer cargado correctamente.")
                else:
                    print("  ✗ Lexer generado pero no se pudo cargar — modo standalone.")
            else:
                print("  ✗ YALex falló — modo standalone.")

    else:
        print("  Modo standalone: los tokens se leerán como strings desde el archivo de entrada.")

    # ── FASE 2: Parser YAPar ──────────────────────────────────────────────
    _sep("FASE 2 – Parser YAPar (Lectura de Gramática)")
    print(f"  Archivo: {args.grammar}")
    grammar = parse_yalp(args.grammar)
    grammar.print_summary()

    # ── FASE 3: Autómata LR(0) ────────────────────────────────────────────
    _sep("FASE 3 – Autómata LR(0)")
    print("  Construyendo gramática aumentada y colecciones canónicas …")
    automaton = build_lr0_automaton(grammar)
    aug_grammar = automaton._grammar  # type: ignore[attr-defined]
    print(f"  ✓ {automaton}")

    first = compute_first(aug_grammar)
    follow = compute_follow(aug_grammar, first)

    print("\n  FIRST:")
    for nt in sorted(aug_grammar.non_terminals):
        print(f"    FIRST({nt}) = {sorted(first.get(nt, set()))}")

    print("\n  FOLLOW:")
    for nt in sorted(aug_grammar.non_terminals):
        print(f"    FOLLOW({nt}) = {sorted(follow.get(nt, set()))}")

    # ── FASE 4: Tabla SLR(1) ──────────────────────────────────────────────
    _sep("FASE 4 – Tabla SLR(1)")
    slr_table = build_slr_table(automaton)

    if slr_table.has_conflicts():
        print("  ⚠ Conflictos detectados:")
        for c in slr_table.conflicts:
            print(f"    {c}")
    else:
        print("  ✓ Gramática SLR(1) sin conflictos.")

    print()
    # Usamos grammar (original) para imprimir sin mostrar S'
    slr_table.print_table(grammar, ignored=grammar.ignored)

    # ── FASE 5: Visualizador ──────────────────────────────────────────────
    _sep("FASE 5 – Visualizador del Autómata")

    if not args.no_png:
        png_path = os.path.join(args.output, "lr0_automaton.png")
        result_png = render_automaton_png(automaton, png_path)
        if result_png:
            print(f"  ✓ PNG generado: {result_png}")
        else:
            print("  ✗ PNG no generado (instala pydot y graphviz).")



    # ── FASE 6: Evaluador de cadenas ──────────────────────────────────────
    if not args.input:
        _sep()
        print("\nYAPar finalizado. (Sin archivo de entrada para evaluar cadenas)")
        return

    _sep("FASE 6 – Evaluación de Cadenas")
    if not os.path.exists(args.input):
        print(f"  ERROR: archivo de entrada '{args.input}' no encontrado.")
        sys.exit(1)

    with open(args.input, "r", encoding="utf-8") as fh:
        lines = [l.lstrip('\ufeff').rstrip("\n") for l in fh if l.strip().lstrip('\ufeff') and not l.strip().lstrip('\ufeff').startswith("#")]

    evaluator = StringEvaluator(slr_table, aug_grammar)
    ignore_set = grammar.ignored

    results_path = os.path.join(args.output, "parse_results.txt")
    with open(results_path, "w", encoding="utf-8") as out_file:
        for idx, line in enumerate(lines, 1):
            print(f"\n  Cadena {idx}: {line!r}")
            out_file.write(f"\nCadena {idx}: {line!r}\n")

            # Tokenización
            if lexer_module:
                try:
                    tokens = tokenize_with_lexer(
                        line, lexer_module, args.entrypoint, ignore_set
                    )
                    token_types = [t[0] for t in tokens]
                except Exception as e:
                    print(f"    ✗ Error léxico: {e}")
                    out_file.write(f"  ERROR LÉXICO: {e}\n")
                    continue
            else:
                # Modo standalone: la línea ya contiene nombres de tokens separados por espacio
                token_types = tokenize_simple(line, ignore_set=ignore_set)

            print(f"  Tokens: {token_types}")
            result = evaluator.evaluate(token_types, trace=True)
            print_parse_trace(result)

            verdict = str(result)
            print(f"  {verdict}")
            out_file.write(f"  Tokens: {token_types}\n")
            out_file.write(f"  Resultado: {verdict}\n")

    print(f"\n  ✓ Resultados guardados en: {results_path}")
    _sep()
    print("\nYAPar finalizado exitosamente.")


if __name__ == "__main__":
    main()
