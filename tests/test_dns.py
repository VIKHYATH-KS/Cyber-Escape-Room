import base64
import codecs
import os
import tempfile
import unittest

from escaperoom.rooms.base import GameState
from escaperoom.rooms.dns import (
    DNSConfigError,
    DNSRoom,
    decode_dns,
    decode_value,
    parse_config,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, "data")


def encode_rot13_b64(text: str) -> str:
    """Encode test text the same way as the ROT13+Base64 records."""
    base64_text = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return codecs.encode(base64_text, "rot_13")


class ParseConfigTests(unittest.TestCase):
    # Tests for reading key=value records.
    def test_parses_records_and_ignores_comments_and_blank_lines(self) -> None:
        values = parse_config([
            "# DNS settings\n",
            "\n",
            " env = lab-segment \n",
            "hint1 = b64:YWJj\n",
        ])
        self.assertEqual(values, {"env": "lab-segment", "hint1": "b64:YWJj"})

    def test_line_without_equals_is_rejected(self) -> None:
        with self.assertRaisesRegex(DNSConfigError, "Line 2 is not a key=value"):
            parse_config(["# comment\n", "invalid record\n"])

    def test_empty_key_is_rejected(self) -> None:
        with self.assertRaisesRegex(DNSConfigError, "empty key"):
            parse_config([" = value\n"])


class DecodeValueTests(unittest.TestCase):
    # Tests for decoding the supported value formats.
    def test_decodes_base64_utf8_text(self) -> None:
        payload = base64.b64encode("hello café".encode("utf-8")).decode("ascii")
        self.assertEqual(decode_value(f"b64:{payload}"), ("b64", "hello café"))

    def test_decodes_rot13_then_base64_in_reverse_order(self) -> None:
        # ROT13 is undone before the Base64 text is decoded.
        payload = encode_rot13_b64("The next hint is answer.")
        self.assertEqual(
            decode_value(f"rot13+b64:{payload}"),
            ("rot13+b64", "The next hint is answer."),
        )

    def test_missing_prefix_is_rejected(self) -> None:
        with self.assertRaisesRegex(DNSConfigError, "missing its encoding prefix"):
            decode_value("YWJj")

    def test_unsupported_encoding_is_rejected(self) -> None:
        # An unknown prefix should name the unsupported encoding.
        with self.assertRaisesRegex(DNSConfigError, "Unsupported encoding: hex"):
            decode_value("hex:616263")

    def test_invalid_base64_is_rejected(self) -> None:
        with self.assertRaisesRegex(DNSConfigError, "not valid Base64 or UTF-8"):
            decode_value("b64:%%%")


class DecodeDNSTests(unittest.TestCase):
    # Tests for selecting and reading the hint named by token_tag.
    def test_uses_token_tag_to_select_and_decode_the_hint(self) -> None:
        # token_tag decodes to 2, which selects hint2.
        selected_hint = base64.b64encode(b"2").decode("ascii")
        hint_payload = encode_rot13_b64("Follow the trail to answer.")
        result = decode_dns([
            f"token_tag=b64:{selected_hint}\n",
            f"hint2=rot13+b64:{hint_payload}\n",
            "hint1=b64:unused\n",
        ])
        self.assertEqual(
            result,
            ("hint2", "rot13+b64", "Follow the trail to answer.", "answer"),
        )

    def test_missing_token_tag_is_rejected(self) -> None:
        with self.assertRaisesRegex(DNSConfigError, "Missing token_tag"):
            decode_dns(["hint1=b64:YWJj\n"])

    def test_non_numeric_token_tag_is_rejected(self) -> None:
        token_tag = base64.b64encode(b"two").decode("ascii")
        with self.assertRaisesRegex(DNSConfigError, "hint number"):
            decode_dns([f"token_tag=b64:{token_tag}\n"])

    def test_selected_hint_must_exist(self) -> None:
        token_tag = base64.b64encode(b"2").decode("ascii")
        with self.assertRaisesRegex(DNSConfigError, "Selected record hint2 is missing"):
            decode_dns([f"token_tag=b64:{token_tag}\n"])

    def test_selected_hint_must_contain_a_token(self) -> None:
        empty_hint = base64.b64encode(b"   ").decode("ascii")
        with self.assertRaisesRegex(DNSConfigError, "does not contain a token"):
            decode_dns(["token_tag=b64:MQ==\n", f"hint1=b64:{empty_hint}\n"])


class DNSRoomTests(unittest.TestCase):
    # Tests for inspecting dns.cfg in the DNS room.
    def test_inspecting_config_sets_token_and_returns_evidence(self) -> None:
        # Use a small config with a known token.
        with tempfile.TemporaryDirectory() as folder:
            payload = base64.b64encode(
                "The signal points to answer.".encode("utf-8")
            ).decode("ascii")
            with open(os.path.join(folder, "dns.cfg"), "w", encoding="utf-8") as handle:
                handle.write(
                    "token_tag=b64:MQ==\n"
                    f"hint1=b64:{payload}\n"
                )
            state = GameState()
            lines = DNSRoom(folder).inspect(state, "dns.cfg")

        self.assertEqual(state.tokens["DNS"], "answer")
        self.assertIn("DNS", state.inventory)
        self.assertIn("TOKEN[DNS]=answer", lines)
        self.assertIn("EVIDENCE[DNS].KEY=hint1", lines)
        self.assertIn("EVIDENCE[DNS].ENCODING=b64", lines)

    def test_project_pack_decodes_to_beacon(self) -> None:
        # Check the hint currently stored in the project data.
        with open(os.path.join(PACK, "dns.cfg"), encoding="utf-8") as handle:
            key, _encoding, _sentence, token = decode_dns(handle.readlines())
        self.assertEqual(key, "hint4")
        self.assertEqual(token, "beacon")

    def test_wrong_item_does_not_change_state(self) -> None:
        state = GameState()
        lines = DNSRoom(PACK).inspect(state, "other.cfg")
        self.assertEqual(lines, ["You don't see 'other.cfg' here."])
        self.assertEqual(state.tokens, {})

    def test_missing_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            lines = DNSRoom(folder).inspect(GameState(), "dns.cfg")
        self.assertEqual(lines, [f"Cannot read {os.path.join(folder, 'dns.cfg')}."])

    def test_invalid_config_is_reported_without_setting_token(self) -> None:
        # Invalid config should not add a DNS token.
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "dns.cfg"), "w", encoding="utf-8") as handle:
                handle.write("token_tag=b64:%%%\n")
            state = GameState()
            lines = DNSRoom(folder).inspect(state, "dns.cfg")
        self.assertEqual(lines[0], "[Room DNS] Decoding hints...")
        self.assertNotIn("DNS", state.tokens)
        self.assertNotIn("DNS", state.inventory)

    def test_decoded_hint_is_not_processed_twice(self) -> None:
        state = GameState(tokens={"DNS": "answer"})
        lines = DNSRoom(PACK).inspect(state, "dns.cfg")
        self.assertEqual(lines, ["The DNS hint has already been decoded."])


if __name__ == "__main__":
    unittest.main()
