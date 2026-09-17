import os
import sys
import json
from datetime import datetime, date
from decimal import Decimal
import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"
BACKUP_DIR = r"c:\Users\ASUS\Downloads\dokan-main\backups"

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, bytes):
        return obj.hex()
    raise TypeError(f"Type {type(obj)} not serializable")

def format_sql_value(val):
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float, Decimal)):
        return str(val)
    if isinstance(val, (datetime, date)):
        return f"'{val.isoformat()}'"
    if isinstance(val, dict) or isinstance(val, list):
        escaped = json.dumps(val, ensure_ascii=False).replace("'", "''")
        return f"'{escaped}'"
    if isinstance(val, str):
        escaped = val.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(val, bytes):
        return f"E'\\\\x{val.hex()}'"
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"

def run_backup():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_path = os.path.join(BACKUP_DIR, f"railway_dokan_backup_{now_str}.sql")
    json_path = os.path.join(BACKUP_DIR, f"railway_dokan_backup_{now_str}.json")

    print(f"Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL, connect_timeout=15)
    cur = conn.cursor()

    # 1. Get all public base tables in dependency order
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"Discovered {len(tables)} tables to backup.")

    full_json_data = {
        "metadata": {
            "backup_created_at": datetime.now().isoformat(),
            "database": "railway",
            "host": "altaria.proxy.rlwy.net",
            "port": 37393,
            "table_count": len(tables)
        },
        "tables": {}
    }

    sql_lines = []
    sql_lines.append(f"-- ========================================================")
    sql_lines.append(f"-- Railway PostgreSQL Database Full Backup")
    sql_lines.append(f"-- Created At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sql_lines.append(f"-- Database: railway | Total Tables: {len(tables)}")
    sql_lines.append(f"-- ========================================================\n")
    sql_lines.append("SET client_encoding = 'UTF8';")
    sql_lines.append("SET standard_conforming_strings = on;\n")

    summary_stats = []

    for t in tables:
        # Get column definitions
        cur.execute("""
            SELECT column_name, data_type, udt_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (t,))
        columns_info = cur.fetchall()
        col_names = [c[0] for c in columns_info]

        # Fetch all data
        query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(t))
        cur.execute(query)
        rows = cur.fetchall()
        summary_stats.append((t, len(rows)))

        # Add to JSON dump
        table_rows_dict = []
        for r in rows:
            row_dict = {}
            for col, val in zip(col_names, r):
                row_dict[col] = val
            table_rows_dict.append(row_dict)
        full_json_data["tables"][t] = table_rows_dict

        # Add to SQL dump
        sql_lines.append(f"\n-- --------------------------------------------------------")
        sql_lines.append(f"-- Table: {t} ({len(rows)} rows)")
        sql_lines.append(f"-- --------------------------------------------------------")

        # Table structure
        col_defs = []
        for c in columns_info:
            c_name, c_type, c_udt, c_null, c_def = c
            # map types
            type_str = c_udt.upper()
            if type_str == "VARCHAR":
                type_str = "CHARACTER VARYING"
            null_str = "NOT NULL" if c_null == "NO" else ""
            def_str = f"DEFAULT {c_def}" if c_def else ""
            col_defs.append(f"    {sql.Identifier(c_name).as_string(conn)} {type_str} {null_str} {def_str}".strip())

        sql_lines.append(f"CREATE TABLE IF NOT EXISTS public.{sql.Identifier(t).as_string(conn)} (")
        sql_lines.append(",\n".join(col_defs))
        sql_lines.append(");")

        if rows:
            col_list_str = ", ".join([sql.Identifier(c).as_string(conn) for c in col_names])
            # Write in batches of 500
            batch_size = 500
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                val_rows = []
                for r in batch:
                    formatted_vals = [format_sql_value(v) for v in r]
                    val_rows.append(f"({', '.join(formatted_vals)})")
                
                insert_stmt = f"INSERT INTO public.{sql.Identifier(t).as_string(conn)} ({col_list_str}) VALUES\n" + ",\n".join(val_rows) + ";"
                sql_lines.append(insert_stmt)

        # Reset sequence if id column exists
        if "id" in col_names:
            sql_lines.append(f"SELECT setval(pg_get_serial_sequence('public.{sql.Identifier(t).as_string(conn)}', 'id'), COALESCE((SELECT MAX(id) FROM public.{sql.Identifier(t).as_string(conn)}), 1), true) WHERE pg_get_serial_sequence('public.{sql.Identifier(t).as_string(conn)}', 'id') IS NOT NULL;")

    # Write SQL File
    print(f"\nWriting SQL dump to {sql_path}...")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sql_lines))

    # Write JSON File
    print(f"Writing JSON dump to {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(full_json_data, f, ensure_ascii=False, indent=2, default=json_serial)

    sql_size_kb = os.path.getsize(sql_path) / 1024
    json_size_kb = os.path.getsize(json_path) / 1024

    print(f"\n=== BACKUP COMPLETED SUCCESSFULLY! ===")
    print(f"SQL Backup:  {sql_path} ({sql_size_kb:.2f} KB)")
    print(f"JSON Backup: {json_path} ({json_size_kb:.2f} KB)")
    print("\nTable Breakdown:")
    for t, cnt in summary_stats:
        print(f"  - {t:<30}: {cnt:>6} rows")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_backup()
