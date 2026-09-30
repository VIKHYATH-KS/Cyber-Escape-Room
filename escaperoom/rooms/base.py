from dataclasses import dataclass, field

@dataclass
class GameState:
    current_room: str = "intro"
    inventory: set[str] = field(default_factory=set)
    tokens: dict[str, str] = field(default_factory=dict)

class Room:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def solve(self, state: GameState) -> None:
        raise NotImplementedError