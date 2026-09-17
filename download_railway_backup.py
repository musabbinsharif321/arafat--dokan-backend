import os
import sys
import time
import json
import datetime
import psycopg2

DATABASE_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    print(f"Connecting to Railway PostgreSQL...")
    conn = None
    for attempt in range(1, 11):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            print("Connected successfully!")
            break
        except Exception as e:
            print(f"Attempt {attempt}/10 failed ({e}). Retrying in 3 seconds...")
            time.sleep(3)

    if not conn:
        print("Could not establish connection to Railway PostgreSQL.")
        sys.exit(1)

    # Create backup directory
    backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    sql_backup_path = os.path.join(backup_dir, f"railway_backup_{timestamp}.sql")
    json_backup_path = os.path.join(backup_dir, f"railway_backup_{timestamp}.json")

    cur = conn.cursor()

    # Get all tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    print(f"Found {len(tables)} tables in database.")

    total_rows = 0
    all_data = {}

    with open(sql_backup_path, "w", encoding="utf-8") as f_sql:
        f_sql.write(f"-- ==========================================================\n")
        f_sql.write(f"-- Railway PostgreSQL Full Backup\n")
        f_sql.write(f"-- Created At: {datetime.datetime.now().isoformat()}\n")
        f_sql.write(f"-- Database: railway\n")
        f_sql.write(f"-- ==========================================================\n\n")
        f_sql.write("SET statement_timeout = 0;\n")
        f_sql.write("SET lock_timeout = 0;\n")
        f_sql.write("SET client_encoding = 'UTF8';\n")
        f_sql.write("SET standard_conforming_strings = on;\n\n")

        for table in tables:
            # Get columns
            cur.execute(f"""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (table,))
            cols_info = cur.fetchall()
            col_names = [c[0] for c in cols_info]
            
            # Count rows
            cur.execute(f'SELECT COUNT(*) FROM "{table}";')
            count = cur.fetchone()[0]
            total_rows += count
            print(f"  Exporting table: {table} ({count} rows)...")

            # Fetch rows
            cur.execute(f'SELECT * FROM "{table}";')
            rows = cur.fetchall()

            table_records = []
            f_sql.write(f"\n-- Table: {table} ({count} rows)\n")
            
            for row in rows:
                row_dict = {}
                sql_vals = []
                for col_name, val in zip(col_names, row):
                    # Handle json serializable
                    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
                        row_dict[col_name] = str(val)
                    elif hasattr(val, '__float__') and not isinstance(val, (int, float, bool)):
                        row_dict[col_name] = float(val)
                    else:
                        row_dict[col_name] = val

                    # Format for SQL INSERT
                    if val is None:
                        sql_vals.append("NULL")
                    elif isinstance(val, bool):
                        sql_vals.append("TRUE" if val else "FALSE")
                    elif isinstance(val, (int, float)):
                        sql_vals.append(str(val))
                    elif isinstance(val, (dict, list)):
                        escaped = json.dumps(val).replace("'", "''")
                        sql_vals.append(f"'{escaped}'")
                    else:
                        escaped = str(val).replace("'", "''")
                        sql_vals.append(f"'{escaped}'")

                table_records.append(row_dict)
                quoted_cols = ', '.join([f'"{c}"' for c in col_names])
                val_str = ', '.join(sql_vals)
                f_sql.write(f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({val_str});\n')

            all_data[table] = table_records

    # Also save JSON format
    with open(json_backup_path, "w", encoding="utf-8") as f_json:
        json.dump(all_data, f_json, ensure_ascii=False, indent=2, default=str)

    cur.close()
    conn.close()

    print("\n" + "="*60)
    print("BACKUP COMPLETED SUCCESSFULLY!")
    print(f"Total Tables Exported: {len(tables)}")
    print(f"Total Records Exported: {total_rows}")
    print(f"SQL Backup File:  {sql_backup_path}")
    print(f"JSON Backup File: {json_backup_path}")
    print("="*60)

if __name__ == "__main__":
    main()
