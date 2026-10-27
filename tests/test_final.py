import hashlib
import hmac
import os
import tempfile
import unittest

from escaperoom.rooms.base import GameState
from escaperoom.rooms.final import FinalGateError, FinalRoom, clearance_code, read_final_gate


class ReadFinalGateTests(unittest.TestCase):
    def write_gate(self, contents: str) -> str:
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, "final_gate.txt")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(contents)
        return path

    def test_reads_group_order_and_utf8_key_bytes(self) -> None:
        path = self.write_gate(
            "# final gate\n group_id = team-é \n"
            "token_order = A, B \n"
            "hmac_key = clé-秘密\n"
        )
        group_id, order, key = read_final_gate(path)
        self.assertEqual(group_id, "team-é")
        self.assertEqual(order, ["A", "B"])
        self.assertEqual(key, "clé-秘密".encode("utf-8"))

    def test_missing_hmac_key_is_reported(self) -> None:
        path = self.write_gate("group_id=team\ntoken_order=A\n")
        with self.assertRaisesRegex(FinalGateError, "Missing hmac_key"):
            read_final_gate(path)

    def test_empty_hmac_key_is_rejected(self) -> None:
        path = self.write_gate("group_id=team\ntoken_order=A\nhmac_key=\n")
        with self.assertRaisesRegex(FinalGateError, "cannot be empty"):
            read_final_gate(path)

    def test_missing_group_or_token_order_is_rejected(self) -> None:
        cases = (
            ("token_order=A\nhmac_key=secret\n", "Missing group_id"),
            ("group_id=team\nhmac_key=secret\n", "Missing token_order"),
        )
        for contents, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(FinalGateError, message):
                    read_final_gate(self.write_gate(contents))


class ClearanceCodeTests(unittest.TestCase):
    def test_hmac_uses_utf8_key_and_ordered_message(self) -> None:
        key = "clé-秘密".encode("utf-8")
        expected = hmac.new(
            key, "team-é|one-two".encode("utf-8"), hashlib.sha256
        ).hexdigest()
        actual = clearance_code(
            "team-é", ["A", "B"], {"A": "one", "B": "two"}, key
        )
        self.assertEqual(actual, expected)

    def test_missing_token_is_reported(self) -> None:
        with self.assertRaisesRegex(FinalGateError, "Missing required tokens: B"):
            clearance_code("team", ["A", "B"], {"A": "one"}, b"secret")

    def test_final_room_displays_message_and_expected_hmac(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "final_gate.txt"), "w", encoding="utf-8") as handle:
                handle.write("group_id=team\ntoken_order=A,B\nhmac_key=secret\n")
            lines = FinalRoom(folder).use(
                GameState(tokens={"A": "one", "B": "two"}), "gate"
            )
        expected = hmac.new(b"secret", b"team|one-two", hashlib.sha256).hexdigest()
        self.assertIn("MSG=team|one-two", lines)
        self.assertIn(f"EXPECTED_HMAC={expected}", lines)


if __name__ == "__main__":
    unittest.main()
