"""
=================================================================
 MINE SAFETY ANALYTICS  -  SQL RUNNER
=================================================================
 Runs SQL against mine_safety.db and prints the results as a table.

 Usage:
     python run_sql.py queries/v1_queries.sql      (run a whole file)
     python run_sql.py "SELECT * FROM shifts"      (run one query)

 Build the database first with:  python create_database.py
=================================================================
"""

import os
import sqlite3
import sys

DB_NAME = "mine_safety.db"


def print_table(cursor, rows):
    """Print query results as a simple aligned text table."""
    headers = [col[0] for col in cursor.description]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(str(value)))

    line = "  ".join(h.ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for row in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(row, widths)))
    print(f"({len(rows)} rows)\n")


def split_statements(sql_text):
    """Split a .sql file into single statements, keeping the comment
    lines that sit directly above each statement as its title."""
    statements = []
    for chunk in sql_text.split(";"):
        lines = [ln for ln in chunk.strip().splitlines()]
        code = "\n".join(ln for ln in lines if not ln.strip().startswith("--")).strip()
        if not code:
            continue
        title = [ln.strip("- ").strip() for ln in lines
                 if ln.strip().startswith("--") and ln.strip("- ").strip()]
        statements.append((title[-3:] if title else [], code))
    return statements


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    if not os.path.exists(DB_NAME):
        print(f"{DB_NAME} not found. Run:  python create_database.py")
        sys.exit(1)

    argument = sys.argv[1]
    if argument.endswith(".sql") and os.path.exists(argument):
        with open(argument, encoding="utf-8") as f:
            statements = split_statements(f.read())
    else:
        statements = [([], argument)]

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    for title, sql in statements:
        for t in title:
            print(f"## {t}")
        cursor.execute(sql)
        print_table(cursor, cursor.fetchall())

    connection.close()


if __name__ == "__main__":
    main()
