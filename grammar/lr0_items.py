from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class LR0Item:
    lhs: str
    rhs: tuple[str, ...]
    dot: int = 0

    @property
    def next_symbol(self) -> Optional[str]:
        if self.dot < len(self.rhs):
            return self.rhs[self.dot]
        return None

    @property
    def is_complete(self) -> bool:
        return self.dot == len(self.rhs)

    def advance(self) -> "LR0Item":
        if self.is_complete:
            raise ValueError("No se puede avanzar el punto: ítem completo.")
        return LR0Item(self.lhs, self.rhs, self.dot + 1)

    def __str__(self) -> str:
        symbols = list(self.rhs)
        symbols.insert(self.dot, "·")
        rhs_str = " ".join(symbols) if symbols else "·"
        return f"{self.lhs} → {rhs_str}"

    def __repr__(self) -> str:
        return f"LR0Item({self!s})"


@dataclass
class LR0State:
    id: int
    items: frozenset[LR0Item]

    def __hash__(self):
        return hash(self.items)

    def __eq__(self, other) -> bool:
        if not isinstance(other, LR0State):
            return False
        return self.items == other.items

    def __str__(self) -> str:
        items_str = "\n  ".join(str(i) for i in sorted(self.items, key=str))
        return f"Estado {self.id}:\n  {items_str}"

    def __repr__(self) -> str:
        return f"LR0State(id={self.id}, items={len(self.items)})"


@dataclass
class LR0Automaton:
    states: list[LR0State] = field(default_factory=list)
    transitions: dict[int, dict[str, int]] = field(default_factory=dict)
    initial_state: Optional[LR0State] = None

    def get_state(self, state_id: int) -> LR0State:
        return self.states[state_id]

    def add_transition(self, from_id: int, symbol: str, to_id: int):
        self.transitions.setdefault(from_id, {})[symbol] = to_id

    def __repr__(self) -> str:
        return (
            f"LR0Automaton("
            f"{len(self.states)} estados, "
            f"{sum(len(v) for v in self.transitions.values())} transiciones)"
        )
