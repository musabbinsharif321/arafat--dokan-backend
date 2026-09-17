import sqlite3
import datetime
import json

conn = sqlite3.connect('db.sqlite3')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Customer ID 16: নজরুল ইসলাম
cust_id = 16
cust = cursor.execute("SELECT * FROM api_party WHERE id=?", (cust_id,)).fetchone()
if not cust:
    print(f"Customer {cust_id} not found!")
    conn.close()
    exit(1)

print(f"Adding demo sites and ledger for customer: {cust['name']} (ID: {cust_id})")

now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 1. Clean existing demo transactions & sites if previously created
existing_site_names = ['মিয়াপাড়া সাইট', 'বেদগ্রাম প্রজেক্ট']
cursor.execute("DELETE FROM api_transactionitem WHERE transaction_id IN (SELECT id FROM api_transaction WHERE invoice_no IN ('INV-2026-9011', 'RCV-2026-9012', 'INV-2026-9021', 'RCV-2026-9022'))")
cursor.execute("DELETE FROM api_transaction WHERE invoice_no IN ('INV-2026-9011', 'RCV-2026-9012', 'INV-2026-9021', 'RCV-2026-9022')")
cursor.execute("DELETE FROM api_customersite WHERE customer_id=? AND name IN (?, ?)", (cust_id, 'মিয়াপাড়া সাইট', 'বেদগ্রাম প্রজেক্ট'))

# 2. Insert Sites
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

print(f"✓ Created Site 1: মিয়াপাড়া সাইট (ID: {site1_id})")
print(f"✓ Created Site 2: বেদগ্রাম প্রজেক্ট (ID: {site2_id})")

# 3. Insert Site 1: Sale Invoice (INV-2026-9011)
meta_inv1 = json.dumps({
    "customerName": cust['name'],
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
    cust_id, cust['name'], cust['phone'], 'sale', 'completed',
    75500, 0, 0, 75500, 25500, 50000,
    'cash', 'cleared', 'INV-2026-9011', 'মিয়াপাড়া সাইট', 'মিয়াপাড়া মোড়, গোপালগঞ্জ', 'রফিক মিস্ত্রি (০১৭১১-২২৩৩৪৪)',
    site1_id, notes_inv1, '2026-09-10 10:30:00', now_str
))
tx1_id = cursor.lastrowid

# Items for Invoice 1
cursor.execute("""
    INSERT INTO api_transactionitem (product_name, quantity, price, unit, total, product_id, transaction_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('16 মি.লি বি এস আর এম রড', 500, 98, 'কেজি', 49000, 22, tx1_id))

cursor.execute("""
    INSERT INTO api_transactionitem (product_name, quantity, price, unit, total, product_id, transaction_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('প্রিমিয়ার সিমেন্ট', 50, 530, 'ব্যাগ', 26500, None, tx1_id))

print(f"✓ Created Sale Invoice 1 (INV-2026-9011) for মিয়াপাড়া সাইট (মোট: ৳৭৫,৫০০, জমা: ৳২৫,৫০০, বাকি: ৳৫০,০০০)")

# 4. Insert Site 1: Payment In (RCV-2026-9012)
meta_rcv1 = json.dumps({
    "partyId": cust_id,
    "partyName": cust['name'],
    "siteName": "মিয়াপাড়া সাইট",
    "paymentMethodName": "Bank",
    "bankName": "সোনালী ব্যাংক",
    "userNote": "মিয়াপাড়া সাইটের কাজের জন্য ব্যাংক ডিপোজিট"
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
    cust_id, cust['name'], cust['phone'], 'payment_in', 'completed',
    0, 0, 0, 20000, 20000, 0,
    'bank', 'cleared', 'RCV-2026-9012', 'মিয়াপাড়া সাইট', 'মিয়াপাড়া মোড়, গোপালগঞ্জ', 'রফিক মিস্ত্রি',
    site1_id, notes_rcv1, '2026-09-12 15:00:00', now_str
))
print(f"✓ Created Payment 1 (RCV-2026-9012) for মিয়াপাড়া সাইট (জমা: ৳২০,০০০ ব্যাংক)")

# 5. Insert Site 2: Sale Invoice (INV-2026-9021)
meta_inv2 = json.dumps({
    "customerName": cust['name'],
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
    cust_id, cust['name'], cust['phone'], 'sale', 'completed',
    52000, 0, 0, 52000, 12000, 40000,
    'cash', 'cleared', 'INV-2026-9021', 'বেদগ্রাম প্রজেক্ট', 'বেদগ্রাম বাসস্ট্যান্ড সংলগ্ন, গোপালগঞ্জ', 'শফিক কন্ট্রাক্টর (০১৮১১-৫৫৬৬৭৭)',
    site2_id, notes_inv2, '2026-09-14 11:15:00', now_str
))
tx2_id = cursor.lastrowid

cursor.execute("""
    INSERT INTO api_transactionitem (product_name, quantity, price, unit, total, product_id, transaction_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('ফ্রেশ সুপার সিমেন্ট', 100, 520, 'ব্যাগ', 52000, None, tx2_id))

print(f"✓ Created Sale Invoice 2 (INV-2026-9021) for বেদগ্রাম প্রজেক্ট (মোট: ৳৫২,০০০, জমা: ৳১২,০০০, বাকি: ৳৪০,০০০)")

# 6. Insert Site 2: Payment In (RCV-2026-9022)
meta_rcv2 = json.dumps({
    "partyId": cust_id,
    "partyName": cust['name'],
    "siteName": "বেদগ্রাম প্রজেক্ট",
    "paymentMethodName": "Cash",
    "userNote": "বেদগ্রাম প্রজেক্টের সাইট থেকে নগদ কালেকশন"
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
    cust_id, cust['name'], cust['phone'], 'payment_in', 'completed',
    0, 0, 0, 15000, 15000, 0,
    'cash', 'cleared', 'RCV-2026-9022', 'বেদগ্রাম প্রজেক্ট', 'বেদগ্রাম বাসস্ট্যান্ড সংলগ্ন, গোপালগঞ্জ', 'শফিক কন্ট্রাক্টর',
    site2_id, notes_rcv2, '2026-09-16 16:45:00', now_str
))
print(f"✓ Created Payment 2 (RCV-2026-9022) for বেদগ্রাম প্রজেক্ট (জমা: ৳১৫,০০০ নগদ)")

conn.commit()
conn.close()
print("\n--- ALL DEMO ENTRIES INSERTED SUCCESSFULLY INTO LOCAL SQLITE ---")
