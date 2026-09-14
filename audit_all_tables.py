import psycopg2

DB_URL = 'postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway'

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# Get all tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'api_%';")
tables = [t[0] for t in cur.fetchall()]

print("=== COMPLETE AUDIT OF RAILWAY POSTGRESQL TABLES ===")
for t in sorted(tables):
    cur.execute(f"SELECT count(*) FROM {t};")
    cnt = cur.fetchone()[0]
    print(f"Table: {t:<25} -> Rows: {cnt}")

print("\n--- Specific Field Audits ---")

# 1. Banks & Bank Balances
cur.execute("SELECT * FROM api_bank;")
banks = cur.fetchall()
print(f"api_bank records: {banks}")

# 2. Expenses
cur.execute("SELECT count(*), coalesce(sum(amount), 0) FROM api_expense;")
exp = cur.fetchone()
print(f"api_expense count: {exp[0]}, sum: {exp[1]}")

# 3. Hawlat
cur.execute("SELECT count(*), coalesce(sum(amount), 0) FROM api_hawlat;")
haw = cur.fetchone()
print(f"api_hawlat count: {haw[0]}, sum: {haw[1]}")

# 4. Cash / Shop Settings
cur.execute("SELECT count(*) FROM api_shopsettings;")
print(f"api_shopsettings count: {cur.fetchone()[0]}")

# 5. Customer Sites
cur.execute("SELECT count(*) FROM api_customersite;")
print(f"api_customersite count: {cur.fetchone()[0]}")

# 6. Parties (Customers)
cur.execute("SELECT id, name, party_type, total_sales, total_due FROM api_party ORDER BY id;")
parties = cur.fetchall()
print("\napi_party records:")
for p in parties:
    print("  ", p)

# 7. Transactions
cur.execute("SELECT transaction_type, count(*), sum(total_amount), sum(paid_amount), sum(due_amount) FROM api_transaction GROUP BY transaction_type;")
print("\napi_transaction summary:")
for tx in cur.fetchall():
    print("  ", tx)

# 8. Check if any transaction has bank_account_id
cur.execute("SELECT count(*) FROM api_transaction WHERE bank_account_id IS NOT NULL;")
print(f"\nTransactions linked to Bank: {cur.fetchone()[0]} (Expected: 0)")

# 9. Check if any transaction item is linked to a product
cur.execute("SELECT count(*) FROM api_transactionitem WHERE product_id IS NOT NULL;")
print(f"TransactionItems linked to Product: {cur.fetchone()[0]} (Expected: 0)")

conn.close()
