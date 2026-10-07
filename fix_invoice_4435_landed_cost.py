import json
import psycopg2
from decimal import Decimal

DATABASE_URL = "postgresql://postgres:eUaCQcxpqmZhAFkmAqfvJVBnAJimqLTc@altaria.proxy.rlwy.net:37393/railway"

def recalculate_product_cost_and_stock(cur, prod_id):
    cur.execute('SELECT id, name, opening_stock, purchase_price, stock FROM api_product WHERE id = %s', (prod_id,))
    p = cur.fetchone()
    if not p:
        return None
    name = p[1]
    opening_stock = float(p[2] or 0.0)
    current_cost = float(p[3] or 0.0)
    old_stock = float(p[4] or 0.0)

    cur.execute('''
        SELECT t.id, t.transaction_type, t.status, ti.quantity, ti.price, t.notes
        FROM api_transactionitem ti
        JOIN api_transaction t ON ti.transaction_id = t.id
        WHERE ti.product_id = %s
        ORDER BY t.created_at ASC, t.id ASC, ti.id ASC;
    ''', (prod_id,))
    items = cur.fetchall()

    running_stock = opening_stock
    running_price = current_cost

    for tx_id, tx_type, status, qty_dec, price_dec, notes in items:
        if status in ['pending', 'draft', 'cancelled', 'rejected']:
            continue
        qty = float(qty_dec or 0)
        unit_price = float(price_dec or 0)

        if tx_type == 'purchase':
            extra_per_unit = 0.0
            if notes and notes.strip().startswith('{'):
                try:
                    first_line = notes.split('\n')[0]
                    meta = json.loads(first_line)
                    is_landed_auto = meta.get('isLandedCostAuto', True)
                    if is_landed_auto is not False and is_landed_auto != 'false' and is_landed_auto != 0:
                        ship = float(meta.get('shippingCost') or 0.0)
                        lab = float(meta.get('laborCost') or 0.0)
                        tot_extra = ship + lab
                        cur.execute('SELECT SUM(quantity) FROM api_transactionitem WHERE transaction_id = %s', (tx_id,))
                        tot_qty = float(cur.fetchone()[0] or 0)
                        if tot_qty > 0 and tot_extra > 0:
                            extra_per_unit = tot_extra / tot_qty
                except Exception:
                    pass
            landed_price = unit_price + extra_per_unit
            if (running_stock + qty) > 0 and running_stock > 0 and running_price > 0:
                running_price = ((running_stock * running_price) + (qty * landed_price)) / (running_stock + qty)
            elif landed_price > 0:
                running_price = landed_price
            running_stock += qty
        elif tx_type == 'sale':
            running_stock = max(0.0, running_stock - qty)
        elif tx_type == 'sale_return':
            running_stock += qty
        elif tx_type == 'purchase_return':
            running_stock = max(0.0, running_stock - qty)

    new_stock = round(running_stock, 2)
    new_price = round(running_price, 2)

    cur.execute('''
        UPDATE api_product
        SET stock = %s, purchase_price = %s
        WHERE id = %s;
    ''', (new_stock, new_price, prod_id))

    return {
        'id': prod_id,
        'name': name,
        'old_price': current_cost,
        'new_price': new_price,
        'stock': new_stock
    }

def recalculate_supplier_balance(cur, party_id):
    cur.execute('''
        SELECT id, name, total_purchases, total_due, opening_balance
        FROM api_party WHERE id = %s;
    ''', (party_id,))
    party = cur.fetchone()
    if not party:
        return None
    name = party[1]
    opening_bal = Decimal(str(party[4] or 0))

    # Active purchases
    cur.execute('''
        SELECT id, total_amount, paid_amount, notes
        FROM api_transaction
        WHERE party_id = %s AND transaction_type = 'purchase'
          AND status NOT IN ('pending', 'draft', 'cancelled', 'rejected');
    ''', (party_id,))
    purchases = cur.fetchall()

    purchases_tot = Decimal('0.00')
    purchases_paid = Decimal('0.00')
    for pid, tot_amt, paid_amt, notes in purchases:
        amt = Decimal(str(tot_amt or 0))
        if notes and notes.strip().startswith('{'):
            try:
                meta = json.loads(notes.split('\n')[0])
                ship_payer = meta.get('shippingPayer', 'shop')
                labor_payer = meta.get('laborPayer', 'shop')
                ship = Decimal(str(meta.get('shippingCost') or meta.get('shipping_cost') or meta.get('transportCost') or 0)) if ship_payer != 'supplier' else Decimal('0.00')
                lab = Decimal(str(meta.get('laborCost') or meta.get('labor_cost') or 0)) if labor_payer != 'supplier' else Decimal('0.00')
                amt = max(Decimal('0.00'), amt - (ship + lab))
            except Exception:
                pass
        purchases_tot += amt
        purchases_paid += Decimal(str(paid_amt or 0))

    # Payments out
    cur.execute('''
        SELECT COALESCE(SUM(paid_amount), 0), COALESCE(SUM(discount), 0)
        FROM api_transaction
        WHERE party_id = %s AND transaction_type = 'payment_out'
          AND status NOT IN ('pending', 'draft', 'cancelled', 'rejected');
    ''', (party_id,))
    p_row = cur.fetchone()
    payments_tot = Decimal(str(p_row[0])) + Decimal(str(p_row[1]))

    # Purchase returns
    cur.execute('''
        SELECT COALESCE(SUM(total_amount), 0), COALESCE(SUM(paid_amount), 0)
        FROM api_transaction
        WHERE party_id = %s AND transaction_type = 'purchase_return'
          AND status NOT IN ('pending', 'draft', 'cancelled', 'rejected');
    ''', (party_id,))
    r_row = cur.fetchone()
    returns_tot = Decimal(str(r_row[0])) - Decimal(str(r_row[1]))

    # Loans
    cur.execute('''
        SELECT COALESCE(SUM(total_amount), 0)
        FROM api_transaction
        WHERE party_id = %s AND transaction_type = 'loan_in'
          AND status NOT IN ('pending', 'draft', 'cancelled', 'rejected');
    ''', (party_id,))
    loans_tot = Decimal(str(cur.fetchone()[0]))

    net_balance = opening_bal + purchases_tot + loans_tot - purchases_paid - payments_tot - returns_tot

    cur.execute('''
        UPDATE api_party
        SET total_purchases = %s, total_due = %s
        WHERE id = %s;
    ''', (purchases_tot, net_balance, party_id))

    return {
        'id': party_id,
        'name': name,
        'total_purchases': purchases_tot,
        'total_due': net_balance
    }

def main():
    print("Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Update Transaction INV-2026-4435
        print("\n--- 1. Updating Invoice INV-2026-4435 ---")
        cur.execute("SELECT id, invoice_no, total_amount, due_amount, notes FROM api_transaction WHERE id = 4435;")
        tx = cur.fetchone()
        print(f"Current Tx 4435: Total={tx[2]}, Due={tx[3]}")
        old_meta = json.loads(tx[4].split('\n')[0])

        new_meta = dict(old_meta)
        new_meta['shippingCost'] = 15500
        new_meta['laborCost'] = 3000
        new_meta['shippingPaidAmount'] = 15500
        new_meta['laborPaidAmount'] = 3000
        new_meta['shippingStatus'] = 'paid'
        new_meta['laborStatus'] = 'paid'
        new_meta['shippingPayer'] = 'shop'
        new_meta['laborPayer'] = 'shop'
        new_meta['supplierDue'] = 1233000

        new_notes = json.dumps(new_meta, ensure_ascii=False)
        new_total_amount = Decimal('1251500.00') # 1233000 + 15500 + 3000

        cur.execute('''
            UPDATE api_transaction
            SET total_amount = %s, notes = %s
            WHERE id = 4435;
        ''', (new_total_amount, new_notes))
        print(f"Updated Tx 4435: Total={new_total_amount}, Shipping=15500, Labor=3000")

        # 2. Update Expenses 60 and 61
        print("\n--- 2. Updating Expense Records 60 and 61 ---")
        cur.execute('''
            UPDATE api_expense
            SET title = 'পরিবহন / গাড়ি ভাড়া (চালান #INV-2026-4435)',
                notes = 'চালান নং: INV-2026-4435 | গাড়ি:  | ড্রাইভার:'
            WHERE id = 60;
        ''')
        print(f"Expense 60 updated (rows affected: {cur.rowcount})")

        cur.execute('''
            UPDATE api_expense
            SET title = 'ক্রয় চালান আনলোডিং চার্জ (চালান #INV-2026-4435)',
                notes = 'ক্রয় চালান নং: INV-2026-4435 | সাপ্লায়ার: দেলোয়ার এন্ড ব্রাদার্স (কোটালিপাড়া শাখা) | স্থান: প্রধান গুদাম'
            WHERE id = 61;
        ''')
        print(f"Expense 61 updated (rows affected: {cur.rowcount})")

        # 3. Recalculate Products 7, 8, 9, 10
        print("\n--- 3. Recalculating Product Stock and Weighted Purchase Price ---")
        for pid in [7, 8, 9, 10]:
            res = recalculate_product_cost_and_stock(cur, pid)
            print(f"Product {res['id']} ({res['name']}): Old Cost={res['old_price']} -> New Cost={res['new_price']}, Stock={res['stock']}")

        # 4. Recalculate Supplier Party 64
        print("\n--- 4. Recalculating Supplier 64 Balances ---")
        s_res = recalculate_supplier_balance(cur, 64)
        print(f"Supplier {s_res['id']} ({s_res['name']}): Total Purchases={s_res['total_purchases']}, Total Due={s_res['total_due']}")

        conn.commit()
        print("\n>>> ALL UPDATES COMMITTED SUCCESSFULLY TO RAILWAY POSTGRESQL! <<<")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR OCCURRED, TRANSACTION ROLLED BACK: {e}")
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()
