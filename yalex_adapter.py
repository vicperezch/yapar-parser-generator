"""
Módulo 1 (adaptador) – Integración con YALex

Este módulo actúa como puente entre el proyecto YALex existente y YAPar.
Tiene tres modos de operación:

  Modo A (integración automática):
    Invoca YALex programáticamente desde su carpeta hermana para generar
    el lexer .py a partir del archivo .yal, y luego lo carga.

  Modo B (integración manual):
    Carga un lexer .py ya generado previamente por YALex.

  Modo C (standalone):
    Si YALex no está disponible, el evaluador usa los tokens como strings
    directamente (las cadenas ya contienen nombres de tokens separados por espacio).

Funciones principales:
  invoke_yalex(yal_file, output_py, yalex_dir) → str | None
  load_generated_lexer(lexer_path) → module | None
  tokenize_with_lexer(text, lexer_module, entrypoint, ignore_set) → list[tuple]
  tokenize_simple(text, separator, ignore_set) → list[str]
"""

from __future__ import annotations
import sys
import os
import subprocess
import importlib.util
from typing import Optional


# ---------------------------------------------------------------------------
# Invocación automática de YALex
# ---------------------------------------------------------------------------

def invoke_yalex(
    yal_file: str,
    output_py: str,
    yalex_dir: str | None = None,
) -> str | None:
    """
    Invoca YALex programáticamente para generar un lexer .py a partir de un .yal.

    Busca el proyecto YALex en:
      1. El directorio pasado como `yalex_dir`
      2. La carpeta hermana `../lexical-analyzer-and-parser/`
      3. Variable de entorno YALEX_DIR

    Retorna la ruta al lexer .py generado, o None si falla.
    """
    # Resolver directorio de YALex
    if yalex_dir is None:
        # Intenta la carpeta hermana estándar
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidate = os.path.join(base, "lexical-analyzer-and-parser")
        if os.path.isdir(candidate):
            yalex_dir = candidate
        elif "YALEX_DIR" in os.environ:
            yalex_dir = os.environ["YALEX_DIR"]
        else:
            print(
                "  [YALex Adapter] No se encontró el proyecto YALex. "
                "Pasa --lexer-py con el lexer ya generado o define YALEX_DIR."
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
            print(f"  [YALex Adapter] YALex terminó con error:")
            print(result.stderr or result.stdout)
            return None
        print(f"  [YALex Adapter] Lexer generado en: {output_py}")
        return output_py
    except subprocess.TimeoutExpired:
        print("  [YALex Adapter] Timeout al ejecutar YALex.")
        return None
    except Exception as e:
        print(f"  [YALex Adapter] Error al invocar YALex: {e}")
        return None


# ---------------------------------------------------------------------------
# Tabla de tokens desde un lexer generado
# ---------------------------------------------------------------------------

def load_generated_lexer(lexer_path: str):
    """
    Carga dinámicamente el lexer generado por YALex (.py).

    Retorna el módulo cargado o None si no existe / falla.
    """
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


def tokenize_with_lexer(
    text: str,
    lexer_module,
    entrypoint: str = "token",
    ignore_set: frozenset[str] | None = None,
) -> list[tuple[str, str]]:
    """
    Tokeniza una cadena usando el lexer generado.

    Retorna lista de tuplas (tipo_token, lexema).
    """
    ignore_set = ignore_set or frozenset()
    lexer_instance = lexer_module.Lexer(text=text)
    fn = getattr(lexer_instance, entrypoint, None)
    if fn is None:
        raise RuntimeError(
            f"El lexer generado no tiene el método '{entrypoint}'. "
            f"Verifica el archivo .yal."
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


def tokenize_simple(
    text: str,
    separator: str = " ",
    ignore_set: frozenset[str] | None = None,
) -> list[str]:
    """
    Tokenización simple por separador (modo standalone).

    Retorna lista de strings (tipos de token directamente).
    Útil cuando el archivo de cadenas ya contiene los nombres de tokens
    separados por espacio.
    """
    ignore_set = ignore_set or frozenset()
    return [t for t in text.strip().split(separator) if t and t not in ignore_set]
