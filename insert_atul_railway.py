import psycopg2
from decimal import Decimal
from datetime import datetime, timezone
import json

DB_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Customer: অতুল স্যার
    customer_name = "অতুল স্যার"
    address = "মেডিকেল"
    phone = "01700-000000"
    
    total_sales = Decimal('284158.30')
    total_due = Decimal('0.00')
    advance_bal = Decimal('0.00')

    cur.execute("SELECT id FROM api_party WHERE name = %s;", (customer_name,))
    row = cur.fetchone()
    if row:
        party_id = row[0]
        cur.execute("""
            UPDATE api_party 
            SET address = %s, total_sales = %s, total_due = %s, advance_balance = %s, updated_at = NOW()
            WHERE id = %s;
        """, (address, total_sales, total_due, advance_bal, party_id))
        print(f"Updated existing customer ID: {party_id}")
    else:
        cur.execute("""
            INSERT INTO api_party 
            (name, address, phone, party_type, opening_balance, total_sales, total_purchases, total_due, advance_balance, customer_type, country, division, district, id_type, credit_limit, credit_days, discount_percent, joined_date, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id;
        """, (
            customer_name, 
            address, 
            phone, 
            'customer', 
            Decimal('0.00'), 
            total_sales, 
            Decimal('0.00'),
            total_due, 
            advance_bal,
            'খুচরা গ্রাহক',
            'বাংলাদেশ',
            'ঢাকা',
            'গোপালগঞ্জ',
            'NID',
            Decimal('0.00'),
            30,
            Decimal('0.00'),
            '2026-06-26'
        ))
        party_id = cur.fetchone()[0]
        print(f"Created customer ID: {party_id} -> {customer_name}")

    # Remove any existing transactions for this customer to ensure clean idempotent insert
    cur.execute("DELETE FROM api_transaction WHERE party_id = %s;", (party_id,))

    def insert_payment(inv_no, amount, dt, note_text):
        notes_payload = json.dumps({"isHistoricalLedger": True, "memoNo": "৯৫", "userNote": note_text}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO api_transaction
            (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            inv_no,
            party_id,
            customer_name,
            phone,
            'payment_in',
            'completed',
            amount,
            Decimal('0.00'),
            Decimal('0.00'),
            amount,
            amount,
            Decimal('0.00'),
            'cash',
            'pending',
            notes_payload,
            dt,
            dt
        ))
        return cur.fetchone()[0]

    def insert_sale(inv_no, subtotal, dt, note_text, items):
        notes_payload = json.dumps({"isHistoricalLedger": True, "memoNo": "৯৫", "userNote": note_text}, ensure_ascii=False)
        cur.execute("""
            INSERT INTO api_transaction
            (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
        """, (
            inv_no,
            party_id,
            customer_name,
            phone,
            'sale',
            'completed',
            subtotal,
            Decimal('0.00'),
            Decimal('0.00'),
            subtotal,
            Decimal('0.00'),
            subtotal,
            'cash',
            'pending',
            notes_payload,
            dt,
            dt
        ))
        tx_id = cur.fetchone()[0]

        for p_name, qty, rate, unit, tot in items:
            cur.execute("""
                INSERT INTO api_transactionitem
                (transaction_id, product_name, quantity, price, unit, total)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (tx_id, p_name, qty, rate, unit, tot))

        return tx_id

    # 1. Payment: 26-06-2026 (34,000)
    p1 = insert_payment('PAY-AS-0095-1', Decimal('34000.00'), datetime(2026, 6, 26, 10, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 1 (ID: {p1}) -> 34,000 ৳ (26-06-2026)")

    # 2. Payment: 28-06-2026 (20,000)
    p2 = insert_payment('PAY-AS-0095-2', Decimal('20000.00'), datetime(2026, 6, 28, 10, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 2 (ID: {p2}) -> 20,000 ৳ (28-06-2026)")

    # 3. Sale 1: 30-06-2026 (54,000)
    s1_items = [
        ('সুপারক্রিট সিমেন্ট', Decimal('100.00'), Decimal('540.00'), 'বস্তা', Decimal('54000.00'))
    ]
    s1 = insert_sale('INV-AS-0095-1', Decimal('54000.00'), datetime(2026, 6, 30, 11, 0, tzinfo=timezone.utc), 'মেমো নং ৯৫', s1_items)
    print(f"Inserted Sale 1 (ID: {s1}) -> 54,000 ৳ (30-06-2026)")

    # 4. Payment: 30-06-2026 (1,20,000)
    p3 = insert_payment('PAY-AS-0095-3', Decimal('120000.00'), datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 3 (ID: {p3}) -> 1,20,000 ৳ (30-06-2026)")

    # 5. Sale 2: 03-08-2026 (1,36,595.20)
    s2_items = [
        ('১২মি: এস সি আর এম থ্যারমেক্স', Decimal('146.30'), Decimal('88.00'), 'কেজি', Decimal('12874.40')),
        ('৮মি: এস সি আর এম থ্যারমেক্স', Decimal('148.90'), Decimal('88.00'), 'কেজি', Decimal('13103.20')),
        ('১০মি: এস সি আর এম থ্যারমেক্স', Decimal('644.50'), Decimal('88.00'), 'কেজি', Decimal('56716.00')),
        ('১৬মি: এস সি আর এম থ্যারমেক্স', Decimal('600.20'), Decimal('88.00'), 'কেজি', Decimal('52817.60')),
        ('লেবারী', Decimal('1.00'), Decimal('384.00'), 'টি', Decimal('384.00')),
        ('ভাড়া', Decimal('1.00'), Decimal('700.00'), 'টি', Decimal('700.00')),
    ]
    s2 = insert_sale('INV-AS-0095-2', Decimal('136595.20'), datetime(2026, 8, 3, 11, 0, tzinfo=timezone.utc), 'মেমো নং ৯৫', s2_items)
    print(f"Inserted Sale 2 (ID: {s2}) -> 1,36,595.20 ৳ (03-08-2026)")

    # 6. Payment: 03-08-2026 (16,550)
    p4 = insert_payment('PAY-AS-0095-4', Decimal('16550.00'), datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 4 (ID: {p4}) -> 16,550 ৳ (03-08-2026)")

    # 7. Payment: 12-08-2026 (78,000)
    p5 = insert_payment('PAY-AS-0095-5', Decimal('78000.00'), datetime(2026, 8, 12, 10, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 5 (ID: {p5}) -> 78,000 ৳ (12-08-2026)")

    # 8. Sale 3: 15-08-2026 (87,378.10)
    s3_items = [
        ('সুপারক্রিট সিমেন্ট', Decimal('100.00'), Decimal('540.00'), 'বস্তা', Decimal('54000.00')),
        ('১৬মি: এস সি আর এম থ্যারমেক্স', Decimal('111.90'), Decimal('84.50'), 'কেজি', Decimal('9455.55')),
        ('১২মি: এস সি আর এম থ্যারমেক্স', Decimal('71.70'), Decimal('84.50'), 'কেজি', Decimal('6058.65')),
        ('৮মি: এস সি আর এম থ্যারমেক্স', Decimal('207.80'), Decimal('85.50'), 'কেজি', Decimal('17766.90')),
        ('লেবারী', Decimal('1.00'), Decimal('97.00'), 'টি', Decimal('97.00')),
    ]
    s3 = insert_sale('INV-AS-0095-3', Decimal('87378.10'), datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc), 'মেমো নং ৯৫', s3_items)
    print(f"Inserted Sale 3 (ID: {s3}) -> 87,378.10 ৳ (15-08-2026)")

    # 9. Payment: 15-08-2026 (9,350)
    p6 = insert_payment('PAY-AS-0095-6', Decimal('9350.00'), datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 6 (ID: {p6}) -> 9,350 ৳ (15-08-2026)")

    # 10. Sale 4: 24-08-2026 (6,185)
    s4_items = [
        ('১০মি: এস সি আর এম থ্যারমেক্স', Decimal('71.40'), Decimal('85.00'), 'কেজি', Decimal('6069.00')),
        ('লেবারী', Decimal('1.00'), Decimal('16.00'), 'টি', Decimal('16.00')),
        ('ভাড়া', Decimal('1.00'), Decimal('100.00'), 'টি', Decimal('100.00')),
    ]
    s4 = insert_sale('INV-AS-0095-4', Decimal('6185.00'), datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc), 'মেমো নং ৯৫', s4_items)
    print(f"Inserted Sale 4 (ID: {s4}) -> 6,185 ৳ (24-08-2026)")

    # 11. Payment: 25-08-2026 (6,185)
    p7 = insert_payment('PAY-AS-0095-7', Decimal('6185.00'), datetime(2026, 8, 25, 10, 0, tzinfo=timezone.utc), 'জমা')
    print(f"Inserted Payment 7 (ID: {p7}) -> 6,185 ৳ (25-08-2026)")

    # 12. Payment: 14-09-2026 (73.30)
    p8 = insert_payment('PAY-AS-0095-8', Decimal('73.30'), datetime(2026, 9, 14, 10, 0, tzinfo=timezone.utc), 'জমা (অবশিষ্ট ক্লোজিং)')
    print(f"Inserted Payment 8 (ID: {p8}) -> 73.30 ৳ (14-09-2026)")

    conn.commit()
    print("\n--- ATUL SIR LEDGER IMPORT COMPLETED SUCCESSFULLY ---")

    # Verify final balance
    cur.execute("SELECT id, name, address, total_sales, total_due, advance_balance FROM api_party WHERE id = %s;", (party_id,))
    p = cur.fetchone()
    print(f"Party: {p[1]} (ID: {p[0]}) | Address: {p[2]} | Total Sales: ৳ {p[3]:,.2f} | Total Due: ৳ {p[4]:,.2f} | Advance: ৳ {p[5]:,.2f}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
