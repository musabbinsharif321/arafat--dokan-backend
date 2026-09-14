import psycopg2
from decimal import Decimal
from datetime import datetime, timezone
import json

DB_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 1. Customer: সজিব
    customer_name = "সজিব"
    address = "মিয়াপাড়া"
    phone = "01700-000000"
    
    total_sales = Decimal('671160.00')
    total_due = Decimal('6310.00')
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
            '2026-01-02'
        ))
        party_id = cur.fetchone()[0]
        print(f"Created customer ID: {party_id} -> {customer_name}")

    # Remove any existing transactions for this customer to ensure clean idempotent insert
    cur.execute("DELETE FROM api_transaction WHERE party_id = %s;", (party_id,))

    def insert_payment(inv_no, amount, dt, note_text):
        notes_payload = json.dumps({"isHistoricalLedger": True, "memoNo": "২৬", "userNote": note_text}, ensure_ascii=False)
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
        notes_payload = json.dumps({"isHistoricalLedger": True, "memoNo": "২৬", "userNote": note_text}, ensure_ascii=False)
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

    # 1. Advance Payment: 02-01-2026 (50,000)
    insert_payment('PAY-SJ-0026-01', Decimal('50000.00'), datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc), 'অগ্রিম জমা')

    # 2. Sale: 10-01-2026 (6,200)
    insert_sale('INV-SJ-0026-01', Decimal('6200.00'), datetime(2026, 1, 10, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('620.00'), 'বস্তা', Decimal('6200.00'))
    ])

    # 3. Sale: 11-01-2026 (6,200)
    insert_sale('INV-SJ-0026-02', Decimal('6200.00'), datetime(2026, 1, 11, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('620.00'), 'বস্তা', Decimal('6200.00'))
    ])

    # 4. Sale: 13-01-2026 (12,400)
    insert_sale('INV-SJ-0026-03', Decimal('12400.00'), datetime(2026, 1, 13, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('20.00'), Decimal('620.00'), 'বস্তা', Decimal('12400.00'))
    ])

    # 5. Sale: 16-01-2026 (43,400)
    insert_sale('INV-SJ-0026-04', Decimal('43400.00'), datetime(2026, 1, 16, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('70.00'), Decimal('620.00'), 'বস্তা', Decimal('43400.00'))
    ])

    # 6. Payment: 16-01-2026 (18,200)
    insert_payment('PAY-SJ-0026-02', Decimal('18200.00'), datetime(2026, 1, 16, 12, 0, tzinfo=timezone.utc), 'জমা')

    # 7. Sale: 24-01-2026 (55,800)
    insert_sale('INV-SJ-0026-05', Decimal('55800.00'), datetime(2026, 1, 24, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('90.00'), Decimal('620.00'), 'বস্তা', Decimal('55800.00'))
    ])

    # 8. Payment: 25-01-2026 (55,800)
    insert_payment('PAY-SJ-0026-03', Decimal('55800.00'), datetime(2026, 1, 25, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 9. Sale: 06-02-2026 (12,400)
    insert_sale('INV-SJ-0026-06', Decimal('12400.00'), datetime(2026, 2, 6, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('20.00'), Decimal('620.00'), 'বস্তা', Decimal('12400.00'))
    ])

    # 10. Sale: 10-02-2026 (24,800) - 20+20 bags
    insert_sale('INV-SJ-0026-07', Decimal('24800.00'), datetime(2026, 2, 10, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('20.00'), Decimal('620.00'), 'বস্তা', Decimal('12400.00')),
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('20.00'), Decimal('620.00'), 'বস্তা', Decimal('12400.00'))
    ])

    # 11. Payment: 10-02-2026 (20,800)
    insert_payment('PAY-SJ-0026-04', Decimal('20800.00'), datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc), 'জমা')

    # 12. Payment: 10-02-2026 (16,400)
    insert_payment('PAY-SJ-0026-05', Decimal('16400.00'), datetime(2026, 2, 10, 13, 0, tzinfo=timezone.utc), 'জমা')

    # 13. Sale: 19-02-2026 (12,400)
    insert_sale('INV-SJ-0026-08', Decimal('12400.00'), datetime(2026, 2, 19, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('20.00'), Decimal('620.00'), 'বস্তা', Decimal('12400.00'))
    ])

    # 14. Sale: 22-02-2026 (12,400)
    insert_sale('INV-SJ-0026-09', Decimal('12400.00'), datetime(2026, 2, 22, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('20.00'), Decimal('620.00'), 'বস্তা', Decimal('12400.00'))
    ])

    # 15. Payment: 26-02-2026 (24,800)
    insert_payment('PAY-SJ-0026-06', Decimal('24800.00'), datetime(2026, 2, 26, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 16. Sale: 01-03-2026 (6,200)
    insert_sale('INV-SJ-0026-10', Decimal('6200.00'), datetime(2026, 3, 1, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('620.00'), 'বস্তা', Decimal('6200.00'))
    ])

    # 17. Payment: 02-03-2026 (6,200)
    insert_payment('PAY-SJ-0026-07', Decimal('6200.00'), datetime(2026, 3, 2, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 18. Sale: 07-03-2026 (2,17,000)
    insert_sale('INV-SJ-0026-11', Decimal('217000.00'), datetime(2026, 3, 7, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('350.00'), Decimal('620.00'), 'বস্তা', Decimal('217000.00'))
    ])

    # 19. Payment: 07-03-2026 (1,00,000)
    insert_payment('PAY-SJ-0026-08', Decimal('100000.00'), datetime(2026, 3, 7, 12, 0, tzinfo=timezone.utc), 'জমা')

    # 20. Payment: 08-03-2026 (1,17,000)
    insert_payment('PAY-SJ-0026-09', Decimal('117000.00'), datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 21. Sale: 19-06-2026 (6,300)
    insert_sale('INV-SJ-0026-12', Decimal('6300.00'), datetime(2026, 6, 19, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 22. Payment: 19-06-2026 (100)
    insert_payment('PAY-SJ-0026-10', Decimal('100.00'), datetime(2026, 6, 19, 12, 0, tzinfo=timezone.utc), 'জমা')

    # 23. Sale: 21-06-2026 (6,300)
    insert_sale('INV-SJ-0026-13', Decimal('6300.00'), datetime(2026, 6, 21, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 24. Payment: 22-06-2026 (12,500)
    insert_payment('PAY-SJ-0026-11', Decimal('12500.00'), datetime(2026, 6, 22, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 25. Sale: 02-07-2026 (44,100) - 60+10 bags
    insert_sale('INV-SJ-0026-14', Decimal('44100.00'), datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('60.00'), Decimal('630.00'), 'বস্তা', Decimal('37800.00')),
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 26. Payment: 03-07-2026 (44,000)
    insert_payment('PAY-SJ-0026-12', Decimal('44000.00'), datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 27. Sale: 06-07-2026 (6,300)
    insert_sale('INV-SJ-0026-15', Decimal('6300.00'), datetime(2026, 7, 6, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 28. Sale: 12-07-2026 (6,300)
    insert_sale('INV-SJ-0026-16', Decimal('6300.00'), datetime(2026, 7, 12, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 29. Sale: 15-07-2026 (1,00,800) - 150+10 bags
    insert_sale('INV-SJ-0026-17', Decimal('100800.00'), datetime(2026, 7, 15, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('150.00'), Decimal('630.00'), 'বস্তা', Decimal('94500.00')),
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 30. Payment: 17-07-2026 (1,13,500)
    insert_payment('PAY-SJ-0026-13', Decimal('113500.00'), datetime(2026, 7, 17, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 31. Sale: 21-07-2026 (4,410)
    insert_sale('INV-SJ-0026-18', Decimal('4410.00'), datetime(2026, 7, 21, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('7.00'), Decimal('630.00'), 'বস্তা', Decimal('4410.00'))
    ])

    # 32. Sale: 22-07-2026 (5,550) - 10 bags holcim + 150 transport
    insert_sale('INV-SJ-0026-19', Decimal('5550.00'), datetime(2026, 7, 22, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('হোলসিম স্ট্রং স্ট্রাকচার', Decimal('10.00'), Decimal('540.00'), 'বস্তা', Decimal('5400.00')),
        ('ভাড়া', Decimal('1.00'), Decimal('150.00'), 'টি', Decimal('150.00'))
    ])

    # 33. Sale: 26-07-2026 (6,300)
    insert_sale('INV-SJ-0026-20', Decimal('6300.00'), datetime(2026, 7, 26, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 34. Sale: 28-07-2026 (6,300)
    insert_sale('INV-SJ-0026-21', Decimal('6300.00'), datetime(2026, 7, 28, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 35. Payment: 28-07-2026 (22,550)
    insert_payment('PAY-SJ-0026-14', Decimal('22550.00'), datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc), 'জমা')

    # ---------------- PAGE 2 ----------------
    # 36. Sale: 31-07-2026 (6,300)
    insert_sale('INV-SJ-0026-22', Decimal('6300.00'), datetime(2026, 7, 31, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 37. Sale: 08-08-2026 (6,300)
    insert_sale('INV-SJ-0026-23', Decimal('6300.00'), datetime(2026, 8, 8, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 38. Sale: 11-08-2026 (6,300)
    insert_sale('INV-SJ-0026-24', Decimal('6300.00'), datetime(2026, 8, 11, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 39. Sale: 13-08-2026 (6,300)
    insert_sale('INV-SJ-0026-25', Decimal('6300.00'), datetime(2026, 8, 13, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 40. Sale: 15-08-2026 (6,300)
    insert_sale('INV-SJ-0026-26', Decimal('6300.00'), datetime(2026, 8, 15, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 41. Sale: 21-08-2026 (6,300)
    insert_sale('INV-SJ-0026-27', Decimal('6300.00'), datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 42. Sale: 24-08-2026 (6,300)
    insert_sale('INV-SJ-0026-28', Decimal('6300.00'), datetime(2026, 8, 24, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 43. Sale: 30-08-2026 (6,300)
    insert_sale('INV-SJ-0026-29', Decimal('6300.00'), datetime(2026, 8, 30, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 44. Sale: 03-09-2026 (6,300)
    insert_sale('INV-SJ-0026-30', Decimal('6300.00'), datetime(2026, 9, 3, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 45. Sale: 05-09-2026 (6,300)
    insert_sale('INV-SJ-0026-31', Decimal('6300.00'), datetime(2026, 9, 5, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    # 46. Payment: 06-09-2026 (63,000)
    insert_payment('PAY-SJ-0026-15', Decimal('63000.00'), datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc), 'জমা')

    # 47. Sale: 10-09-2026 (6,300)
    insert_sale('INV-SJ-0026-32', Decimal('6300.00'), datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc), 'মেমো নং ২৬', [
        ('কোস্টাল গার্ড সিমেন্ট', Decimal('10.00'), Decimal('630.00'), 'বস্তা', Decimal('6300.00'))
    ])

    conn.commit()
    print("\n--- SAJIB LEDGER IMPORT COMPLETED SUCCESSFULLY ---")

    # Verify final balance
    cur.execute("SELECT id, name, address, total_sales, total_due, advance_balance FROM api_party WHERE id = %s;", (party_id,))
    p = cur.fetchone()
    print(f"Party: {p[1]} (ID: {p[0]}) | Address: {p[2]} | Total Sales: ৳ {p[3]:,.2f} | Total Due: ৳ {p[4]:,.2f} | Advance: ৳ {p[5]:,.2f}")

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
