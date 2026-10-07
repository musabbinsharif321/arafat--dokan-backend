import psycopg2

DATABASE_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

UPDATES = {
    33: 'Holcim Strong Structure',
    34: 'Holcim Supercrete',
    35: 'Holcim Coastal Guard',
    36: 'King Brand',
    37: 'Holcim Waterprotect',
    38: 'Holcim Supercrete Plus',
    39: 'Aman (OPC)',
}

def main():
    print("Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 1. Update api_product
    print("Updating api_product names without PCC...")
    for pid, new_name in UPDATES.items():
        cur.execute("UPDATE api_product SET name = %s WHERE id = %s RETURNING id, name;", (new_name, pid))
        res = cur.fetchone()
        if res:
            print(f"Product {res[0]} updated to: {res[1]}")

    # 2. Update api_transactionitem for these product_ids
    print("\nUpdating api_transactionitem by product_id...")
    for pid, new_name in UPDATES.items():
        cur.execute("""
            UPDATE api_transactionitem 
            SET product_name = CASE 
                WHEN product_name ~* '\\((?:ইনভ|inv)?:?\\s*[a-zA-Z0-9-]+\\)' 
                THEN %s || ' ' || substring(product_name from '\\((?:ইনভ|inv)?:?\\s*[a-zA-Z0-9-]+\\)')
                ELSE %s 
            END
            WHERE product_id = %s;
        """, (new_name, new_name, pid))
        print(f"Updated transaction items for product_id {pid}: {cur.rowcount} rows affected.")

    # 3. Update legacy transaction items with '- PCC'
    LEGACY_REMOVALS = {
        'Holcim Strong Structure - PCC': 'Holcim Strong Structure',
        'Holcim Supercrete - PCC': 'Holcim Supercrete',
        'Holcim Coastal Guard - PCC': 'Holcim Coastal Guard',
        'King Brand - PCC': 'King Brand',
    }
    for old_n, new_n in LEGACY_REMOVALS.items():
        cur.execute("UPDATE api_transactionitem SET product_name = %s WHERE product_name = %s;", (new_n, old_n))
        if cur.rowcount > 0:
            print(f"Updated legacy text '{old_n}' -> '{new_n}': {cur.rowcount} rows affected.")

    conn.commit()

    print("\nVerifying current cement products in api_product:")
    cur.execute("SELECT id, name, category_name FROM api_product WHERE id >= 33 ORDER BY id;")
    for r in cur.fetchall():
        print(f"ID {r[0]}: {r[1]} ({r[2]})")

    conn.close()
    print("\nRailway PostgreSQL updated successfully!")

if __name__ == '__main__':
    main()
