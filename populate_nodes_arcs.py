# python populate_nodes_arcs.py --nodes nodes.csv --arcs arcs.csv
# per popolare le tabelle

import argparse
import csv
import os
import sys
import tempfile

import psycopg2

# Import dal progetto
try:
    from MapViewer.db.db_connection import create_connection
except Exception as e:
    print("✖ Impossibile importare MapViewer.db.db_connection.create_connection. "
          "Esegui questo script dalla root del progetto o sistema il PYTHONPATH.", file=sys.stderr)
    raise

# Colonne previste dallo schema
NODE_COLS_PREF = [
    "node_id","x1","x2","y1","y2","z1","z2","floor_level","capacity",
    "node_type","current_occupancy","safe","evacuation_path",
    "last_modified","last_modified_by"
]
ARC_COLS_PREF = [
    "arc_id","flow","traversal_time","active","x1","x2","y1","y2","z1","z2",
    "capacity","initial_node","final_node"
]

BOOL_MAP = {"1":"TRUE","0":"FALSE","true":"TRUE","false":"FALSE","si":"TRUE","sì":"TRUE","no":"FALSE"}

def _seconds_to_hms(v: str) -> str:
    s = int(v)
    h = s // 3600
    m = (s % 3600) // 60
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}"

def _normalize_pg_int_array(val: str) -> str:
    """
    Normalizza vari formati in un literal Postgres int[]: "{1,2,3}".
    Accetta: "{1,2,3}", "[1,2,3]", "1,2,3", " 1 ; 2 ; 3 " (con virgole o punti e virgola).
    """
    if val is None:
        return val
    s = str(val).strip()
    if s == "":
        return s
    # già in forma {..}
    if s.startswith("{") and s.endswith("}"):
        return s
    # forma [..] -> {..}
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
    else:
        inner = s
    # Sostituisci eventuali separatori ; con ,
    inner = inner.replace(";", ",")
    # Rimuovi spazi superflui
    parts = [p.strip() for p in inner.split(",") if p.strip() != ""]
    if not parts:
        return ""
    try:
        _ = [str(int(x)) for x in parts]
    except Exception:
        return "{" + ",".join(parts) + "}"
    return "{" + ",".join(parts) + "}"

def normalize_nodes_csv(in_path: str, out_dir: str, db_cols: set) -> str:
    """
    - Converte safe a TRUE/FALSE
    - Converte floor_level/evacuation_path a literal int[] valido
    - Filtra colonne al sottoinsieme presente a DB (mantiene l'ordine NODE_COLS_PREF)
    """
    out_path = os.path.join(out_dir, "nodes.normalized.csv")
    with open(in_path, "r", newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        if reader.fieldnames is None:
            raise ValueError("nodes.csv senza header.")
        # colonne ammesse = intersezione tra CSV e DB
        allowed = [c for c in NODE_COLS_PREF if c in reader.fieldnames and c in db_cols]
        if "node_id" in db_cols and "node_id" not in allowed and "node_id" in reader.fieldnames:
            allowed = ["node_id"] + allowed
        with open(out_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=allowed)
            writer.writeheader()
            for row in reader:
                r = {k: row.get(k, "") for k in allowed}
                # safe -> booleano
                if "safe" in r and r["safe"] not in (None, ""):
                    v = str(r["safe"]).strip().lower()
                    if v in BOOL_MAP:
                        r["safe"] = BOOL_MAP[v]
                # floor_level / evacuation_path -> array
                for arr_col in ("floor_level", "evacuation_path"):
                    if arr_col in r and r[arr_col] not in (None, ""):
                        r[arr_col] = _normalize_pg_int_array(r[arr_col])
                writer.writerow(r)
    return out_path

def normalize_arcs_csv(in_path: str, out_dir: str, db_cols: set) -> str:
    """
    - Converte active a TRUE/FALSE
    - Converte traversal_time numerico->HH:MM:SS
    - Filtra colonne al sottoinsieme presente a DB (mantiene l'ordine ARC_COLS_PREF)
    """
    out_path = os.path.join(out_dir, "arcs.normalized.csv")
    with open(in_path, "r", newline="", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        if reader.fieldnames is None:
            raise ValueError("arcs.csv senza header.")
        allowed = [c for c in ARC_COLS_PREF if c in reader.fieldnames and c in db_cols]
        if "arc_id" in db_cols and "arc_id" not in allowed and "arc_id" in reader.fieldnames:
            allowed = ["arc_id"] + allowed
        with open(out_path, "w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=allowed)
            writer.writeheader()
            for row in reader:
                r = {k: row.get(k, "") for k in allowed}
                # active -> booleano
                if "active" in r and r["active"] not in (None, ""):
                    v = str(r["active"]).strip().lower()
                    if v in BOOL_MAP:
                        r["active"] = BOOL_MAP[v]
                # traversal_time numerico -> HH:MM:SS
                if "traversal_time" in r and r["traversal_time"] not in (None, ""):
                    vt = str(r["traversal_time"]).strip()
                    if vt.isdigit():
                        r["traversal_time"] = _seconds_to_hms(vt)
                writer.writerow(r)
    return out_path

def get_table_columns(conn, table: str) -> list[str]:
    with conn.cursor() as cur:
        if "." in table:
            schema, name = table.split(".", 1)
        else:
            schema, name = "public", table
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, name),
        )
        rows = cur.fetchall()
        if not rows:
            cur.execute(f"SELECT * FROM {table} LIMIT 0;")
            return [d.name for d in cur.description]
        return [r[0] for r in rows]

def realign_serial_sequence(conn, table: str, pk_col: str):
    with conn.cursor() as cur:
        cur.execute("SELECT pg_get_serial_sequence(%s, %s);", (table, pk_col))
        seq_row = cur.fetchone()
        seq_name = seq_row[0]
        if seq_name:
            cur.execute(f"SELECT setval(%s, COALESCE((SELECT MAX({pk_col}) FROM {table}), 0))", (seq_name,))

def copy_with_headers(conn, table: str, csv_path: str, columns: list[str], delimiter: str = ",", null_str: str | None = None):
    null_clause = f" NULL '{null_str}'" if null_str is not None else ""
    copy_sql = f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER '{delimiter}'{null_clause})"
    with open(csv_path, "r", newline="", encoding="utf-8") as fin, conn.cursor() as cur:
        cur.copy_expert(copy_sql, fin)

def main():
    ap = argparse.ArgumentParser(description="Popola le tabelle 'nodes' e 'arcs' da CSV.")
    ap.add_argument("--nodes", required=True, help="Percorso del CSV dei nodi.")
    ap.add_argument("--arcs", required=True, help="Percorso del CSV degli archi.")
    ap.add_argument("--delimiter", default=",")
    ap.add_argument("--null", dest="null_str", default=None, help="Stringa usata per NULL nel CSV (es. 'NULL' o '').")
    ap.add_argument("--truncate", action="store_true", help="TRUNCATE entrambe le tabelle prima del caricamento.")
    args = ap.parse_args()

    conn = create_connection()
    if conn is None:
        print("✖ Connessione DB fallita.", file=sys.stderr)
        sys.exit(2)

    try:
        # Determina colonne reali a DB
        node_db_cols = get_table_columns(conn, "nodes")
        arc_db_cols  = get_table_columns(conn, "arcs")
        node_db_set  = set(node_db_cols)
        arc_db_set   = set(arc_db_cols)

        # Normalizza CSV in file temporanei e determina colonne effettive da usare
        with tempfile.TemporaryDirectory() as tmpd:
            nodes_csv_norm = normalize_nodes_csv(args.nodes, tmpd, node_db_set)
            arcs_csv_norm  = normalize_arcs_csv(args.arcs, tmpd, arc_db_set)

            # Filtra all'intersezione CSV_norm ∩ DB mantenendo ordine DB
            with open(nodes_csv_norm, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                node_cols_final = [c for c in node_db_cols if c in reader.fieldnames]
            with open(arcs_csv_norm, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                arc_cols_final = [c for c in arc_db_cols if c in reader.fieldnames]

            # Eventuale TRUNCATE (prima arcs poi nodes per FK safety)
            if args.truncate:
                with conn.cursor() as cur:
                    cur.execute("TRUNCATE TABLE arcs RESTART IDENTITY CASCADE;")
                    cur.execute("TRUNCATE TABLE nodes RESTART IDENTITY CASCADE;")

            # COPY: nodes, poi arcs
            copy_with_headers(conn, "nodes", nodes_csv_norm, node_cols_final, delimiter=args.delimiter, null_str=args.null_str)
            copy_with_headers(conn, "arcs", arcs_csv_norm, arc_cols_final, delimiter=args.delimiter, null_str=args.null_str)

            # Riallineo sequence per PK esplicite
            if "node_id" in node_db_set:
                realign_serial_sequence(conn, "nodes", "node_id")
            if "arc_id" in arc_db_set:
                realign_serial_sequence(conn, "arcs", "arc_id")

        conn.commit()
        print("✔ Caricamento completato: nodes + arcs.")
    except Exception as e:
        conn.rollback()
        print(f"✖ Errore durante il popolamento: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
