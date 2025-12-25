import sqlite3
import os
from textwrap import dedent


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str):
    print("=" * 60)
    print(title)
    print("=" * 60)


def connect_to_db(path: str) -> sqlite3.Connection:
    # Ha a fájl nem létezik, sqlite3 létrehozza
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # oszlopneves eléréshez
    return conn


def input_non_empty(prompt: str) -> str:
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("Üres érték nem megengedett, próbáld újra.")


def menu():
    print_header("SQLite3 adatbázis-kezelő (Python)")
    print("Válassz egy műveletet:")
    print("  1) Új adatbázis létrehozása / meglévő megnyitása")
    print("  2) Tábla létrehozása")
    print("  3) Rekord beszúrása (INSERT)")
    print("  4) SELECT lekérdezés futtatása")
    print("  5) Táblák listázása")
    print("  0) Kilépés")
    choice = input("Választás: ").strip()
    return choice


def ensure_connection(conn):
    if conn is None:
        print("Nincs megnyitott adatbázis. Előbb válaszd az 1) menüpontot.")
        return False
    return True


def action_open_db():
    clear_screen()
    print_header("Adatbázis létrehozása / megnyitása")
    db_path = input_non_empty("Adatbázis fájl neve vagy elérési útja (pl. data.db): ")
    conn = connect_to_db(db_path)
    print(f"Sikeresen csatlakozva ehhez az adatbázishoz: {db_path}")
    input("Nyomj Entert a folytatáshoz...")
    return conn


def action_create_table(conn: sqlite3.Connection):
    clear_screen()
    print_header("Tábla létrehozása")

    if not ensure_connection(conn):
        input("Nyomj Entert a folytatáshoz...")
        return conn

    table_name = input_non_empty("Tábla neve: ")

    print(
        dedent(
            """
            Add meg az oszlopdefiníciókat SQL szintaxissal, pl.:
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL,
              age INTEGER

            A teljes listát egyben írd be (ENTER-rel lezárod).
            """
        )
    )

    columns_def = input_non_empty("Oszlopdefiníciók: ")

    sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def});"

    try:
        conn.execute(sql)
        conn.commit()
        print(f"A(z) '{table_name}' tábla létrehozva (ha még nem létezett).")
    except sqlite3.Error as e:
        print("Hiba történt a tábla létrehozásakor:")
        print(e)

    input("Nyomj Entert a folytatáshoz...")
    return conn


def list_tables(conn: sqlite3.Connection):
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    )
    rows = cursor.fetchall()
    return [row["name"] for row in rows]


def action_insert_row(conn: sqlite3.Connection):
    clear_screen()
    print_header("Rekord beszúrása (INSERT)")

    if not ensure_connection(conn):
        input("Nyomj Entert a folytatáshoz...")
        return conn

    tables = list_tables(conn)
    if not tables:
        print("Nincs egyetlen tábla sem az adatbázisban.")
        input("Nyomj Entert a folytatáshoz...")
        return conn

    print("Elérhető táblák:")
    for i, t in enumerate(tables, start=1):
        print(f"  {i}) {t}")
    choice = input_non_empty("Válaszd ki a táblát sorszámmal vagy névvel: ")

    if choice.isdigit() and 1 <= int(choice) <= len(tables):
        table_name = tables[int(choice) - 1]
    else:
        table_name = choice

    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name});")
        cols = cursor.fetchall()
        if not cols:
            print("Nem található ilyen tábla, vagy nincs oszlopinformáció.")
            input("Nyomj Entert a folytatáshoz...")
            return conn
    except sqlite3.Error as e:
        print("Hiba a tábla lekérdezésekor:")
        print(e)
        input("Nyomj Entert a folytatáshoz...")
        return conn

    print(f"Osztlopok a(z) '{table_name}' táblában:")
    columns = []
    for c in cols:
        col_name = c["name"]
        col_type = c["type"]
        notnull = c["notnull"]
        default = c["dflt_value"]
        pk = c["pk"]
        print(
            f"  - {col_name} ({col_type}) "
            f"{'NOT NULL' if notnull else ''} "
            f"{'PK' if pk else ''} "
            f"{'(alapértelmezett: ' + str(default) + ')' if default is not None else ''}"
        )
        columns.append(col_name)

    print("\nAdd meg az értékeket az egyes oszlopokhoz.")
    print("Ha egy oszlopot ki akarsz hagyni, hagyd üresen és nyomj Entert.")
    values = {}
    for col in columns:
        val = input(f"{col} = ").strip()
        if val != "":
            values[col] = val

    if not values:
        print("Nem adtál meg egyetlen értéket sem, beszúrás megszakítva.")
        input("Nyomj Entert a folytatáshoz...")
        return conn

    cols_part = ", ".join(values.keys())
    placeholders = ", ".join(["?"] * len(values))
    sql = f"INSERT INTO {table_name} ({cols_part}) VALUES ({placeholders});"
    params = list(values.values())

    try:
        conn.execute(sql, params)
        conn.commit()
        print("Rekord sikeresen beszúrva.")
    except sqlite3.Error as e:
        print("Hiba történt a beszúráskor:")
        print(e)

    input("Nyomj Entert a folytatáshoz...")
    return conn


def print_query_results(cursor: sqlite3.Cursor):
    rows = cursor.fetchall()
    if not rows:
        print("Nincs találat.")
        return

    col_names = [desc[0] for desc in cursor.description]

    col_widths = []
    for idx, name in enumerate(col_names):
        max_len = len(name)
        for row in rows:
            val = row[idx]
            val_str = "" if val is None else str(val)
            if len(val_str) > max_len:
                max_len = len(val_str)
        col_widths.append(max_len)

    header = " | ".join(name.ljust(col_widths[i]) for i, name in enumerate(col_names))
    sep = "-+-".join("-" * col_widths[i] for i in range(len(col_names)))
    print(header)
    print(sep)

    for row in rows:
        line = " | ".join(
            ("" if row[i] is None else str(row[i])).ljust(col_widths[i])
            for i in range(len(col_names))
        )
        print(line)


def action_select_query(conn: sqlite3.Connection):
    clear_screen()
    print_header("SELECT lekérdezés futtatása")

    if not ensure_connection(conn):
        input("Nyomj Entert a folytatáshoz...")
        return conn

    print(
        dedent(
            """
            Írj be egy teljes SELECT lekérdezést, pl.:
              SELECT * FROM users;
              SELECT name, age FROM users WHERE age > 18;

            Csak SELECT-et engedélyezünk biztonsági okokból.
            """
        )
    )
    query = input_non_empty("SQL > ")

    if not query.strip().lower().startswith("select"):
        print("Csak SELECT lekérdezések engedélyezettek ebben a menüpontban.")
        input("Nyomj Entert a folytatáshoz...")
        return conn

    try:
        cursor = conn.execute(query)
        print_query_results(cursor)
    except sqlite3.Error as e:
        print("Hiba történt a lekérdezés során:")
        print(e)

    input("Nyomj Entert a folytatáshoz...")
    return conn


def action_list_tables(conn: sqlite3.Connection):
    clear_screen()
    print_header("Táblák listázása")

    if not ensure_connection(conn):
        input("Nyomj Entert a folytatáshoz...")
        return conn

    tables = list_tables(conn)
    if not tables:
        print("Nincs tábla az adatbázisban.")
    else:
        print("Táblák az adatbázisban:")
        for t in tables:
            print(f"  - {t}")

    input("Nyomj Entert a folytatáshoz...")
    return conn


def main():
    conn = None

    while True:
        clear_screen()
        choice = menu()

        if choice == "1":
            conn = action_open_db()
        elif choice == "2":
            conn = action_create_table(conn)
        elif choice == "3":
            conn = action_insert_row(conn)
        elif choice == "4":
            conn = action_select_query(conn)
        elif choice == "5":
            conn = action_list_tables(conn)
        elif choice == "0":
            print("Kilépés...")
            if conn is not None:
                conn.close()
            break
        else:
            print("Ismeretlen menüpont, próbáld újra.")
            input("Nyomj Entert a folytatáshoz...")


if __name__ == "__main__":
    main()
