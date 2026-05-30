from __future__ import annotations
import sys
import os
import subprocess
import importlib.util
from typing import Optional

# Genera un lexer utilizando YALex y retorna su ruta.
def invoke_yalex(
    yal_file: str,
    output_py: str,
    yalex_dir: str | None = None,
) -> str | None:

    # Obtiene la ubicación del proyecto YALex.
    if yalex_dir is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(base, "lexical-analyzer-and-parser")

        if os.path.isdir(candidate):
            yalex_dir = candidate
        elif "YALEX_DIR" in os.environ:
            yalex_dir = os.environ["YALEX_DIR"]
        else:
            print(
                "  [YALex Adapter] No se encontró el proyecto YALex. "
                "Utilice --lexer-py o defina YALEX_DIR."
            )
            return None

    yalex_main = os.path.join(yalex_dir, "main.py")

    if not os.path.exists(yalex_main):
        print(f"  [YALex Adapter] No se encontró main.py en: {yalex_dir}")
        return None

    os.makedirs(os.path.dirname(output_py) or ".", exist_ok=True)

    cmd = [sys.executable, yalex_main, yal_file, "-o", output_py]
    print(f"  [YALex Adapter] Ejecutando: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=yalex_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print("  [YALex Adapter] Error durante la ejecución de YALex:")
            print(result.stderr or result.stdout)
            return None

        print(f"  [YALex Adapter] Lexer generado en: {output_py}")
        return output_py

    except subprocess.TimeoutExpired:
        print("  [YALex Adapter] Tiempo de espera excedido.")
        return None

    except Exception as e:
        print(f"  [YALex Adapter] Error al ejecutar YALex: {e}")
        return None


# Carga dinámicamente un lexer generado por YALex.
def load_generated_lexer(lexer_path: str):

    if not os.path.exists(lexer_path):
        return None

    try:
        spec = importlib.util.spec_from_file_location("_generated_lexer", lexer_path)
        module = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(module)  # type: ignore
        return module

    except Exception as e:
        print(f"  [YALex Adapter] No se pudo cargar el lexer: {e}")
        return None


# Tokeniza una cadena utilizando un lexer generado.
def tokenize_with_lexer(
    text: str,
    lexer_module,
    entrypoint: str = "token",
    ignore_set: frozenset[str] | None = None,
) -> list[tuple[str, str]]:

    ignore_set = ignore_set or frozenset()

    lexer_instance = lexer_module.Lexer(text=text)
    fn = getattr(lexer_instance, entrypoint, None)

    if fn is None:
        raise RuntimeError(
            f"El lexer generado no tiene el método '{entrypoint}'. "
            f"Verifique el archivo .yal."
        )

    tokens: list[tuple[str, str]] = []

    while lexer_instance.pos < len(text):
        tok = fn()

        if tok is None:
            continue

        if isinstance(tok, tuple):
            tipo, lexema = tok[0], tok[1]
        else:
            tipo, lexema = str(tok), str(tok)

        if tipo not in ignore_set:
            tokens.append((tipo, lexema))

        if lexer_instance.pos >= len(text):
            break

    return tokens


# Divide una cadena en tokens usando un separador simple.
def tokenize_simple(
    text: str,
    separator: str = " ",
    ignore_set: frozenset[str] | None = None,
) -> list[str]:

    ignore_set = ignore_set or frozenset()

    return [t for t in text.strip().split(separator) if t and t not in ignore_set]