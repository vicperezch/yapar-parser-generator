from __future__ import annotations
import os
import textwrap
from grammar.lr0_items import LR0Automaton, LR0State, LR0Item


# Convierte un ítem LR(0) en una representación legible.
def _format_item(item: LR0Item) -> str:
    symbols = list(item.rhs)
    symbols.insert(item.dot, "·")
    rhs_str = " ".join(symbols) if symbols else "·"
    return f"{item.lhs} → {rhs_str}"


# Genera la etiqueta de texto para un estado del autómata.
def _node_label(state: LR0State) -> str:
    lines = [f"Estado {state.id}"]
    for item in sorted(state.items, key=lambda i: (i.lhs, str(i))):
        lines.append(_format_item(item))
    return "\n".join(lines)


# Genera una imagen PNG del autómata LR(0).
def render_automaton_png(automaton: LR0Automaton, output_path: str) -> str:
    try:
        import pydot  # type: ignore
    except ImportError:
        print("  [Visualizador] pydot no instalado — omitiendo PNG.")
        return ""

    graph = pydot.Dot(
        graph_type="digraph",
        rankdir="LR",
        fontname="Helvetica",
        bgcolor="#1e1e2e",
    )
    graph.set_node_defaults(
        shape="box",
        style="filled,rounded",
        fillcolor="#313244",
        fontcolor="#cdd6f4",
        fontname="Courier New",
        fontsize="10",
    )
    graph.set_edge_defaults(
        color="#89b4fa",
        fontcolor="#a6e3a1",
        fontname="Helvetica",
        fontsize="9",
    )

    # Agrega el punto de entrada al estado inicial.
    graph.add_node(pydot.Node("__start__", shape="point", width="0.1"))
    graph.add_edge(pydot.Edge("__start__", f"s{automaton.initial_state.id}"))

    for state in automaton.states:
        label = _node_label(state)

        # Resalta visualmente el estado inicial.
        fillcolor = "#45475a" if state.id == automaton.initial_state.id else "#313244"

        node = pydot.Node(
            f"s{state.id}",
            label=label,
            fillcolor=fillcolor,
        )
        graph.add_node(node)

    for from_id, transitions in automaton.transitions.items():
        for symbol, to_id in transitions.items():
            edge = pydot.Edge(
                f"s{from_id}",
                f"s{to_id}",
                label=f" {symbol} ",
            )
            graph.add_edge(edge)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    graph.write_png(output_path)
    return output_path