
from escaperoom.rooms.base import GameState,Room


def run(start: str, data: str, transcript: str) -> None:
    start = start or "intro"
    transcript = transcript or "run.txt"

    state = GameState(current_room=start)
    rooms = make_rooms()
    if state.current_room not in rooms:
        raise SystemExit(f"Unknown room: {state.current_room}")

    with open(transcript, "w", encoding="utf-8") as log:
        echo(log, "[Game] Cyber Escape Room has started. You can type 'help' for commands.")
        while True:
            line = input("> ").strip()
            print(f"> {line}", file=log, flush=True)
            if not line:
                continue

            parts = line.split()
            cmd, arg = parts[0].lower(), " ".join(parts[1:])
            if cmd == "quit":
                echo(log, f"[Game] Transcript written to {transcript}")
                break

            elif cmd == "help":
                echo(log, "Commands: look, move <room>, inventory, quit")
            elif cmd == "look":
                echo(log, rooms[state.current_room].description)
            elif cmd == "move":
                dest = arg.lower()
                if dest in rooms:
                    state.current_room = dest
                    echo(log, rooms[dest].description)
                else:
                    echo(log, f"No door '{dest}'.")
            elif cmd == "inventory":

                held = ", ".join(sorted(state.inventory)) or "nothing"
                echo(log, f"You currently hold: {held}")
            else:
                echo(log, "This command does not exist")

def make_rooms() -> dict[str, Room]:
    return {
        "intro": Room("intro",
            "You are in the Intro Lobby.\n"
            "A terminal blinks in the corner. Doors lead to: soc, dns, vault, malvare, final.")
        }

def echo(log, text: str = "") -> None:
    print(text)
    print(text, file=log, flush=True)

