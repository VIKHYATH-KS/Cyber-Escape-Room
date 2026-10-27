import hashlib
import hmac
import os

from .base import GameState, Room

_ITEM = "final_gate.txt"


class FinalGateError(ValueError):
    """Raised when the final gate metadata is incomplete or invalid."""


def read_final_gate(path: str) -> tuple[str, list[str], bytes]:
    """Read the group, ordered token names, and UTF-8-encoded HMAC key."""
    values: dict[str, str] = {}
    with open(path, encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                raise FinalGateError(f"Line {line_number} is not a key=value record.")
            key, value = (part.strip() for part in stripped.split("=", 1))
            if key:
                values[key] = value

    group_id = values.get("group_id", "")
    order = [part.strip() for part in values.get("token_order", "").split(",") if part.strip()]
    if not group_id:
        raise FinalGateError("Missing group_id record.")
    if not order:
        raise FinalGateError("Missing token_order record.")
    try:
        key = values["hmac_key"].encode("utf-8")
    except KeyError as err:
        raise FinalGateError("Missing hmac_key record.") from err
    if not key:
        raise FinalGateError("hmac_key cannot be empty.")
    return group_id, order, key


def clearance_code(group_id: str, order: list[str], tokens: dict[str, str], key: bytes) -> str:
    """Return HMAC-SHA256 for the group and hyphen-joined ordered tokens."""
    missing = [name for name in order if name not in tokens]
    if missing:
        raise FinalGateError("Missing required tokens: " + ", ".join(missing) + ".")
    message = f"{group_id}|{'-'.join(tokens[name] for name in order)}"
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()


class FinalRoom(Room):
    def __init__(self, data_dir: str):
        super().__init__(
            "final",
            "You stand before the Final Gate. The console asks for proof.",
        )
        self.data_dir = data_dir

    def use(self, state: GameState, item: str) -> list[str]:
        if item.lower() != "gate":
            return super().use(state, item)

        path = os.path.join(self.data_dir, _ITEM)
        try:
            group_id, order, key = read_final_gate(path)
        except OSError:
            return [f"Cannot read {path}."]
        except FinalGateError as err:
            return ["[Final Gate] Verifying incident tokens...", str(err)]

        collected = [f"{name}={state.tokens[name]}" for name in order if name in state.tokens]
        result = ["Collected tokens: " + ", ".join(collected), "FINAL_GATE=PENDING"]
        missing = [name for name in order if name not in state.tokens]
        if missing:
            result.append("Missing tokens: " + ", ".join(missing))
            return result

        message = f"{group_id}|{'-'.join(state.tokens[name] for name in order)}"
        code = clearance_code(group_id, order, state.tokens, key)
        result.extend((f"MSG={message}", f"EXPECTED_HMAC={code}"))
        return result

    def inspect(self, state: GameState, item: str) -> list[str]:
        if item != _ITEM:
            return [f"You don't see '{item}' here."]
        return ["The console is ready. Use gate to assemble the proof."]
