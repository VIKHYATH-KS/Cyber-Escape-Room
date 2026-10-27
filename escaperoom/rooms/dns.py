import base64
import codecs
import os

from .base import GameState, Room

_ITEM = "dns.cfg"


class DNSConfigError(ValueError):
    """Raised when the DNS configuration cannot be decoded."""


def parse_config(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            raise DNSConfigError(f"Line {line_number} is not a key=value record.")

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            raise DNSConfigError(f"Line {line_number} has an empty key.")

        values[key] = value

    return values


def decode_value(value: str) -> tuple[str, str]:
    if ":" not in value:
        raise DNSConfigError("Encoded value is missing its encoding prefix.")

    encoding, payload = value.split(":", 1)

    try:
        if encoding == "b64":
            decoded_bytes = base64.b64decode(payload, validate=True)
        elif encoding == "rot13+b64":
            # The file was encoded as Base64 first, then ROT13.
            # Reverse that order when decoding.
            base64_text = codecs.decode(payload, "rot_13")
            decoded_bytes = base64.b64decode(base64_text, validate=True)
        else:
            raise DNSConfigError(f"Unsupported encoding: {encoding}")

        return encoding, decoded_bytes.decode("utf-8")
    except DNSConfigError:
        raise
    except (ValueError, UnicodeDecodeError) as err:
        raise DNSConfigError("Encoded value is not valid Base64 or UTF-8.") from err


def decode_dns(lines: list[str]) -> tuple[str, str, str, str]:
    values = parse_config(lines)

    if "token_tag" not in values:
        raise DNSConfigError("Missing token_tag record.")

    _, selected_hint = decode_value(values["token_tag"])
    if not selected_hint.isdecimal():
        raise DNSConfigError("token_tag must decode to a hint number.")

    key = f"hint{selected_hint}"
    if key not in values:
        raise DNSConfigError(f"Selected record {key} is missing.")

    encoding, sentence = decode_value(values[key])

    sentence_without_period = (
        sentence[:-1] if sentence.endswith(".") else sentence
    )
    words = sentence_without_period.split()
    if not words:
        raise DNSConfigError("Selected hint does not contain a token.")

    token = words[-1]
    return key, encoding, sentence, token


class DNSRoom(Room):
    def __init__(self, data_dir: str):
        super().__init__(
            "dns",
            "You enter the DNS Closet.\n"
            "The walls are covered with scribbled key=value pairs.\n"
            "Items here: dns.cfg"
        )
        self.data_dir = data_dir

    def inspect(self, state: GameState, item: str) -> list[str]: # overrides Room.inspect
        if item != _ITEM:
            return super().inspect(item) # use the base class's inspect method

        if "DNS" in state.tokens:
            return ["The DNS hint has already been decoded."]

        path = os.path.join(self.data_dir, _ITEM)

        try:
            with open(path, encoding="utf-8") as handle:
                key, encoding, sentence, token = decode_dns(handle.readlines())
        except OSError:
            return [f"Cannot read {path}."]
        except DNSConfigError as err:
            return ["[Room DNS] Decoding hints...", str(err)]

        state.tokens["DNS"] = token
        state.inventory.add("DNS")
        
        return [
       "[Room DNS] Decoding hints...",
            f'Decoded line: "{sentence}"',
            f"Token formed: {token}",
            f"TOKEN[DNS]={token}",
            f"EVIDENCE[DNS].KEY={key}",
            f"EVIDENCE[DNS].ENCODING={encoding}",
            f"EVIDENCE[DNS].DECODED_LINE={sentence}",
        ]