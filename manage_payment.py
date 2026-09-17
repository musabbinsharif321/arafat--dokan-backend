import sys
import psycopg2
from decimal import Decimal

DATABASE_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def view_supplier_payments(party_id=64):
    """View all payments made to a specific supplier."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, opening_balance, total_purchases, total_due FROM api_party WHERE id = %s;", (party_id,))
    party = cur.fetchone()
    if not party:
        print(f"Party with ID {party_id} not found.")
        return

    print("=" * 80)
    print(f"সাপ্লায়ার: {party[1]} (ID: {party[0]})")
    print(f"প্রারম্ভিক বকেয়া: ৳ {party[2]:,.2f} | মোট ক্রয়: ৳ {party[3]:,.2f} | বর্তমান বকেয়া: ৳ {party[4]:,.2f}")
    print("=" * 80)

    cur.execute("""
        SELECT id, invoice_no, paid_amount, payment_method, notes, created_at
        FROM api_transaction
        WHERE party_id = %s AND transaction_type = 'payment_out'
        ORDER BY created_at ASC, id ASC;
    """, (party_id,))
    rows = cur.fetchall()

    print(f"{'TX ID':<8} | {'ভাউচার নং':<15} | {'পরিশোধ (টাকা)':<16} | {'মেথড':<8} | {'তারিখ':<12} | {'বিবরণ / নোট'}")
    print("-" * 80)
    total_paid = Decimal('0.00')
    for r in rows:
        tx_id, inv, paid, method, notes, dt = r
        total_paid += paid
        dt_str = dt.strftime('%d-%b-%Y')
        import json
        user_note = ""
        if notes and notes.strip().startswith('{'):
            try:
                user_note = json.loads(notes.split('\n')[0]).get('userNote', '')
            except Exception:
                user_note = notes
        else:
            user_note = notes or ""
        print(f"{tx_id:<8} | {inv:<15} | ৳ {paid:<14,.2f} | {method:<8} | {dt_str:<12} | {user_note}")

    print("-" * 80)
    print(f"মোট পেমেন্ট সংখ্যা: {len(rows)} টি | সর্বমোট পরিশোধিত টাকা: ৳ {total_paid:,.2f}")
    print("=" * 80)

    cur.close()
    conn.close()

def update_payment(tx_id, new_amount, new_note=None):
    """
    Safely update a payment transaction amount and automatically
    recalculate the supplier's due balance.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, party_id, invoice_no, paid_amount, transaction_type FROM api_transaction WHERE id = %s;", (tx_id,))
    tx = cur.fetchone()
    if not tx:
        print(f"Transaction ID {tx_id} not found!")
        return

    if tx[4] != 'payment_out':
        print(f"Warning: Transaction {tx_id} is '{tx[4]}', not 'payment_out'.")

    party_id = tx[1]
    old_amount = tx[3]
    new_amt_dec = Decimal(str(new_amount))

    print(f"Updating Transaction #{tx_id} ({tx[2]}): ৳ {old_amount:,.2f} -> ৳ {new_amt_dec:,.2f}")

    if new_note:
        import json
        notes_dict = {
            "isHistoricalLedger": True,
            "supplierLedger": True,
            "userNote": new_note
        }
        cur.execute("""
            UPDATE api_transaction
            SET paid_amount = %s, total_amount = %s, notes = %s, updated_at = NOW()
            WHERE id = %s;
        """, (new_amt_dec, new_amt_dec, json.dumps(notes_dict, ensure_ascii=False), tx_id))
    else:
        cur.execute("""
            UPDATE api_transaction
            SET paid_amount = %s, total_amount = %s, updated_at = NOW()
            WHERE id = %s;
        """, (new_amt_dec, new_amt_dec, tx_id))

    # Recalculate party balance
    cur.execute("SELECT opening_balance, total_purchases FROM api_party WHERE id = %s;", (party_id,))
    p_info = cur.fetchone()
    op_bal = p_info[0] or Decimal('0.00')
    tot_pur = p_info[1] or Decimal('0.00')

    cur.execute("SELECT COALESCE(SUM(paid_amount), 0) FROM api_transaction WHERE party_id = %s AND transaction_type = 'payment_out';", (party_id,))
    tot_payments = cur.fetchone()[0]

    net_due = op_bal + tot_pur - tot_payments

    cur.execute("""
        UPDATE api_party
        SET total_due = %s, advance_balance = 0.00, updated_at = NOW()
        WHERE id = %s;
    """, (net_due, party_id))

    conn.commit()
    print(f"Successfully updated! Supplier (ID {party_id}) new total due: ৳ {net_due:,.2f}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "update":
        # Usage: python manage_payment.py update <tx_id> <new_amount> [new_note]
        tx_id = int(sys.argv[2])
        new_amt = sys.argv[3]
        note = sys.argv[4] if len(sys.argv) > 4 else None
        update_payment(tx_id, new_amt, note)
    else:
        # Default: view payments for Party 64
        view_supplier_payments(64)
