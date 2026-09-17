import sqlite3
import datetime
import json

conn = sqlite3.connect('db.sqlite3')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# Check if demo customer already exists
existing = cursor.execute("SELECT id FROM api_party WHERE name='শহিদুল ইসলাম ২ (সাইট ডেমো)'").fetchone()
if existing:
    cust_id = existing['id']
    print(f"Cleaning existing demo customer ID: {cust_id}")
    cursor.execute("DELETE FROM api_transactionitem WHERE transaction_id IN (SELECT id FROM api_transaction WHERE party_id=?)", (cust_id,))
    cursor.execute("DELETE FROM api_transaction WHERE party_id=?", (cust_id,))
    cursor.execute("DELETE FROM api_customersite WHERE customer_id=?", (cust_id,))
else:
    cursor.execute("""
        INSERT INTO api_party (
            party_type, name, customer_type, phone, country, division, district,
            address, id_type, opening_balance, credit_limit, credit_days, discount_percent,
            joined_date, created_at, updated_at, total_due, total_purchases, total_sales, advance_balance
        ) VALUES (
            'customer', 'শহিদুল ইসলাম ২ (সাইট ডেমো)', 'খুচরা গ্রাহক', '01712998877', 'বাংলাদেশ', 'ঢাকা', 'গোপালগঞ্জ',
            'মিয়াপাড়া মোড়, গোপালগঞ্জ', 'NID', 0, 0, 30, 0,
            '2026-09-01', now_str, now_str, 55000, 0, 127500, 0
        )
    """)
    cust_id = cursor.lastrowid
    print(f"Created new pure demo customer with ID: {cust_id}")

# 1. Create 2 Sites
cursor.execute("""
    INSERT INTO api_customersite (name, address, contact_person, contact_phone, created_at, updated_at, customer_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('মিয়াপাড়া সাইট', 'মিয়াপাড়া মোড়, গোপালগঞ্জ', 'রফিক মিস্ত্রি', '০১৭১১-২২৩৩৪৪', '2026-09-08 09:00:00', now_str, cust_id))
site1_id = cursor.lastrowid

cursor.execute("""
    INSERT INTO api_customersite (name, address, contact_person, contact_phone, created_at, updated_at, customer_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('বেদগ্রাম প্রজেক্ট', 'বেদগ্রাম বাসস্ট্যান্ড সংলগ্ন, গোপালগঞ্জ', 'শফিক কন্ট্রাক্টর', '০১৮১১-৫৫৬৬৭৭', '2026-09-08 09:30:00', now_str, cust_id))
site2_id = cursor.lastrowid

# 2. Site 1: Miapara Sale Invoice (75,500 total, 25,500 paid, 50,000 due)
meta_inv1 = json.dumps({
    "customerName": "শহিদুল ইসলাম ২ (সাইট ডেমো)",
    "siteName": "মিয়াপাড়া সাইট",
    "siteAddress": "মিয়াপাড়া মোড়, গোপালগঞ্জ",
    "siteContact": "রফিক মিস্ত্রি (০১৭১১-২২৩৩৪৪)",
    "paymentMethodName": "Cash"
}, ensure_ascii=False)
notes_inv1 = f"{meta_inv1}\n[মিয়াপাড়া সাইটের ১ম চালান মালামাল ডেলিভারি]"

cursor.execute("""
    INSERT INTO api_transaction (
        party_id, party_name, party_phone, transaction_type, status,
        subtotal, discount, tax, total_amount, paid_amount, due_amount,
        payment_method, cheque_status, invoice_no, site_name, site_address, site_contact,
        customer_site_id, notes, created_at, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?
    )
""", (
    cust_id, 'শহিদুল ইসলাম ২ (সাইট ডেমো)', '01712998877', 'sale', 'completed',
    75500, 0, 0, 75500, 25500, 50000,
    'cash', 'cleared', 'INV-2026-SITE-1', 'মিয়াপাড়া সাইট', 'মিয়াপাড়া মোড়, গোপালগঞ্জ', 'রফিক মিস্ত্রি (০১৭১১-২২৩৩৪৪)',
    site1_id, notes_inv1, '2026-09-10 10:30:00', now_str
))
tx1_id = cursor.lastrowid

cursor.execute("""
    INSERT INTO api_transactionitem (product_name, quantity, price, unit, total, product_id, transaction_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('16 মি.লি বি এস আর এম রড', 500, 98, 'কেজি', 49000, 22, tx1_id))

cursor.execute("""
    INSERT INTO api_transactionitem (product_name, quantity, price, unit, total, product_id, transaction_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('প্রিমিয়ার সিমেন্ট', 50, 530, 'ব্যাগ', 26500, None, tx1_id))

# 3. Site 1: Miapara Payment (20,000 paid)
meta_rcv1 = json.dumps({
    "partyId": cust_id,
    "partyName": "শহিদুল ইসলাম ২ (সাইট ডেমো)",
    "siteName": "মিয়াপাড়া সাইট",
    "paymentMethodName": "Bank",
    "bankName": "সোনালী ব্যাংক"
}, ensure_ascii=False)
notes_rcv1 = f"{meta_rcv1}\n[মিয়াপাড়া সাইটের জন্য ব্যাংক ডিপোজিটে জমা]"

cursor.execute("""
    INSERT INTO api_transaction (
        party_id, party_name, party_phone, transaction_type, status,
        subtotal, discount, tax, total_amount, paid_amount, due_amount,
        payment_method, cheque_status, invoice_no, site_name, site_address, site_contact,
        customer_site_id, notes, created_at, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?
    )
""", (
    cust_id, 'শহিদুল ইসলাম ২ (সাইট ডেমো)', '01712998877', 'payment_in', 'completed',
    0, 0, 0, 20000, 20000, 0,
    'bank', 'cleared', 'RCV-2026-SITE-1', 'মিয়াপাড়া সাইট', 'মিয়াপাড়া মোড়, গোপালগঞ্জ', 'রফিক মিস্ত্রি',
    site1_id, notes_rcv1, '2026-09-12 15:00:00', now_str
))

# 4. Site 2: Bedgram Sale Invoice (52,000 total, 12,000 paid, 40,000 due)
meta_inv2 = json.dumps({
    "customerName": "শহিদুল ইসলাম ২ (সাইট ডেমো)",
    "siteName": "বেদগ্রাম প্রজেক্ট",
    "siteAddress": "বেদগ্রাম বাসস্ট্যান্ড সংলগ্ন, গোপালগঞ্জ",
    "siteContact": "শফিক কন্ট্রাক্টর (০১৮১১-৫৫৬৬৭৭)",
    "paymentMethodName": "Cash"
}, ensure_ascii=False)
notes_inv2 = f"{meta_inv2}\n[বেদগ্রাম প্রজেক্টে সিমেন্ট সরবরাহ]"

cursor.execute("""
    INSERT INTO api_transaction (
        party_id, party_name, party_phone, transaction_type, status,
        subtotal, discount, tax, total_amount, paid_amount, due_amount,
        payment_method, cheque_status, invoice_no, site_name, site_address, site_contact,
        customer_site_id, notes, created_at, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?
    )
""", (
    cust_id, 'শহিদুল ইসলাম ২ (সাইট ডেমো)', '01712998877', 'sale', 'completed',
    52000, 0, 0, 52000, 12000, 40000,
    'cash', 'cleared', 'INV-2026-SITE-2', 'বেদগ্রাম প্রজেক্ট', 'বেদগ্রাম বাসস্ট্যান্ড সংলগ্ন, গোপালগঞ্জ', 'শফিক কন্ট্রাক্টর (০১৮১১-৫৫৬৬৭৭)',
    site2_id, notes_inv2, '2026-09-14 11:15:00', now_str
))
tx2_id = cursor.lastrowid

cursor.execute("""
    INSERT INTO api_transactionitem (product_name, quantity, price, unit, total, product_id, transaction_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('ফ্রেশ সুপার সিমেন্ট', 100, 520, 'ব্যাগ', 52000, None, tx2_id))

# 5. Site 2: Bedgram Payment (15,000 paid)
meta_rcv2 = json.dumps({
    "partyId": cust_id,
    "partyName": "শহিদুল ইসলাম ২ (সাইট ডেমো)",
    "siteName": "বেদগ্রাম প্রজেক্ট",
    "paymentMethodName": "Cash"
}, ensure_ascii=False)
notes_rcv2 = f"{meta_rcv2}\n[বেদগ্রাম প্রজেক্টের সাইট থেকে নগদ কালেকশন]"

cursor.execute("""
    INSERT INTO api_transaction (
        party_id, party_name, party_phone, transaction_type, status,
        subtotal, discount, tax, total_amount, paid_amount, due_amount,
        payment_method, cheque_status, invoice_no, site_name, site_address, site_contact,
        customer_site_id, notes, created_at, updated_at
    ) VALUES (
        ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?, ?, ?,
        ?, ?, ?, ?
    )
""", (
    cust_id, 'শহিদুল ইসলাম ২ (সাইট ডেমো)', '01712998877', 'payment_in', 'completed',
    0, 0, 0, 15000, 15000, 0,
    'cash', 'cleared', 'RCV-2026-SITE-2', 'বেদগ্রাম প্রজেক্ট', 'বেদগ্রাম বাসস্ট্যান্ড সংলগ্ন, গোপালগঞ্জ', 'শফিক কন্ট্রাক্টর',
    site2_id, notes_rcv2, '2026-09-16 16:45:00', now_str
))

# Update Party total_due
cursor.execute("UPDATE api_party SET total_due=55000, total_sales=127500 WHERE id=?", (cust_id,))

conn.commit()
conn.close()
print(f"✓ Pure demo customer ready! Customer ID: {cust_id}")
print(f"  - মিয়াপাড়া সাইট: বকেয়া ৳৩০,০০০")
print(f"  - বেদগ্রাম প্রজেক্ট: বকেয়া ৳২৫,০০০")
print(f"  - সব সাইট (একত্রিত): বকেয়া ঠিক ৳৫৫,০০০")
