import psycopg2
from decimal import Decimal
from datetime import datetime, timezone
import json

DB_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Create or get customer 'নিরঞ্জন মজুমদার'
    customer_name = "নিরঞ্জন মজুমদার"
    address = "বাঘাযুড়"
    phone = "01700-000000"
    
    cur.execute("SELECT id FROM api_party WHERE name = %s;", (customer_name,))
    row = cur.fetchone()
    if row:
        party_id = row[0]
        cur.execute("""
            UPDATE api_party 
            SET address = %s, total_sales = %s, total_due = %s, advance_balance = %s, updated_at = NOW()
            WHERE id = %s;
        """, (address, Decimal('12000.00'), Decimal('11000.00'), Decimal('0.00'), party_id))
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
            Decimal('12000.00'), 
            Decimal('0.00'),
            Decimal('11000.00'), 
            Decimal('0.00'),
            'খুচরা গ্রাহক',
            'বাংলাদেশ',
            'ঢাকা',
            'গোপালগঞ্জ',
            'NID',
            Decimal('0.00'),
            30,
            Decimal('0.00'),
            '2026-08-27'
        ))
        party_id = cur.fetchone()[0]
        print(f"Created customer ID: {party_id} -> {customer_name}")

    # Remove any existing transactions for this customer to ensure clean idempotent insert
    cur.execute("DELETE FROM api_transaction WHERE party_id = %s;", (party_id,))

    # 2. Transaction 1: Sale on 27-08-2026
    dt1 = datetime(2026, 8, 27, 10, 0, 0, tzinfo=timezone.utc)
    notes_sale1 = json.dumps({"isHistoricalLedger": True, "memoNo": "১৩৪", "userNote": "মেমো নং ১৩৪"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'INV-NM-0134-1',
        party_id,
        customer_name,
        phone,
        'sale',
        'completed',
        Decimal('6000.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('6000.00'),
        Decimal('0.00'),
        Decimal('6000.00'),
        'cash',
        'pending',
        notes_sale1,
        dt1,
        dt1
    ))
    tx1_id = cur.fetchone()[0]

    # Item for Transaction 1: 10 bags Coastal Guard Cement @ 600
    cur.execute("""
        INSERT INTO api_transactionitem
        (transaction_id, product_name, quantity, price, unit, total)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (tx1_id, 'কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('600.00'), 'বস্তা', Decimal('6000.00')))
    print(f"Inserted Sale 1 (ID: {tx1_id}) -> 10 বস্তা কোস্টাল গার্ড সিমেন্ট @ 600 = 6,000")

    # 3. Transaction 2: Payment In (জমা) on 27-08-2026
    dt_pay = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
    notes_pay = json.dumps({"isHistoricalLedger": True, "memoNo": "১৩৪", "userNote": "জমা"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'PAY-NM-0134',
        party_id,
        customer_name,
        phone,
        'payment_in',
        'completed',
        Decimal('1000.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('1000.00'),
        Decimal('1000.00'),
        Decimal('0.00'),
        'cash',
        'pending',
        notes_pay,
        dt_pay,
        dt_pay
    ))
    tx2_id = cur.fetchone()[0]
    print(f"Inserted Payment (ID: {tx2_id}) -> জমা: 1,000.00 ৳")

    # 4. Transaction 3: Sale on 06-09-2026
    dt2 = datetime(2026, 9, 6, 10, 0, 0, tzinfo=timezone.utc)
    notes_sale2 = json.dumps({"isHistoricalLedger": True, "memoNo": "১৩৪", "userNote": "মেমো নং ১৩৪"}, ensure_ascii=False)
    cur.execute("""
        INSERT INTO api_transaction
        (invoice_no, party_id, party_name, party_phone, transaction_type, status, subtotal, discount, tax, total_amount, paid_amount, due_amount, payment_method, cheque_status, notes, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        'INV-NM-0134-2',
        party_id,
        customer_name,
        phone,
        'sale',
        'completed',
        Decimal('6000.00'),
        Decimal('0.00'),
        Decimal('0.00'),
        Decimal('6000.00'),
        Decimal('0.00'),
        Decimal('6000.00'),
        'cash',
        'pending',
        notes_sale2,
        dt2,
        dt2
    ))
    tx3_id = cur.fetchone()[0]

    # Item for Transaction 3: 10 bags Coastal Guard Cement @ 600
    cur.execute("""
        INSERT INTO api_transactionitem
        (transaction_id, product_name, quantity, price, unit, total)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (tx3_id, 'কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('600.00'), 'বস্তা', Decimal('6000.00')))
    print(f"Inserted Sale 2 (ID: {tx3_id}) -> 10 বস্তা কোস্টাল গার্ড সিমেন্ট @ 600 = 6,000")

    conn.commit()
    print("\n--- NIRANJAN MAJUMDAR LEDGER IMPORT COMPLETED SUCCESSFULLY ---")

    # Verify final balance
    cur.execute("SELECT id, name, address, total_sales, total_due, advance_balance FROM api_party WHERE id = %s;", (party_id,))
    p = cur.fetchone()
    print(f"Party: {p[1]} (ID: {p[0]}) | Address: {p[2]} | Total Sales: ৳ {p[3]:,.2f} | Total Due: ৳ {p[4]:,.2f}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
