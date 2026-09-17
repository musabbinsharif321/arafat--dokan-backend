import sqlite3

conn = sqlite3.connect('db.sqlite3')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== VERIFYING DEMO SITES FOR CUSTOMER 16 ===")
sites = cursor.execute("SELECT id, name, address, contact_person, contact_phone FROM api_customersite WHERE customer_id=16").fetchall()
for s in sites:
    print(f"Site ID: {s['id']} | Name: {s['name']} | Address: {s['address']} | Contact: {s['contact_person']} ({s['contact_phone']})")

print("\n=== VERIFYING SITE TRANSACTIONS ===")
txs = cursor.execute("""
    SELECT id, invoice_no, transaction_type, site_name, total_amount, paid_amount, due_amount, payment_method, created_at
    FROM api_transaction
    WHERE party_id=16 AND site_name IS NOT NULL
    ORDER BY created_at ASC
""").fetchall()

miapara_bill = 0
miapara_paid = 0
bedgram_bill = 0
bedgram_paid = 0

for t in txs:
    print(f"{t['created_at']} | {t['invoice_no']} | {t['transaction_type']} | Site: {t['site_name']} | Total: {t['total_amount']} | Paid: {t['paid_amount']} | Due: {t['due_amount']}")
    if t['site_name'] == 'মিয়াপাড়া সাইট':
        if t['transaction_type'] == 'sale':
            miapara_bill += t['total_amount']
        miapara_paid += t['paid_amount']
    elif t['site_name'] == 'বেদগ্রাম প্রজেক্ট':
        if t['transaction_type'] == 'sale':
            bedgram_bill += t['total_amount']
        bedgram_paid += t['paid_amount']

print("\n=== CALCULATED SITE BALANCES ===")
print(f"মিয়াপাড়া সাইট -> মোট বিল: ৳{miapara_bill:,} | মোট জমা: ৳{miapara_paid:,} | সাইটের নিট বকেয়া: ৳{(miapara_bill - miapara_paid):,}")
print(f"বেদগ্রাম প্রজেক্ট -> মোট বিল: ৳{bedgram_bill:,} | মোট জমা: ৳{bedgram_paid:,} | সাইটের নিট বকেয়া: ৳{(bedgram_bill - bedgram_paid):,}")
print(f"উভয় সাইট মিলিয়ে মোট বিল: ৳{(miapara_bill + bedgram_bill):,} | মোট জমা: ৳{(miapara_paid + bedgram_paid):,} | মোট বকেয়া: ৳{((miapara_bill - miapara_paid) + (bedgram_bill - bedgram_paid)):,}")

conn.close()
