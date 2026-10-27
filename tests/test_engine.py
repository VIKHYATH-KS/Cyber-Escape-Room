import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from escaperoom.engine import (
    SaveError,
    echo,
    incident_lines,
    load_progress,
    next_hint,
    read_gate_meta,
    save_progress,
)
from escaperoom.rooms.base import GameState, Room
from escaperoom.rooms.vault import VaultRoom

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "data")


class PlainTextTests(unittest.TestCase):
    def test_echo_prints_the_same_plain_text_to_screen_and_log(self) -> None:
        log = io.StringIO()
        screen = io.StringIO()
        with redirect_stdout(screen):
            echo(log, "  | BLUE TEAM |")
        self.assertEqual(screen.getvalue(), "  | BLUE TEAM |\n")
        self.assertEqual(log.getvalue(), "  | BLUE TEAM |\n")
        self.assertNotIn("\033", screen.getvalue())


class BoardAndRadioTests(unittest.TestCase):
    def test_board_follows_token_order_and_live_tokens(self) -> None:
        state = GameState(tokens={"SAFE": "9-7-16"})
        lines = incident_lines(state, ["KEYPAD", "PID", "SAFE", "DNS"])
        self.assertEqual(lines, [
            "INCIDENT BOARD",
            "[ ] KEYPAD  sealed",
            "[ ] PID     sealed",
            "[x] SAFE    9-7-16",
            "[ ] DNS     sealed",
        ])

    def test_gate_file_supplies_group_and_order(self) -> None:
        group_id, order = read_gate_meta(PACK)
        self.assertEqual(group_id, "group08")
        self.assertEqual(order, ["KEYPAD", "PID", "SAFE", "DNS"])

    def test_missing_gate_file_has_a_fallback(self) -> None:
        group_id, order = read_gate_meta(os.path.join(tempfile.gettempdir(), "no-such-pack"))
        self.assertEqual(group_id, "")
        self.assertEqual(order, ["KEYPAD", "DNS", "SAFE", "PID"])

    def test_vault_radio_stops_at_three_and_hides_the_code(self) -> None:
        room = VaultRoom(PACK)
        state = GameState(current_room="vault")
        heard = []
        for _ in range(4):
            heard.extend(next_hint(state, "vault", room))
        self.assertEqual(heard[0], "[Radio] Dispatch 1/3.")
        self.assertIn("vault_dump.txt", heard[1])
        self.assertEqual(heard[2], "[Radio] Dispatch 2/3.")
        self.assertEqual(heard[4], "[Radio] Dispatch 3/3.")
        self.assertIn("a + b = c", heard[5])
        self.assertEqual(
            heard[6],
            "[Radio] The channel is quiet. You already have the last dispatch.",
        )
        self.assertNotIn("9-7-16", "\n".join(heard))
        self.assertNotIn("TOKEN[", "\n".join(heard))

    def test_room_without_a_script_uses_the_engine_radio(self) -> None:
        room = Room("SOC Triage Desk", "A cluttered screen.")
        state = GameState()
        lines = next_hint(state, "soc", room)
        self.assertEqual(lines[0], "[Radio] Dispatch 1/3.")
        self.assertIn("auth.log", lines[1])


class SaveLoadTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        rooms = {"lobby": Room("lobby", "lobby"), "vault": VaultRoom(PACK)}
        state = GameState(
            current_room="vault",
            inventory={"SAFE", "KEYPAD"},
            tokens={"SAFE": "9-7-16", "KEYPAD": "21758"},
            hint_counts={"vault": 2},
        )
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "save1.json")
            save_progress(path, state)
            with open(path, encoding="utf-8") as handle:
                raw = handle.read()
            self.assertNotIn("hmac", raw)
            loaded = load_progress(path, rooms)
        self.assertEqual(loaded.current_room, "vault")
        self.assertEqual(loaded.tokens, {"KEYPAD": "21758", "SAFE": "9-7-16"})
        self.assertEqual(loaded.inventory, {"KEYPAD", "SAFE"})
        self.assertEqual(loaded.hint_counts, {"vault": 2})

    def test_malformed_json_does_not_build_a_state(self) -> None:
        rooms = {"lobby": Room("lobby", "lobby")}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "broken.json")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("{not json\n")
            with self.assertRaises(SaveError):
                load_progress(path, rooms)

    def test_unknown_room_is_rejected(self) -> None:
        rooms = {"lobby": Room("lobby", "lobby")}
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "save1.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"current_room": "malware", "inventory": [], "tokens": {}}, handle)
            with self.assertRaises(SaveError) as caught:
                load_progress(path, rooms)
        self.assertIn("malware", str(caught.exception))

    def test_missing_file_raises_oserror(self) -> None:
        rooms = {"lobby": Room("lobby", "lobby")}
        with self.assertRaises(OSError):
            load_progress(os.path.join(tempfile.gettempdir(), "no-such-save.json"), rooms)

    def test_empty_path_is_explicit(self) -> None:
        with self.assertRaises(SaveError):
            save_progress("", GameState())
        with self.assertRaises(SaveError):
            load_progress("", {"lobby": Room("lobby", "lobby")})


class VaultUseTests(unittest.TestCase):
    def test_use_points_at_inspect_until_the_code_is_held(self) -> None:
        room = VaultRoom(PACK)
        state = GameState()
        self.assertEqual(
            room.use(state, "vault_dump.txt"),
            ["Inspect vault_dump.txt. Use only for the final gate."],
        )
        state.tokens["SAFE"] = "9-7-16"
        state.inventory.add("SAFE")
        self.assertEqual(
            room.use(state, "vault_dump.txt"),
            ["The vault is already open. The code is in your inventory."],
        )
        self.assertEqual(
            room.use(state, "SAFE"),
            ["You have SAFE."],
        )


if __name__ == "__main__":
    unittest.main()
