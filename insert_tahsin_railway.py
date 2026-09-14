import psycopg2
from decimal import Decimal
from datetime import datetime, timezone
import json

DB_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Create or get customer 'তাহসিন ট্রেডার্স'
    customer_name = "তাহসিন ট্রেডার্স"
    address = "গোপালগঞ্জ"
    phone = "01700-000000"
    
    total_sales = Decimal('1385843.30')
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
            '2026-02-08'
        ))
        party_id = cur.fetchone()[0]
        print(f"Created customer ID: {party_id} -> {customer_name}")

    # Remove any existing transactions for this customer to ensure clean idempotent insert
    cur.execute("DELETE FROM api_transaction WHERE party_id = %s;", (party_id,))

    # -------------------------------------------------------------
    # 2. Transaction 1: Advance Payment (০৮-০২-২০২৬) = ১২,০০,০০০ ৳
    # -------------------------------------------------------------
    dt_pay1 = datetime(2026, 2, 8, 10, 0, 0, tzinfo=timezone.utc)
    notes_p1 = json.dumps({"isHistoricalLedger": True, "memoNo": "৫৩", "userNote": "অগ্রিম জমা"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'PAY-TT-0053-1',
        party_id,
        customer_name,
        phone,
        'payment_in',
        'completed',
        Decimal('1200000.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('1200000.00'),
        Decimal('1200000.00'),
        Decimal('0.00'),
        'cash',
        'pending',
        notes_p1,
        dt_pay1,
        dt_pay1
    ))
    p1_id = cur.fetchone()[0]
    print(f"Inserted Advance Payment (ID: {p1_id}) -> জমা: 12,00,000.00 ৳ (08-02-2026)")

    # -------------------------------------------------------------
    # 3. Transaction 2: Sale Invoice (১০-০২-২০২৬) = ১২,০৫,৫০০ ৳
    # -------------------------------------------------------------
    dt_sale1 = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
    notes_s1 = json.dumps({"isHistoricalLedger": True, "memoNo": "৫৩", "userNote": "মেমো নং ৫৩"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'INV-TT-0053-1',
        party_id,
        customer_name,
        phone,
        'sale',
        'completed',
        Decimal('1205500.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('1205500.00'),
        Decimal('0.00'),
        Decimal('1205500.00'),
        'cash',
        'pending',
        notes_s1,
        dt_sale1,
        dt_sale1
    ))
    s1_id = cur.fetchone()[0]

    # Items for Sale 1:
    items_s1 = [
        ('৮ মি: এস সি আর এম', Decimal('1000.00'), Decimal('81.30'), 'কেজি', Decimal('81300.00')),
        ('১০ মি: এস সি আর এম', Decimal('6000.00'), Decimal('80.30'), 'কেজি', Decimal('481800.00')),
        ('১২ মি: এস সি আর এম', Decimal('2000.00'), Decimal('80.30'), 'কেজি', Decimal('160600.00')),
        ('১৬ মি: এস সি আর এম', Decimal('4000.00'), Decimal('80.30'), 'কেজি', Decimal('321200.00')),
        ('২০ মি: এস সি আর এম', Decimal('2000.00'), Decimal('80.30'), 'কেজি', Decimal('160600.00')),
    ]
    for p_name, qty, rate, unit, tot in items_s1:
        cur.execute("""
            INSERT INTO api_transactionitem
            (transaction_id, product_name, quantity, price, unit, total)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (s1_id, p_name, qty, rate, unit, tot))
    print(f"Inserted Sale 1 (ID: {s1_id}) -> 5টি রড আইটেম মোট: 12,05,500.00 ৳ (10-02-2026)")

    # -------------------------------------------------------------
    # 4. Transaction 3: Payment (১১-০২-২০২৬) = ৫,৫০০ ৳
    # -------------------------------------------------------------
    dt_pay2 = datetime(2026, 2, 11, 10, 0, 0, tzinfo=timezone.utc)
    notes_p2 = json.dumps({"isHistoricalLedger": True, "memoNo": "৫৩", "userNote": "জমা"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'PAY-TT-0053-2',
        party_id,
        customer_name,
        phone,
        'payment_in',
        'completed',
        Decimal('5500.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('5500.00'),
        Decimal('5500.00'),
        Decimal('0.00'),
        'cash',
        'pending',
        notes_p2,
        dt_pay2,
        dt_pay2
    ))
    p2_id = cur.fetchone()[0]
    print(f"Inserted Payment 2 (ID: {p2_id}) -> জমা: 5,500.00 ৳ (11-02-2026)")

    # -------------------------------------------------------------
    # 5. Transaction 4: Sale Invoice (১২-০৯-২০২৬) = ১,৮০,৩৪৩.৩০ ৳
    # -------------------------------------------------------------
    dt_sale2 = datetime(2026, 9, 12, 11, 0, 0, tzinfo=timezone.utc)
    notes_s2 = json.dumps({"isHistoricalLedger": True, "memoNo": "৫৩", "userNote": "মেমো নং ৫৩"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'INV-TT-0053-2',
        party_id,
        customer_name,
        phone,
        'sale',
        'completed',
        Decimal('180343.30'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('180343.30'),
        Decimal('0.00'),
        Decimal('180343.30'),
        'cash',
        'pending',
        notes_s2,
        dt_sale2,
        dt_sale2
    ))
    s2_id = cur.fetchone()[0]

    # Items for Sale 2:
    items_s2 = [
        ('১০ মি: বি এস আর এম', Decimal('901.60'), Decimal('90.50'), 'কেজি', Decimal('81594.80')),
        ('০৮ মি: বি এস আর এম', Decimal('596.00'), Decimal('91.50'), 'কেজি', Decimal('54534.00')),
        ('৮ মি: এস সি আর এম', Decimal('514.30'), Decimal('85.00'), 'কেজি', Decimal('43715.50')),
        ('লেবারী', Decimal('1.00'), Decimal('499.00'), 'টি', Decimal('499.00')),
    ]
    for p_name, qty, rate, unit, tot in items_s2:
        cur.execute("""
            INSERT INTO api_transactionitem
            (transaction_id, product_name, quantity, price, unit, total)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (s2_id, p_name, qty, rate, unit, tot))
    print(f"Inserted Sale 2 (ID: {s2_id}) -> 3টি রড ও লেবারী মোট: 1,80,343.30 ৳ (12-09-2026)")

    # -------------------------------------------------------------
    # 6. Transaction 5: Payment (১২-০৯-২০২৬) = ১,৮০,৩০০ ৳
    # -------------------------------------------------------------
    dt_pay3 = datetime(2026, 9, 12, 12, 0, 0, tzinfo=timezone.utc)
    notes_p3 = json.dumps({"isHistoricalLedger": True, "memoNo": "৫৩", "userNote": "জমা"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'PAY-TT-0053-3',
        party_id,
        customer_name,
        phone,
        'payment_in',
        'completed',
        Decimal('180300.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('180300.00'),
        Decimal('180300.00'),
        Decimal('0.00'),
        'cash',
        'pending',
        notes_p3,
        dt_pay3,
        dt_pay3
    ))
    p3_id = cur.fetchone()[0]
    print(f"Inserted Payment 3 (ID: {p3_id}) -> জমা: 1,80,300.00 ৳ (12-09-2026)")

    # -------------------------------------------------------------
    # 7. Transaction 6: Payment (১৪-০৯-২০২৬) = ৪৩.৩০ ৳
    # -------------------------------------------------------------
    dt_pay4 = datetime(2026, 9, 14, 10, 0, 0, tzinfo=timezone.utc)
    notes_p4 = json.dumps({"isHistoricalLedger": True, "memoNo": "৫৩", "userNote": "জমা"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'PAY-TT-0053-4',
        party_id,
        customer_name,
        phone,
        'payment_in',
        'completed',
        Decimal('43.30'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('43.30'),
        Decimal('43.30'),
        Decimal('0.00'),
        'cash',
        'pending',
        notes_p4,
        dt_pay4,
        dt_pay4
    ))
    p4_id = cur.fetchone()[0]
    print(f"Inserted Payment 4 (ID: {p4_id}) -> জমা: 43.30 ৳ (14-09-2026)")

    conn.commit()
    print("\n--- TAHSIN TRADERS LEDGER IMPORT COMPLETED SUCCESSFULLY ---")

    # Verify final balance
    cur.execute("SELECT id, name, address, total_sales, total_due, advance_balance FROM api_party WHERE id = %s;", (party_id,))
    p = cur.fetchone()
    print(f"Party: {p[1]} (ID: {p[0]}) | Address: {p[2]} | Total Sales: ৳ {p[3]:,.2f} | Total Due: ৳ {p[4]:,.2f} | Advance: ৳ {p[5]:,.2f}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
