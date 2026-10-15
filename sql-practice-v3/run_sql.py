"""Run SQL against practice.db and print the results as a table.
Standard library only.

Usage:
  python run_sql.py "SELECT * FROM dim_department"
  python run_sql.py my_answers.sql          (runs every statement in the file)
"""
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).with_name("practice.db")
MAX_ROWS = 25

# Some answers contain characters like "–"; this keeps a Windows terminal from crashing on them.
try:
    sys.stdout.reconfigure(errors="replace")
except AttributeError:
    pass


def show(cur):
    if cur.description is None:
        return
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    widths = [max(len(str(c)), *(len(str(r[i])) for r in rows[:MAX_ROWS])) if rows else len(str(c))
              for i, c in enumerate(cols)]
    line = " | ".join(str(c).ljust(w) for c, w in zip(cols, widths))
    print(line)
    print("-" * len(line))
    for r in rows[:MAX_ROWS]:
        print(" | ".join(str(v).ljust(w) for v, w in zip(r, widths)))
    extra = f" (showing first {MAX_ROWS})" if len(rows) > MAX_ROWS else ""
    print(f"\n{len(rows)} row(s){extra}\n")


def split_statements(sql):
    """Split on semicolons that end a statement (not ones inside quotes or comments)."""
    statements, buf, quote, i = [], [], None, 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            buf.append(ch)
        elif sql.startswith("--", i):
            end = sql.find("\n", i)
            end = len(sql) if end == -1 else end
            buf.append(sql[i:end])
            i = end
            continue
        elif ch == ";":
            statements.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    statements.append("".join(buf))
    keep = []
    for s in statements:
        code = [l for l in s.splitlines() if l.strip() and not l.strip().startswith("--")]
        if code:
            keep.append(s.strip())
    return keep


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    arg = sys.argv[1]
    path = Path(arg)
    sql = path.read_text(encoding="utf-8") if arg.endswith(".sql") and path.exists() else arg
    con = sqlite3.connect(DB)
    for stmt in split_statements(sql):
        first = next((l for l in stmt.splitlines() if l.strip() and not l.strip().startswith("--")), "")
        print(f">>> {first.strip()[:70]}")
        try:
            show(con.execute(stmt))
        except sqlite3.Error as e:
            print(f"ERROR: {e}\n")
    con.close()


if __name__ == "__main__":
    main()
