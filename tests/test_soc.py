import unittest
from pathlib import Path
import tempfile

from escaperoom.rooms.soc import SOCRoom


class SOCRoomTests(unittest.TestCase):

    def test_auth_log_result(self):
        room = SOCRoom("data")

        keypad, top24, count, top_ip, sample, malformed = room.read_auth_log("data/auth.log")

        self.assertEqual(keypad, "21758")
        self.assertEqual(top24, "198.51.100.0/24")
        self.assertEqual(top_ip, "198.51.100.217")
        self.assertEqual(count, 58)
        self.assertEqual(malformed, 3)
        self.assertIn("Failed password", sample)

    def test_malformed_entry_is_skipped(self):
        valid_line = (
            "2026-10-05T09:00:04Z lab1 sshd[3506]: "
            "Failed password for admin from 192.0.2.7 "
            "port 43983 protocol 2")

        malformed_line = (
            "2026-10-05T09:00:05Z lab1 sshd[3507]: "
            "Failed password for admin from 192.0.2.999 "
            "port 43983 protocol 2")

        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "auth.log"

            log_path.write_text( valid_line + "\n" + malformed_line + "\n", encoding="utf-8")

            room = SOCRoom(temp_dir)

            keypad, top24, count, top_ip, sample, malformed = room.read_auth_log(str(log_path))

        self.assertEqual(keypad, "71")
        self.assertEqual(top24, "192.0.2.0/24")
        self.assertEqual(top_ip, "192.0.2.7")
        self.assertEqual(count, 1)
        self.assertEqual(sample, valid_line)
        self.assertEqual(malformed, 1)


if __name__ == "__main__":
    unittest.main()