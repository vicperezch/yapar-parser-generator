# YAPar – Yet Another Parser Generator

> Generador de analizadores sintácticos SLR(1) y LALR(1) para el curso CC3071 – Diseño de Lenguajes de Programación  
> Universidad del Valle de Guatemala

---

## Estructura del Proyecto

```
yapar-parser-generator/
│
├── main.py
├── yalex_adapter.py               # Módulo 1 – Puente con YALex
├── requirements.txt
│
├── parsing/                       # Módulo 2 – Parser YAPar
│   ├── __init__.py
│   ├── yalp_lexer.py              #   Tokenizador de archivos .yalp
│   └── yalp_parser.py
│
├── grammar/                       # Módulo 3 – Autómatas LR(0) y LALR(1)
│   ├── __init__.py
│   ├── lr0_items.py
│   ├── lr1_items.py
│   ├── first_follow.py
│   ├── lr0_builder.py             #   CLOSURE, GOTO, construcción canónica
│   └── lalr_builder.py            #   Colección LR(1) + fusión por núcleo
│
├── slr/                           # Módulo 4 – Tabla SLR(1)
│   ├── __init__.py
│   └── slr_table.py
│
├── lalr/                          # Módulo 4b – Tabla LALR(1)
│   ├── __init__.py
│   └── lalr_table.py
│
├── visualizer/                    # Módulo 5 – Visualizador
│   ├── __init__.py
│   └── automaton_renderer.py      #   PNG (pydot)
│
├── evaluator/                     # Módulo 6 – Evaluador de cadenas
│   ├── __init__.py
│   └── string_evaluator.py
│
├── examples/
│   ├── arithmetic.yalp
│   ├── production_example.yalp
│   └── cadenas_aritmetica.txt
│
└── output/                        # Salidas generadas
    ├── lr0_automaton.png
    └── parse_results.txt
```

---

## Instalación

```bash
# Clonar el repositorio
cd yapar-parser-generator

# Instalar dependencias Python
pip install -r requirements.txt

# Instalar Graphviz en el sistema (para PNG)
# macOS:
brew install graphviz
# Ubuntu/Debian:
sudo apt-get install graphviz
```

---

## Uso

El sistema funciona de 3 maneras distintas dependiendo de cómo quieras integrar el lexer de YALex.

### Modo A: Integración Automática (Recomendado)
YAPar invocará automáticamente tu proyecto anterior para generar el lexer al vuelo y evaluará las cadenas:
```bash
python3 main.py examples/arithmetic.yalp \
    -l ../lexical-analyzer-and-parser/mi_lexer.yal \
    -i examples/cadenas_aritmetica.txt \
    -o output/
```

### Modo B: Integración Manual
Si ya generaste el archivo `.py` de tu lexer previamente en YALex, se lo pasas directamente a YAPar:
```bash
# Ejecutar YAPar con el lexer ya generado
python3 main.py examples/arithmetic.yalp \
    --lexer-py output/thelexer.py \
    -i examples/cadenas_aritmetica.txt \
    -o output/
```

### Modo C: Básico (Standalone)
Si no cuentas con YALex, puedes probar la gramática dando las cadenas ya separadas por espacios con los nombres de sus tokens (ej: `ID PLUS ID`):
```bash
python3 main.py examples/arithmetic.yalp \
    -i examples/cadenas_aritmetica.txt \
    -o output/
```

### Argumentos

| Argumento | Descripción |
|---|---|
| `grammar` | Archivo `.yalp` (requerido) |
| `-l` / `--lexer` | Archivo `.yal` de YALex (referencia) |
| `--lexer-py` | Lexer `.py` generado por YALex (activa integración real) |
| `-i` / `--input` | Archivo con cadenas a evaluar |
| `-o` / `--output` | Directorio de salida (default: `output/`) |

| `--no-png` | Omite la generación del PNG |
| `--entrypoint` | Nombre del método tokenizador del lexer (default: `token`) |
| `--method` | Método de construcción de la tabla: `slr` o `lalr` (default: `slr`) |

---

## Entradas y Salidas del Sistema

### Inputs
El sistema requiere de 3 archivos principales para funcionar en conjunto:

1. **El archivo de la Gramática (`.yalp`)**: Es como el manual de reglas de sintaxis. Define exactamente *cómo* se pueden combinar las palabras para que la oración (cadena) sea correcta.
2. **El archivo de Tokens Léxicos (`.yal`)**: Es el diccionario. Le dice al programa cómo reconocer las "letras" o "palabras" base (por ejemplo, que el símbolo `+` significa `PLUS`, o que `123` significa `ID`). *Nota: El programa invoca a YALex automáticamente en el fondo usando este archivo.*
3. **El archivo de Pruebas (`.txt`)**: Es el examen final. Contiene las oraciones que quieres evaluar. El programa las lee y, usando el diccionario (YALex) y las reglas gramaticales (YAPar), las califica como válidas o inválidas.

### Outputs
1. **La Tabla y los Cálculos en la Consola**: Imprime los conjuntos FIRST, FOLLOW y dibuja la matriz de la Tabla SLR(1) (con acciones de shift/reduce).
2. **La Traza Paso a Paso**: Imprime cómo la pila va evaluando cada cadena ingresada.
3. **El Reporte de Resultados (`output/parse_results.txt`)**: Archivo de texto limpio indicando únicamente si la cadena fue `ACCEPTED ` o detalla el `SYNTAX ERROR`.
4. **El Autómata Visual (`output/lr0_automaton.png`)**: Un grafo estático (imagen) donde cada nodo es un estado con sus ítems LR(0) y las transiciones etiquetadas.

---

## Arquitectura y Módulos

El proyecto está organizado en 6 módulos secuenciales que interactúan de la siguiente manera:

### Módulo 1 — YALex (Analizador Léxico del .yal)
- **Recibe**: archivo `.yal` con expresiones regulares y nombres de tokens.
- **Produce**: tabla de símbolos (lista de pares nombre_token, patron_regex), más el conjunto de tokens a ignorar.
- **Responsabilidades**: Tokenizar el archivo `.yal`, compilar las regex a un AFD (implementado vía el proyecto hermano `lexical-analyzer-and-parser`) y exponer una función `next_token(cadena)` (o `token()`) que usarán los módulos posteriores.

### Módulo 2 — Parser YAPar (Lector del .yalp)
- **Recibe**: archivo `.yalp` + tabla de tokens del Módulo 1.
- **Produce**: Una estructura de gramática estructurada conteniendo: `{ terminales, no_terminales, producciones, símbolo_inicial, tokens_ignorados }`.
- **Responsabilidades**: Eliminar comentarios `/* ... */`, separar la sección de tokens de la sección de producciones por `%%`, validar que los tokens coincidan con la tabla, y construir el diccionario de producciones.

### Módulo 3 — Constructor del autómata LR(0)
- **Recibe**: Gramática estructurada del Módulo 2.
- **Produce**: El autómata LR(0) como un grafo de estados: `{ estados, transiciones }`.
- **Responsabilidades**: 
  - **Augmented grammar**: Agregar `S' → S` como producción inicial.
  - **CLOSURE(I)**: Cierra sobre todos los ítems derivables.
  - **GOTO(I, X)**: Calcula el estado destino.
  - **FIRST(α)** y **FOLLOW(A)**.
  - **Construcción canónica**: Genera el conjunto de colecciones canónicas.

### Módulo 4 — Constructor de la tabla SLR(1)
- **Recibe**: Autómata LR(0) + conjuntos FOLLOW.
- **Produce**: Dos tablas: `ACTION[estado][terminal]` y `GOTO[estado][no_terminal]`.
- **Responsabilidades**: Llenar la matriz basándose en la lógica SLR(1). Detectar errores de colisión (Shift/Reduce o Reduce/Reduce).

### Módulo 4b — Constructor de la tabla LALR(1)
- **Recibe**: Gramática estructurada del Módulo 2.
- **Produce**: Las tablas `ACTION` y `GOTO`, con la misma estructura que SLR(1).
- **Responsabilidades**: Construir la colección canónica LR(1) (ítems con lookahead) y luego **fusionar los estados cuyo núcleo LR(0) coincide**, uniendo sus lookaheads. Las acciones reduce se colocan con el lookahead preciso de cada ítem (un subconjunto de FOLLOW), lo que elimina conflictos que SLR(1) no puede resolver. Se activa con `--method lalr`; el visualizador anota los lookaheads en cada ítem (`A → α·β , {a b}`).

### Módulo 5 — Visualizador del autómata
- **Recibe**: Autómata LR(0) del Módulo 3.
- **Produce**: Representación visual (`PNG`) mostrando estados como nodos y transiciones como aristas etiquetadas.
- **Herramienta**: Graphviz (`pydot`). Cada nodo lista sus ítems LR(0) internamente.

### Módulo 6 — Evaluador de cadenas
- **Recibe**: Tabla SLR(1) + función `next_token` del Módulo 1 + cadenas de entrada.
- **Produce**: `ACCEPTED` o `SYNTAX ERROR en token X (estado Y)` por cada cadena.
- **Responsabilidades**: Ejecutar el algoritmo estándar de simulación LR con pila.

---

## Formato del archivo de gramática `.yalp`

```
/* Comentario */
%token TERMINAL_1
%token TERMINAL_2 TERMINAL_3
%token WS
IGNORE WS

%%

produccion1:
    produccion1 TERMINAL_1 produccion2
    | produccion2
    ;

produccion2:
    TERMINAL_2 produccion1 TERMINAL_3
    | TERMINAL_1
    ;
```

**Reglas:**
- Los terminales se declaran en **MAYÚSCULAS** con `%token`.
- Los no-terminales se escriben en **minúsculas** en las producciones.
- `IGNORE` marca tokens que el evaluador descartará.
- `%%` separa la sección de tokens de las producciones.
- Cada producción termina con `;`.
- Las alternativas se separan con `|`.

---

## Formato del archivo de cadenas

En modo **standalone** (sin lexer YALex), cada línea contiene los nombres de tokens separados por espacio:

```
# Comentario (ignorado)
ID PLUS ID
LPAREN ID TIMES ID RPAREN
ID ID   <- error sintáctico
```

---

## Equipo

- José Gerardo Ruiz García – 23719  
- Gerardo Andre Fernandez Cruz – 23763  
- Víctor Manuel Pérez Chávez – 23731  
- Juan Diego Solís Martínez – 23720  

CC3071 – Diseño de Lenguajes de Programación  
Universidad del Valle de Guatemala, 2026
