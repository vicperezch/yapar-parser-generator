from __future__ import annotations
from dataclasses import dataclass, field
from slr.slr_table import SLRTable
from parsing.yalp_parser import Grammar
from grammar.first_follow import EOF_MARKER


# Guarda el estado de un paso del proceso de parseo.
@dataclass
class ParseStep:
    step: int
    stack: list
    remaining: list[str]
    action: str


# Almacena el resultado completo de una evaluación.
@dataclass
class ParseResult:
    accepted: bool
    message: str
    steps: list[ParseStep] = field(default_factory=list)
    error_token: str | None = None
    error_state: int | None = None

    def __str__(self) -> str:
        status = "ACCEPTED" if self.accepted else f"SYNTAX ERROR"
        return f"{status} — {self.message}"


# Evalúa secuencias de tokens usando una tabla SLR(1).
class StringEvaluator:

    def __init__(self, table: SLRTable, grammar: Grammar):
        self.table = table
        self.grammar = grammar

    # Ejecuta el algoritmo de parseo sobre una secuencia de tokens.
    def evaluate(
        self,
        tokens: list,
        ignored: frozenset[str] | None = None,
        trace: bool = True,
    ) -> ParseResult:
        ignored = ignored or frozenset()

        # Extrae únicamente los tipos de token.
        token_types: list[str] = []
        for tok in tokens:
            if isinstance(tok, tuple):
                token_types.append(tok[0])
            else:
                token_types.append(str(tok))

        # Elimina tokens ignorados y agrega EOF.
        token_types = [t for t in token_types if t not in ignored]
        token_types.append(EOF_MARKER)

        stack: list[int] = [0]
        steps: list[ParseStep] = []
        pos = 0
        step_num = 0

        while True:
            state = stack[-1]
            lookahead = token_types[pos] if pos < len(token_types) else EOF_MARKER
            action = self.table.get_action(state, lookahead)

            # Guarda el estado actual del análisis.
            if trace:
                steps.append(ParseStep(
                    step=step_num,
                    stack=list(stack),
                    remaining=list(token_types[pos:]),
                    action=action or "error",
                ))
            step_num += 1

            if action is None:
                # Reporta un error sintáctico.
                msg = (
                    f"Token inesperado '{lookahead}' en estado {state}. "
                    f"Tokens válidos: {sorted(self.table.action.get(state, {}).keys())}"
                )
                return ParseResult(
                    accepted=False,
                    message=msg,
                    steps=steps,
                    error_token=lookahead,
                    error_state=state,
                )

            if action == "accept":
                return ParseResult(
                    accepted=True,
                    message="Cadena aceptada exitosamente.",
                    steps=steps,
                )

            if action.startswith("shift"):
                next_state = int(action.split()[1])
                stack.append(next_state)
                pos += 1

            elif action.startswith("reduce"):
                prod_idx = int(action.split()[1])
                prod = self.grammar.productions[prod_idx]

                # Retira los estados correspondientes a la producción reducida.
                for _ in prod.rhs:
                    stack.pop()

                top_state = stack[-1]
                lhs = prod.lhs
                goto_state = self.table.get_goto(top_state, lhs)

                if goto_state is None:
                    msg = (
                        f"Error en GOTO[{top_state}][{lhs}] durante reduce "
                        f"por {prod}."
                    )
                    return ParseResult(
                        accepted=False,
                        message=msg,
                        steps=steps,
                        error_state=top_state,
                    )

                stack.append(goto_state)

                # Actualiza el paso con la producción aplicada.
                if trace:
                    steps[-1] = ParseStep(
                        step=steps[-1].step,
                        stack=steps[-1].stack,
                        remaining=steps[-1].remaining,
                        action=f"reduce {prod}",
                    )
            else:
                return ParseResult(
                    accepted=False,
                    message=f"Acción desconocida: {action!r}",
                    steps=steps,
                )

            # Evita ciclos infinitos durante el análisis.
            if step_num > 10_000:
                return ParseResult(
                    accepted=False,
                    message="Límite de pasos excedido (posible ciclo).",
                    steps=steps,
                )


# Muestra el historial de pasos del parseo en formato tabular.
def print_parse_trace(result: ParseResult):
    col_step = 6
    col_stack = 25
    col_remaining = 30
    col_action = 40

    header = (
        f"{'Paso':>{col_step}} | "
        f"{'Pila':<{col_stack}} | "
        f"{'Entrada restante':<{col_remaining}} | "
        f"{'Acción':<{col_action}}"
    )
    print(header)
    print("-" * len(header))

    for s in result.steps:
        stack_str = str(s.stack)[-col_stack:]
        remaining_str = " ".join(s.remaining)
        remaining_str = remaining_str[:col_remaining]
        action_str = str(s.action)[:col_action]
        print(
            f"{s.step:>{col_step}} | "
            f"{stack_str:<{col_stack}} | "
            f"{remaining_str:<{col_remaining}} | "
            f"{action_str:<{col_action}}"
        )

    print()
    print(f"  → {result}")