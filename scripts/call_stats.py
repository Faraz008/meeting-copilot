import sqlite3
import statistics
import sys
from collections import Counter

db = sqlite3.connect("data/calls.sqlite")
run_like = sys.argv[1] if len(sys.argv) > 1 else "final__%"
rows = db.execute(
    "SELECT provider, purpose, outcome, attempt, latency_s, cached FROM calls WHERE run_id LIKE ?",
    (run_like,),
).fetchall()
print(f"{len(rows)} logged calls")
for prov in sorted({r[0] for r in rows}):
    rs = [r for r in rows if r[0] == prov and not r[5]]
    ok = [r for r in rs if r[2] == "ok"]
    lat = sorted(r[4] for r in ok if r[4])
    errs = Counter(r[2] for r in rs if r[2] != "ok")
    p95 = lat[int(0.95 * (len(lat) - 1))] if lat else 0
    print(
        f"{prov}: live calls {len(rs)}, ok {len(ok)}, "
        f"retried (attempt>1) {sum(r[3] > 1 for r in rs)}, "
        f"median {statistics.median(lat) if lat else 0:.1f}s, "
        f"p95 {p95:.1f}s, errors {dict(errs)}"
    )
    print(
        f"   repairs: {sum(r[1] == 'repair' for r in rs)},"
        f"  by purpose: {dict(Counter(r[1] for r in rs))}"
    )
