"""Fixed game text and default configuration."""

HELP = (
    "Commands: look, move <room>, inspect <item>, use <item>, "
    "inventory, hint, save <file>, load <file>, quit"
)

DEFAULT_ORDER = ["KEYPAD", "DNS", "SAFE", "PID"]

RADIO: dict[str, tuple[str, str, str]] = {
    "lobby": (
        "The doors are labeled. move <room> to start a desk.",
        "Each open room has one evidence file. inspect it by name.",
        "Collected tokens appear on the incident board. The final gate wants all four.",
    ),
    "soc": (
        "The item on this desk is auth.log.",
        "Keep a line only when it is a full SSH password record. Count every line you skip.",
        "The keypad is the busiest address's last octet, then the failure count of its /24.",
    ),
    "dns": (
        "The item in this closet is dns.cfg.",
        "token_tag names the real hint; ignore comments and the other hint records.",
        "Decode the selected value using its declared encoding, then take its last word as the token.",
    ),
    "vault": (
        "The item in this corridor is vault_dump.txt.",
        "A candidate looks like SAFE{a-b-c}. Spacing and characters vary.",
        "Correct candidate is where a + b = c.",
    ),
    "malware": (
        "The process evidence is proc_tree.jsonl.",
        "Skip malformed records, then connect each PID to its PPID starting from the process with PPID 0.",
        "Follow the tree to a curl POST uploading /tmp/x.tgz or an scp sending it to a remote host. That process PID is the token.",
    ),
    "final": (
        "The console uses final_gate.txt.",
        "Collect every token shown on the incident board first.",
        "The file defines the group, token order, and signing key.",
    ),
}

# fallback for any room without custom hints (if all rooms have custom hints, this is unused)
GENERIC_RADIO = (
    "Look around. The room description names what matters.",
    "Inspect the item in this room.",
    "Derive the token from the evidence and keep it.",
)
