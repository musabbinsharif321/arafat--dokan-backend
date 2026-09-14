import psycopg2
from decimal import Decimal

DB_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Create or get Category: 'সিমেন্ট'
    cur.execute("SELECT id, name FROM api_category WHERE name = 'সিমেন্ট';")
    cement_cat = cur.fetchone()
    if not cement_cat:
        cur.execute("INSERT INTO api_category (name, description) VALUES ('সিমেন্ট', 'সকল প্রকার সিমেন্ট') RETURNING id;")
        cement_cat_id = cur.fetchone()[0]
    else:
        cement_cat_id = cement_cat[0]

    print(f"Category 'সিমেন্ট' ID: {cement_cat_id}")

    # 2. Cement products to insert/update
    cement_items = [
        ('Holcim Strong Structure (PCC)', 'হোলসিম স্ট্রং স্ট্রাকচার (Holcim Strong Structure - PCC)', 'Holcim', cement_cat_id, 'সিমেন্ট', Decimal('375.00'), 'বস্তা', 'CEM-HOLCIM-SS-PCC'),
        ('Holcim Supercrete (PCC)', 'হোলসিম সুপারক্রিট (Holcim Supercrete - PCC)', 'Holcim', cement_cat_id, 'সিমেন্ট', Decimal('110.00'), 'বস্তা', 'CEM-HOLCIM-SC-PCC'),
        ('Holcim Coastal Guard (PCC)', 'হোলসিম কোস্টাল গার্ড (Holcim Coastal Guard - PCC)', 'Holcim', cement_cat_id, 'সিমেন্ট', Decimal('364.00'), 'বস্তা', 'CEM-HOLCIM-CG-PCC'),
        ('King Brand (PCC)', 'কিং ব্র্যান্ড সিমেন্ট (King Brand - PCC)', 'King Brand', cement_cat_id, 'সিমেন্ট', Decimal('85.00'), 'বস্তা', 'CEM-KINGBRAND-PCC'),
    ]

    for short_name, full_name, brand, cat_id, cat_name, stock, unit, sku in cement_items:
        # Check if already exists by full_name or short_name
        cur.execute("SELECT id FROM api_product WHERE name = %s OR name = %s;", (full_name, short_name))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE api_product
                SET name = %s, brand = %s, category_id = %s, category_name = %s, stock = %s, unit = %s, sku = %s, updated_at = NOW()
                WHERE id = %s;
            """, (full_name, brand, cat_id, cat_name, stock, unit, sku, existing[0]))
            print(f"Updated product [{existing[0]}] {full_name} -> Stock: {stock} {unit}")
        else:
            cur.execute("""
                INSERT INTO api_product
                (name, brand, category_id, category_name, stock, min_stock, unit, purchase_price, sell_price, sku, needs_price_review, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id;
            """, (full_name, brand, cat_id, cat_name, stock, Decimal('50.00'), unit, Decimal('0.00'), Decimal('0.00'), sku, False))
            p_id = cur.fetchone()[0]
            print(f"Inserted product [{p_id}] {full_name} -> Stock: {stock} {unit}")

    # 3. Restore SCRM 8mm and 10mm stock if 0
    cur.execute("UPDATE api_product SET stock = 15891.90 WHERE name = 'SCRM ৮ মিলি রড' AND stock = 0;")
    if cur.rowcount > 0:
        print(f"Restored SCRM ৮ মিলি রড stock to 15,891.90 KG")

    cur.execute("UPDATE api_product SET stock = 13415.40 WHERE name = 'SCRM ১০ মিলি রড' AND stock = 0;")
    if cur.rowcount > 0:
        print(f"Restored SCRM ১০ মিলি রড stock to 13,415.40 KG")

    conn.commit()
    print("\n--- ALL CEMENT STOCKS COMMITTED SUCCESSFULLY ---")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
