import os
import sys
import gzip
import json
import logging
import tempfile
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger("dokan_backup")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

def json_serial(obj):
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
    if isinstance(val, (dict, list)):
        escaped = json.dumps(val, ensure_ascii=False).replace("'", "''")
        return f"'{escaped}'"
    if isinstance(val, str):
        escaped = val.replace("'", "''")
        return f"'{escaped}'"
    if isinstance(val, bytes):
        return f"E'\\\\x{val.hex()}'"
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"

def dump_postgres_database(output_file_path):
    """
    Dumps all public tables in PostgreSQL database directly using psycopg2
    and compresses output to .sql.gz
    """
    import psycopg2
    from psycopg2 import sql
    from django.conf import settings

    db_conf = settings.DATABASES["default"]
    db_name = db_conf.get("NAME")
    db_user = db_conf.get("USER")
    db_password = db_conf.get("PASSWORD")
    db_host = db_conf.get("HOST")
    db_port = db_conf.get("PORT")

    database_url = os.environ.get("DATABASE_URL", "").strip()

    logger.info(f"Connecting to PostgreSQL (host={db_host}, db={db_name})...")
    if database_url:
        conn = psycopg2.connect(database_url, connect_timeout=30)
    else:
        conn = psycopg2.connect(
            dbname=db_name,
            user=db_user,
            password=db_password,
            host=db_host or "localhost",
            port=db_port or 5432,
            connect_timeout=30
        )

    cur = conn.cursor()

    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    tables = [r[0] for r in cur.fetchall()]
    logger.info(f"Found {len(tables)} tables to backup.")

    with gzip.open(output_file_path, "wt", encoding="utf-8") as f_out:
        now_dt = datetime.now()
        f_out.write("-- ========================================================\n")
        f_out.write(f"-- Dokan ERP PostgreSQL Full Backup\n")
        f_out.write(f"-- Created At: {now_dt.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"-- Total Tables: {len(tables)}\n")
        f_out.write("-- ========================================================\n\n")
        f_out.write("SET client_encoding = 'UTF8';\n")
        f_out.write("SET standard_conforming_strings = on;\n\n")

        total_rows = 0
        for t in tables:
            cur.execute("""
                SELECT column_name, data_type, udt_name, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position;
            """, (t,))
            columns_info = cur.fetchall()
            col_names = [c[0] for c in columns_info]

            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(t))
            cur.execute(query)
            rows = cur.fetchall()
            total_rows += len(rows)

            f_out.write(f"\n-- --------------------------------------------------------\n")
            f_out.write(f"-- Table: {t} ({len(rows)} rows)\n")
            f_out.write(f"-- --------------------------------------------------------\n")

            col_defs = []
            for c in columns_info:
                c_name, c_type, c_udt, c_null, c_def = c
                type_str = c_udt.upper()
                if type_str == "VARCHAR":
                    type_str = "CHARACTER VARYING"
                null_str = "NOT NULL" if c_null == "NO" else ""
                def_str = f"DEFAULT {c_def}" if c_def else ""
                col_defs.append(f"    {sql.Identifier(c_name).as_string(conn)} {type_str} {null_str} {def_str}".strip())

            f_out.write(f"CREATE TABLE IF NOT EXISTS public.{sql.Identifier(t).as_string(conn)} (\n")
            f_out.write(",\n".join(col_defs))
            f_out.write("\n);\n")

            if rows:
                col_list_str = ", ".join([sql.Identifier(c).as_string(conn) for c in col_names])
                batch_size = 500
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    val_rows = []
                    for r in batch:
                        formatted_vals = [format_sql_value(v) for v in r]
                        val_rows.append(f"({', '.join(formatted_vals)})")
                    insert_stmt = f"INSERT INTO public.{sql.Identifier(t).as_string(conn)} ({col_list_str}) VALUES\n" + ",\n".join(val_rows) + ";\n"
                    f_out.write(insert_stmt)

            if "id" in col_names:
                f_out.write(f"SELECT setval(pg_get_serial_sequence('public.{sql.Identifier(t).as_string(conn)}', 'id'), COALESCE((SELECT MAX(id) FROM public.{sql.Identifier(t).as_string(conn)}), 1), true) WHERE pg_get_serial_sequence('public.{sql.Identifier(t).as_string(conn)}', 'id') IS NOT NULL;\n")

    cur.close()
    conn.close()
    logger.info(f"Database dump completed successfully: {total_rows} records backed up.")

def dump_sqlite_database(output_file_path):
    """Fallback for local SQLite database"""
    from django.conf import settings
    db_path = settings.DATABASES["default"]["NAME"]
    logger.info(f"Dumping SQLite database from {db_path}...")
    with open(db_path, "rb") as f_in:
        with gzip.open(output_file_path, "wb") as f_out:
            f_out.writelines(f_in)
    logger.info("SQLite database compressed and saved.")

def generate_database_backup(destination_dir=None):
    from django.conf import settings
    dest_dir = destination_dir or tempfile.gettempdir()
    os.makedirs(dest_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    backup_filename = f"dokan_db_backup_{timestamp}.sql.gz"
    backup_path = os.path.join(dest_dir, backup_filename)

    engine = settings.DATABASES["default"].get("ENGINE", "")
    if "postgresql" in engine or os.environ.get("DATABASE_URL"):
        dump_postgres_database(backup_path)
    else:
        dump_sqlite_database(backup_path)

    file_size_kb = os.path.getsize(backup_path) / 1024
    logger.info(f"Generated backup file: {backup_path} ({file_size_kb:.2f} KB)")
    return backup_path, backup_filename

def get_gdrive_service():
    """Builds and returns Google Drive API v3 service from credentials"""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    sa_json_raw = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON", "").strip()
    sa_file_path = os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE", "").strip()

    creds = None
    if sa_json_raw:
        try:
            info = json.loads(sa_json_raw)
            creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
            logger.info("Loaded Google Service Account from GDRIVE_SERVICE_ACCOUNT_JSON env var.")
        except Exception as e:
            logger.error(f"Failed to parse GDRIVE_SERVICE_ACCOUNT_JSON: {e}")
            raise
    elif sa_file_path and os.path.exists(sa_file_path):
        creds = service_account.Credentials.from_service_account_file(sa_file_path, scopes=SCOPES)
        logger.info(f"Loaded Google Service Account from file: {sa_file_path}")
    else:
        raise ValueError(
            "Neither GDRIVE_SERVICE_ACCOUNT_JSON nor GDRIVE_SERVICE_ACCOUNT_FILE is set! "
            "Please provide Google Service Account credentials to enable Google Drive upload."
        )

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service

def upload_to_gdrive(file_path, filename=None, folder_id=None):
    from googleapiclient.http import MediaFileUpload

    folder_id = folder_id or os.environ.get("GDRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        raise ValueError("GDRIVE_FOLDER_ID is not configured in environment variables!")

    service = get_gdrive_service()
    fname = filename or os.path.basename(file_path)

    logger.info(f"Uploading '{fname}' to Google Drive folder '{folder_id}'...")

    file_metadata = {
        "name": fname,
        "parents": [folder_id]
    }
    media = MediaFileUpload(file_path, mimetype="application/gzip", resumable=True)
    
    file_obj = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, size, webViewLink"
    ).execute()

    logger.info(f"Google Drive upload successful! File ID: {file_obj.get('id')}, Size: {file_obj.get('size')} bytes")
    return file_obj

def prune_old_gdrive_backups(folder_id=None, retention_days=30):
    """Deletes backup files in Google Drive older than retention_days"""
    folder_id = folder_id or os.environ.get("GDRIVE_FOLDER_ID", "").strip()
    if not folder_id:
        return

    try:
        service = get_gdrive_service()
        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()
        
        # Query files in folder with matching prefix created before cutoff_date
        query = f"'{folder_id}' in parents and name contains 'dokan_db_backup_' and trashed = false and createdTime < '{cutoff_date}Z'"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, createdTime)"
        ).execute()

        old_files = results.get("files", [])
        if old_files:
            logger.info(f"Found {len(old_files)} old backup(s) to prune (> {retention_days} days old)...")
            for f in old_files:
                fid = f.get("id")
                fname = f.get("name")
                service.files().delete(fileId=fid).execute()
                logger.info(f"Deleted old backup: {fname} (ID: {fid})")
        else:
            logger.info("No expired backups found in Google Drive to prune.")
    except Exception as e:
        logger.warning(f"Error while cleaning up old backups: {e}")

def perform_full_backup_to_gdrive():
    """Coordinates taking the backup, uploading to Google Drive, and removing local temp file"""
    logger.info("=== STARTING DOKAN AUTOMATED BACKUP PROCEDURE ===")
    backup_path = None
    try:
        backup_path, backup_filename = generate_database_backup()
        file_info = upload_to_gdrive(backup_path, filename=backup_filename)
        
        # Cleanup old backups from Google Drive (keep last 30 days by default)
        retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
        prune_old_gdrive_backups(retention_days=retention_days)

        logger.info(f"=== BACKUP FINISHED SUCCESSFULLY: {backup_filename} ===")
        return {
            "status": "success",
            "file_name": backup_filename,
            "gdrive_id": file_info.get("id"),
            "link": file_info.get("webViewLink")
        }
    except Exception as e:
        logger.error(f"Backup failed with error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }
    finally:
        # Remove temporary file on local disk to save container space
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
                logger.info("Cleaned up local temporary backup file.")
            except Exception:
                pass
