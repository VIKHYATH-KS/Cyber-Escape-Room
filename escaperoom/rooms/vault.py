import os
import re
from collections.abc import Iterable
from dataclasses import dataclass

from escaperoom.constants import VAULT_ITEM
from escaperoom.rooms.base import GameState, Room

_SAFE_RE = re.compile(
    r"\bSAFE\s*\{\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\}"
)


@dataclass(frozen=True)
class SafeHit:
    match: str
    a: int
    b: int
    c: int

    @property
    def token(self) -> str:
        return f"{self.a}-{self.b}-{self.c}"


class VaultScanError(Exception):
    pass


def scan_dump(lines: Iterable[str]) -> SafeHit:
    found: SafeHit | None = None
    for line in lines:
        for match in _SAFE_RE.finditer(line.rstrip("\r\n")):
            a = int(match.group(1))
            b = int(match.group(2))
            c = int(match.group(3))
            if a + b != c:
                continue
            if found is not None:
                raise VaultScanError("More than one valid SAFE code in the dump.")
            found = SafeHit(match.group(0), a, b, c)
    if found is None:
        raise VaultScanError("No valid SAFE code in the dump.")
    return found


class VaultRoom(Room):
    def __init__(self, data_dir: str):
        super().__init__(
            "vault",
            "You enter the Vault Corridor.\n"
            "A noisy dump scrolls past. Somewhere a SAFE{a-b-c} hides.\n"
            f"Items here: {VAULT_ITEM}",
        )
        self.data_dir = data_dir

    def use(self, state: GameState, item: str) -> list[str]:
        if item == VAULT_ITEM:
            if "SAFE" in state.tokens:
                return ["The vault is already open. The code is in your inventory."]
            return [f"Inspect {VAULT_ITEM}. Use only for the final gate."]
        return super().use(state, item)

    def inspect(self, state: GameState, item: str) -> list[str]:
        if item != VAULT_ITEM:
            return super().inspect(state, item)
        
        if "SAFE" in state.tokens:
            return ["The vault is already open."]

        path = os.path.join(self.data_dir, VAULT_ITEM)
        try:
            with open(path, encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError:
            return [f"Cannot read {path}."]

        try:
            hit = scan_dump(lines)
        except VaultScanError as err:
            return ["[Room Vault] Scanning dump...", str(err)]

        state.tokens["SAFE"] = hit.token
        state.inventory.add("SAFE")
        return [
            "[Room Vault] Scanning dump...",
            f"Found candidate: {hit.match}",
            f"Checksum: {hit.a}+{hit.b}={hit.c} (OK)",
            f"TOKEN[SAFE]={hit.token}",
            f'EVIDENCE[SAFE].MATCH="{hit.match}"',
            f"EVIDENCE[SAFE].CHECK={hit.a}+{hit.b}={hit.c}",
        ]
