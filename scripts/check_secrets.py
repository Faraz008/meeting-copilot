import re
import subprocess
import sys

PATTERNS = [
    r"gsk_[A-Za-z0-9]{20,}",
    r"AIza[0-9A-Za-z_\-]{30,}",
    r"sk-or-[A-Za-z0-9\-_]{20,}",
    r"(?:ntn|secret)_[A-Za-z0-9]{30,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]
files = subprocess.run(
    ["git", "ls-files"],
    capture_output=True,
    text=True,
    check=True,
).stdout.split("\n")
bad = []
for f in filter(None, files):
    if f.endswith(".env.example") or f.startswith("tests/replay_cache/"):
        continue
    try:
        text = open(f, encoding="utf-8", errors="ignore").read()
    except OSError:
        continue
    bad += [f"{f}: matches {p}" for p in PATTERNS if re.search(p, text)]
if bad:
    print("\n".join(bad))
    sys.exit(1)
