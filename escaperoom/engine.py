import json
import os
from typing import TextIO

from escaperoom.rooms.base import GameState, Room
from escaperoom.rooms.vault import VaultRoom
from escaperoom.rooms.soc import SOCRoom
from escaperoom.rooms.dns import DNSRoom
from escaperoom.rooms.malware import MalwareRoom


_HELP = (
    "Commands: look, move <room>, inspect <item>, use <item>, "
    "inventory, hint, save <file>, load <file>, quit"
)

_DEFAULT_ORDER = ["KEYPAD", "DNS", "SAFE", "PID"]

# Used when a room does not carry its own script. A room's hints tuple wins.
_RADIO: dict[str, tuple[str, str, str]] = {
    "soc": (
        "The item on this desk is auth.log.",
        "Keep a line only when it is a full SSH password record. Count every line you skip.",
        "The keypad is the busiest address's last octet, then the failure count of its /24.",
    ),
    "dns": (
        "The item in this closet is dns.cfg.",
        "token_tag names the real hint. Lines that start with # are not records.",
        "Reverse the declared encoding. For rot13+b64 that is ROT13, then Base64, then UTF-8. "
        "The token is the last word, without the final period.",
    ),
}

_GENERIC_RADIO = (
    "Look around. The room description names what matters.",
    "Inspect the item in this room.",
    "Derive the token from the evidence and keep it.",
)

_INTRO_RADIO = (
    "The doors are labeled. move <room> to start a desk.",
    "Each open room has one evidence file. inspect it by name.",
    "Collected tokens appear on the incident board. The final gate wants all four.",
)

class SaveError(Exception):
    pass


def run(start: str | None, data: str | None, transcript: str | None) -> None:
    start = start or "intro"
    data = data or "data"
    transcript = transcript or "run.txt"

    state = GameState(current_room=start)
    rooms = make_rooms(data)
    if state.current_room not in rooms:
        raise SystemExit(f"Unknown room: {state.current_room}")

    _, token_order = read_gate_meta(data)
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
                echo(log, _HELP)
            elif cmd == "inspect":
                for text in rooms[state.current_room].inspect(state, arg):
                    echo(log, text)
            elif cmd == "use":
                for text in rooms[state.current_room].use(state, arg):
                    echo(log, text)
            elif cmd == "look":
                show_room(log, state, rooms, token_order)
            elif cmd == "move":
                dest = arg.lower()
                if not dest:
                    echo(log, "Move where?")
                elif dest in rooms:
                    state.current_room = dest
                    show_room(log, state, rooms, token_order)
                else:
                    echo(log, f"No door '{dest}'.")
            elif cmd == "inventory":
                held = ", ".join(sorted(state.inventory)) or "nothing"
                echo(log, f"You currently hold: {held}")
            elif cmd == "hint":
                for text in next_hint(state, state.current_room, rooms[state.current_room]):
                    echo(log, text)
            elif cmd == "save":
                try:
                    save_progress(arg, state)
                except SaveError as err:
                    echo(log, f"[Game] {err}")
                except OSError as err:
                    echo(log, f"[Game] Could not save {arg}: {err.strerror or err}.")
                else:
                    echo(log, "[Game] Progress saved.")
            elif cmd == "load":
                try:
                    state = load_progress(arg, rooms)
                except SaveError as err:
                    echo(log, f"[Game] {err}")
                except OSError as err:
                    echo(log, f"[Game] Could not load {arg}: {err.strerror or err}.")
                else:
                    echo(log, "[Game] Progress loaded.")
                    show_room(log, state, rooms, token_order)
            else:
                echo(log, "This command does not exist")


def make_rooms(data: str) -> dict[str, Room]:
    return {
        "intro": Room(
            "intro",
            "You are in the Intro Lobby.\n"
            "A terminal blinks in the corner. Doors lead to: soc, dns, vault, malware, final.",
            hints=_INTRO_RADIO,
        ),
        "soc": SOCRoom(data),
        "dns": DNSRoom(data),
        "vault": VaultRoom(data),
        "malware": MalwareRoom(data),
        }


def read_gate_meta(data: str) -> tuple[str, list[str]]:
    group_id = ""
    order = list(_DEFAULT_ORDER)
    path = os.path.join(data, "final_gate.txt")
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return group_id, order

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key == "group_id":
            group_id = value
        elif key == "token_order":
            parsed = [part.strip() for part in value.split(",") if part.strip()]
            if parsed:
                order = parsed
    return group_id, order


def incident_lines(state: GameState, order: list[str]) -> list[str]:
    lines = ["INCIDENT BOARD"]
    for name in order:
        if name in state.tokens:
            lines.append(f"[x] {name:<7} {state.tokens[name]}")
        else:
            lines.append(f"[ ] {name:<7} sealed")
    return lines


def radio_script(room_key: str, room: Room) -> tuple[str, str, str]:
    if room.hints is not None:
        return room.hints
    return _RADIO.get(room_key, _GENERIC_RADIO)


def next_hint(state: GameState, room_key: str, room: Room) -> list[str]:
    script = radio_script(room_key, room)
    level = state.hint_counts.get(room_key, 0)
    if level >= len(script):
        return ["[Radio] The channel is quiet. You already have the last dispatch."]
    state.hint_counts[room_key] = level + 1
    return [f"[Radio] Dispatch {level + 1}/{len(script)}.", script[level]]


def save_progress(path: str, state: GameState) -> None:
    if not path:
        raise SaveError("Save where? Try save <file>.")
    payload = {
        "current_room": state.current_room,
        "inventory": sorted(state.inventory),
        "tokens": dict(sorted(state.tokens.items())),
        "hints": dict(sorted(state.hint_counts.items())),
    }
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def load_progress(path: str, rooms: dict[str, Room]) -> GameState:
    if not path:
        raise SaveError("Load what? Try load <file>.")
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as err:
        raise SaveError(f"Save file is not valid JSON: {err.msg}.") from err
    return state_from_payload(payload, rooms)


def state_from_payload(payload: object, rooms: dict[str, Room]) -> GameState:
    if not isinstance(payload, dict):
        raise SaveError("Save file must be a JSON object.")

    room = payload.get("current_room", "intro")
    if not isinstance(room, str) or room not in rooms:
        label = room if isinstance(room, str) else "unknown"
        raise SaveError(f"Save file is for an unknown room: {label}.")

    inventory = payload.get("inventory", [])
    tokens = payload.get("tokens", {})
    hints = payload.get("hints", {})
    if not isinstance(inventory, list) or not all(isinstance(item, str) for item in inventory):
        raise SaveError("Save file inventory is malformed.")
    if not _is_str_dict(tokens):
        raise SaveError("Save file tokens are malformed.")
    if not _is_hint_map(hints):
        raise SaveError("Save file hints are malformed.")

    held = set(inventory)
    held.update(tokens)
    return GameState(
        current_room=room,
        inventory=held,
        tokens=dict(tokens),
        hint_counts=dict(hints),
    )


def show_room(
    log: TextIO,
    state: GameState,
    rooms: dict[str, Room],
    token_order: list[str],
) -> None:
    echo(log, rooms[state.current_room].description)
    if state.current_room != "intro":
        return
    echo(log, "")
    for line in incident_lines(state, token_order):
        echo(log, line)


def echo(log: TextIO, text: str = "") -> None:
    print(text)
    print(text, file=log, flush=True)


def _is_str_dict(value: object) -> bool:
    return (
        isinstance(value, dict)
        and all(isinstance(key, str) and isinstance(item, str) for key, item in value.items())
    )


def _is_hint_map(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    for key, item in value.items():
        if not isinstance(key, str) or isinstance(item, bool) or not isinstance(item, int):
            return False
        if item < 0:
            return False
    return True
