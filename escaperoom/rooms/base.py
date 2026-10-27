from dataclasses import dataclass, field

@dataclass
class GameState:
    current_room: str = "lobby"
    inventory: set[str] = field(default_factory=set)
    tokens: dict[str, str] = field(default_factory=dict)
    hint_counts: dict[str, int] = field(default_factory=dict)

class Room:
    def __init__(
        self,
        name: str,
        description: str,
        hints: tuple[str, str, str] | None = None,
    ):
        self.name = name
        self.description = description
        self.hints = hints

    def inspect(self, _state: GameState, item: str) -> list[str]:
        return [f"You don't see '{item}' here."]

    def use(self, state: GameState, item: str) -> list[str]:
        if not item:
            return ["No item to use"]
        if item in state.inventory or item in state.tokens:
            return [f"You have {item}."]
        return [f"You can't use '{item}' here."]