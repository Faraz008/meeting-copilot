import re
from pathlib import Path

README = Path("README.md")
RESULTS = Path("docs/results_final_table.md")

readme = README.read_text(encoding="utf-8")
results = RESULTS.read_text(encoding="utf-8").strip()

pattern = r"(<!-- RESULTS:START -->).*?(<!-- RESULTS:END -->)"

if not re.search(pattern, readme, flags=re.S):
    raise SystemExit("README results markers not found.")

new = re.sub(
    pattern,
    lambda m: m.group(1) + "\n\n" + results + "\n\n" + m.group(2),
    readme,
    flags=re.S,
)

README.write_text(new, encoding="utf-8")

print("README results updated.")
