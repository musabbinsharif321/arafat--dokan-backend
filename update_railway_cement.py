import psycopg2

DATABASE_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

UPDATES = {
    33: 'Holcim Strong Structure - PCC',
    34: 'Holcim Supercrete - PCC',
    35: 'Holcim Coastal Guard - PCC',
    36: 'King Brand - PCC',
    37: 'Holcim Waterprotect',
    38: 'Holcim Supercrete Plus',
    39: 'Aman (OPC)',
}

def main():
    print("Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 1. Update api_product
    print("Updating api_product names...")
    for pid, new_name in UPDATES.items():
        cur.execute("UPDATE api_product SET name = %s WHERE id = %s RETURNING id, name;", (new_name, pid))
        res = cur.fetchone()
        if res:
            print(f"Product {res[0]} updated to: {res[1]}")

    # 2. Update api_transactionitem for these product_ids
    print("\nUpdating api_transactionitem by product_id...")
    for pid, new_name in UPDATES.items():
        # Preserve invoice tags if any, otherwise set to new_name
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

    # 3. Update any transaction items that have exact old names but null product_id
    OLD_NAME_MAPPING = {
        'হোলসিম স্ট্রং স্ট্রাকচার (Holcim Strong Structure - PCC)': 'Holcim Strong Structure - PCC',
        'হোলসিম সুপারক্রিট (Holcim Supercrete - PCC)': 'Holcim Supercrete - PCC',
        'হোলসিম কোস্টাল গার্ড (Holcim Coastal Guard - PCC)': 'Holcim Coastal Guard - PCC',
        'কিং ব্র্যান্ড সিমেন্ট (King Brand - PCC)': 'King Brand - PCC',
        'Holcim Waterprotect সিমেন্ট': 'Holcim Waterprotect',
        'হোলসিম সুপারক্রিট প্লাস (Holcim Supercrete Plus)': 'Holcim Supercrete Plus',
        'Aman (OPC) সিমেন্ট': 'Aman (OPC)',
        'হোলসিম কোস্টাল গার্ড': 'Holcim Coastal Guard - PCC',
        'হোলসিম সিমেন্ট': 'Holcim Cement',
        'সুপারক্রিট সিমেন্ট': 'Holcim Supercrete - PCC',
        'আমান ওপিসি সিমেন্ট': 'Aman (OPC)',
        'কিং ব্র্যান্ড সিমেন্ট': 'King Brand - PCC',
    }
    for old_n, new_n in OLD_NAME_MAPPING.items():
        cur.execute("UPDATE api_transactionitem SET product_name = %s WHERE product_name = %s;", (new_n, old_n))
        if cur.rowcount > 0:
            print(f"Updated legacy text '{old_n}' -> '{new_n}': {cur.rowcount} rows affected.")

    conn.commit()
    print("\nVerifying current cement products in api_product:")
    cur.execute("SELECT id, name, category_name FROM api_product WHERE id >= 33 ORDER BY id;")
    for r in cur.fetchall():
        print(f"ID {r[0]}: {r[1]} ({r[2]})")

    conn.close()
    print("\nAll Railway PostgreSQL updates completed successfully!")

if __name__ == '__main__':
    main()
