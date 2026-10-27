import os
import tempfile
import unittest

from escaperoom.rooms.base import GameState, Room
from escaperoom.rooms.vault import SafeHit, VaultRoom, VaultScanError, scan_dump

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "data", "vault_dump.txt")


class ScanDumpTests(unittest.TestCase):
    def test_tight_candidate(self) -> None:
        hit = scan_dump(["SAFE{1-2-3}\n"])
        self.assertEqual(hit, SafeHit("SAFE{1-2-3}", 1, 2, 3))
        self.assertEqual(hit.token, "1-2-3")

    def test_spacing_is_preserved(self) -> None:
        hit = scan_dump(["SAFE { 9-7 - 16 }\n"])
        self.assertEqual(hit.match, "SAFE { 9-7 - 16 }")
        self.assertEqual(hit.token, "9-7-16")

    def test_nbsp_around_braces(self) -> None:
        line = "SAFE{\u00a06 - 20 - 26\u00a0}"
        hit = scan_dump([line])
        self.assertEqual(hit.match, line)
        self.assertEqual(hit.token, "6-20-26")

    def test_trailing_junk_loses_to_later_valid_span(self) -> None:
        hit = scan_dump([
            "SAFE{5-6-12} maybe\n",
            "noise SAFE { 1 - 2 - 3 } tail\n",
        ])
        self.assertEqual(hit.match, "SAFE { 1 - 2 - 3 }")
        self.assertEqual(hit.token, "1-2-3")

    def test_failed_checksum_is_ignored(self) -> None:
        hit = scan_dump([
            "SAFE { 14 - 5 - 35 }\n",
            "SAFE{2-2-4}\n",
        ])
        self.assertEqual(hit.token, "2-2-4")
        self.assertEqual(hit.match, "SAFE{2-2-4}")

    def test_prose_and_broken_line_are_not_candidates(self) -> None:
        with self.assertRaises(VaultScanError):
            scan_dump([
                "Telemetry stream initiated.\n",
                "SAFE markers may contain spaces.\n",
                "RANDOM DATA BLOCK 0x3f\n",
                "partialSAFE{3-4-}garbage\n",
                "partialSAFE{1-2-3}\n",
            ])

    def test_glued_prefix_does_not_hide_a_real_code(self) -> None:
        hit = scan_dump(["partialSAFE{1-2-3} SAFE{4-5-9}\n"])
        self.assertEqual(hit.match, "SAFE{4-5-9}")

    def test_two_valid_codes_on_one_line(self) -> None:
        with self.assertRaises(VaultScanError):
            scan_dump(["SAFE{1-1-2} SAFE{2-2-4}\n"])

    def test_two_valid_lines(self) -> None:
        with self.assertRaises(VaultScanError):
            scan_dump(["SAFE{1-1-2}\n", "SAFE{3-3-6}\n"])

    def test_no_valid_code(self) -> None:
        with self.assertRaises(VaultScanError):
            scan_dump(["SAFE{1-1-3}\n", "\n"])

    def test_negatives_and_plus_signs_are_rejected(self) -> None:
        with self.assertRaises(VaultScanError):
            scan_dump(["SAFE{-1-2-1}\n", "SAFE{+1-2-3}\n"])

    def test_leading_zeros_use_integer_values(self) -> None:
        hit = scan_dump(["SAFE{01-02-3}\n"])
        self.assertEqual(hit.match, "SAFE{01-02-3}")
        self.assertEqual(hit.token, "1-2-3")

    def test_group_pack(self) -> None:
        with open(PACK, encoding="utf-8") as handle:
            hit = scan_dump(handle)
        self.assertEqual(hit.token, "9-7-16")
        self.assertEqual(hit.match, "SAFE { 9-7 - 16 }")
        self.assertEqual(hit.a + hit.b, hit.c)


class VaultRoomTests(unittest.TestCase):
    def test_wrong_item(self) -> None:
        room = VaultRoom("data")
        state = GameState()
        self.assertEqual(
            room.inspect(state, "auth.log"),
            ["You don't see 'auth.log' here."],
        )
        self.assertEqual(state.tokens, {})

    def test_missing_file(self) -> None:
        room = VaultRoom(os.path.join(tempfile.gettempdir(), "no-such-vault-dir"))
        state = GameState()
        lines = room.inspect(state, "vault_dump.txt")
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("Cannot read "))
        self.assertNotIn("SAFE", state.tokens)

    def test_inspect_pack_sets_token_once(self) -> None:
        room = VaultRoom(os.path.join(ROOT, "data"))
        state = GameState(current_room="vault")
        lines = room.inspect(state, "vault_dump.txt")
        self.assertEqual(lines, [
            "[Room Vault] Scanning dump...",
            "Found candidate: SAFE { 9-7 - 16 }",
            "Checksum: 9+7=16 (OK)",
            "TOKEN[SAFE]=9-7-16",
            'EVIDENCE[SAFE].MATCH="SAFE { 9-7 - 16 }"',
            "EVIDENCE[SAFE].CHECK=9+7=16",
        ])
        self.assertEqual(state.tokens["SAFE"], "9-7-16")
        self.assertEqual(state.inventory, {"SAFE"})
        self.assertEqual(room.inspect(state, "vault_dump.txt"), ["The vault is already open."])
        self.assertEqual(state.tokens["SAFE"], "9-7-16")

    def test_bad_dump_does_not_set_token(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "vault_dump.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("SAFE{1-1-9}\nSAFE{2-2-9}\n")
            state = GameState()
            lines = VaultRoom(folder).inspect(state, "vault_dump.txt")
        self.assertEqual(lines[0], "[Room Vault] Scanning dump...")
        self.assertIn("No valid SAFE code", lines[1])
        self.assertEqual(state.tokens, {})
        self.assertEqual(state.inventory, set())

if __name__ == "__main__":
    unittest.main()
