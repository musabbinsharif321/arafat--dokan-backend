import psycopg2
from decimal import Decimal

DB_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Create or get Categories: 'রড', 'রিং'
    cur.execute("SELECT id, name FROM api_category WHERE name = 'রড';")
    rod_cat = cur.fetchone()
    if not rod_cat:
        cur.execute("INSERT INTO api_category (name, description) VALUES ('রড', 'সকল প্রকার রড') RETURNING id;")
        rod_cat_id = cur.fetchone()[0]
    else:
        rod_cat_id = rod_cat[0]

    cur.execute("SELECT id, name FROM api_category WHERE name = 'রিং';")
    ring_cat = cur.fetchone()
    if not ring_cat:
        cur.execute("INSERT INTO api_category (name, description) VALUES ('রিং', 'সকল সাইজের রিং') RETURNING id;")
        ring_cat_id = cur.fetchone()[0]
    else:
        ring_cat_id = ring_cat[0]

    print(f"Categories -> রড: {rod_cat_id}, রিং: {ring_cat_id}")

    # (name, brand, category_id, category_name, stock, unit, sku)
    items = [
        # BSRM
        ('BSRM ৮ মিলি রড', 'BSRM', rod_cat_id, 'রড', Decimal('4100.10'), 'কেজি', 'ROD-BSRM-8M'),
        ('BSRM ১০ মিলি রড', 'BSRM', rod_cat_id, 'রড', Decimal('13150.80'), 'কেজি', 'ROD-BSRM-10M'),
        ('BSRM ১২ মিলি রড', 'BSRM', rod_cat_id, 'রড', Decimal('5848.40'), 'কেজি', 'ROD-BSRM-12M'),
        ('BSRM ১৬ মিলি রড', 'BSRM', rod_cat_id, 'রড', Decimal('12946.80'), 'কেজি', 'ROD-BSRM-16M'),
        ('BSRM ২০ মিলি রড', 'BSRM', rod_cat_id, 'রড', Decimal('1670.80'), 'কেজি', 'ROD-BSRM-20M'),

        # SCRM
        ('SCRM ৮ মিলি রড', 'SCRM', rod_cat_id, 'রড', Decimal('15891.90'), 'কেজি', 'ROD-SCRM-8M'),
        ('SCRM ১০ মিলি রড', 'SCRM', rod_cat_id, 'রড', Decimal('13415.40'), 'কেজি', 'ROD-SCRM-10M'),
        ('SCRM ১২ মিলি রড', 'SCRM', rod_cat_id, 'রড', Decimal('2927.10'), 'কেজি', 'ROD-SCRM-12M'),
        ('SCRM ১৬ মিলি রড', 'SCRM', rod_cat_id, 'রড', Decimal('12902.10'), 'কেজি', 'ROD-SCRM-16M'),
        ('SCRM ২০ মিলি রড', 'SCRM', rod_cat_id, 'রড', Decimal('4980.20'), 'কেজি', 'ROD-SCRM-20M'),

        # SCRM TMX
        ('SCRM TMX ৮ মিলি রড', 'SCRM TMX', rod_cat_id, 'রড', Decimal('7650.00'), 'কেজি', 'ROD-SCRMTMX-8M'),
        ('SCRM TMX ১০ মিলি রড', 'SCRM TMX', rod_cat_id, 'রড', Decimal('18779.50'), 'কেজি', 'ROD-SCRMTMX-10M'),
        ('SCRM TMX ১২ মিলি রড', 'SCRM TMX', rod_cat_id, 'রড', Decimal('6702.80'), 'কেজি', 'ROD-SCRMTMX-12M'),
        ('SCRM TMX ১৬ মিলি রড', 'SCRM TMX', rod_cat_id, 'রড', Decimal('16986.40'), 'কেজি', 'ROD-SCRMTMX-16M'),
        ('SCRM TMX ২০ মিলি রড', 'SCRM TMX', rod_cat_id, 'রড', Decimal('5415.20'), 'কেজি', 'ROD-SCRMTMX-20M'),
        ('SCRM TMX ২৫ মিলি রড', 'SCRM TMX', rod_cat_id, 'রড', Decimal('3389.00'), 'কেজি', 'ROD-SCRMTMX-25M'),

        # DSRM
        ('DSRM ৮ মিলি রড', 'DSRM', rod_cat_id, 'রড', Decimal('101.10'), 'কেজি', 'ROD-DSRM-8M'),

        # HKG
        ('HKG ১০ মিলি রড', 'HKG', rod_cat_id, 'রড', Decimal('0.00'), 'কেজি', 'ROD-HKG-10M'),
        ('HKG ১২ মিলি রড', 'HKG', rod_cat_id, 'রড', Decimal('5592.00'), 'কেজি', 'ROD-HKG-12M'),
        ('HKG ১৬ মিলি রড', 'HKG', rod_cat_id, 'রড', Decimal('1904.10'), 'কেজি', 'ROD-HKG-16M'),
        ('HKG ২০ মিলি রড', 'HKG', rod_cat_id, 'রড', Decimal('0.00'), 'কেজি', 'ROD-HKG-20M'),

        # KSML
        ('KSML ১০ মিলি রড', 'KSML', rod_cat_id, 'রড', Decimal('280.60'), 'কেজি', 'ROD-KSML-10M'),
        ('KSML ১২ মিলি রড', 'KSML', rod_cat_id, 'রড', Decimal('0.00'), 'কেজি', 'ROD-KSML-12M'),
        ('KSML ১৬ মিলি রড', 'KSML', rod_cat_id, 'রড', Decimal('492.00'), 'কেজি', 'ROD-KSML-16M'),
        ('KSML ২০ মিলি রড', 'KSML', rod_cat_id, 'রড', Decimal('817.70'), 'কেজি', 'ROD-KSML-20M'),

        # RINGS
        ('3-3 রিং', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('140.70'), 'কেজি', 'RING-3-3'),
        ('3-4 রিং', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('114.00'), 'কেজি', 'RING-3-4'),
        ('3-7 রিং', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('3.60'), 'কেজি', 'RING-3-7'),
        ('7-7 রিং', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('555.90'), 'কেজি', 'RING-7-7'),
        ('7-9 রিং', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('115.00'), 'কেজি', 'RING-7-9'),
        ('7-12 রিং', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('0.00'), 'কেজি', 'RING-7-12'),
        ('Pistol Ring', 'সাইট মেইড', ring_cat_id, 'রিং', Decimal('25.70'), 'কেজি', 'RING-PISTOL'),
    ]

    total_stock = Decimal('0.00')
    inserted_count = 0

    for name, brand, cat_id, cat_name, stock, unit, sku in items:
        total_stock += stock
        # Check if product already exists to avoid duplicates
        cur.execute("SELECT id FROM api_product WHERE name = %s;", (name,))
        existing = cur.fetchone()
        if existing:
            cur.execute("""
                UPDATE api_product 
                SET brand = %s, category_id = %s, category_name = %s, stock = %s, unit = %s, sku = %s, updated_at = NOW()
                WHERE id = %s;
            """, (brand, cat_id, cat_name, stock, unit, sku, existing[0]))
            print(f"Updated [{existing[0]}] {name} -> Stock: {stock} {unit}")
        else:
            cur.execute("""
                INSERT INTO api_product 
                (name, brand, category_id, category_name, stock, min_stock, unit, purchase_price, sell_price, sku, needs_price_review, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id;
            """, (name, brand, cat_id, cat_name, stock, Decimal('500.00'), unit, Decimal('0.00'), Decimal('0.00'), sku, False))
            p_id = cur.fetchone()[0]
            print(f"Inserted [{p_id}] {name} -> Stock: {stock} {unit}")
        inserted_count += 1

    conn.commit()
    print(f"\n--- SUCCESS ---")
    print(f"Total Products Handled: {inserted_count}")
    print(f"Total Hand In Stock: {total_stock} KG (Expected: 156,898.90 KG)")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
