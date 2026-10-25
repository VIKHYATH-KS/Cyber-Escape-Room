"""Fixed game text and default configuration."""

HELP = (
    "Commands: look, move <room>, inspect <item>, use <item>, "
    "inventory, hint, save <file>, load <file>, quit"
)

DEFAULT_ORDER = ["KEYPAD", "DNS", "SAFE", "PID"]

RADIO: dict[str, tuple[str, str, str]] = {
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
    "final": (
        "The console uses final_gate.txt.",
        "Collect every token shown on the incident board first.",
        "The file defines the group, token order, and signing key.",
    ),
}

GENERIC_RADIO = (
    "Look around. The room description names what matters.",
    "Inspect the item in this room.",
    "Derive the token from the evidence and keep it.",
)

INTRO_RADIO = (
    "The doors are labeled. move <room> to start a desk.",
    "Each open room has one evidence file. inspect it by name.",
    "Collected tokens appear on the incident board. The final gate wants all four.",
)
