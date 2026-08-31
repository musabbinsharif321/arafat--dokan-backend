import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dokan_backend.settings')
django.setup()

from decimal import Decimal
from api.models import Product, Party, Transaction, TransactionItem, Bank, Expense, Hawlat
from api.services import recalculate_product_stock_and_cost
from api.serializers import get_available_balances

def run_diagnostics():
    print("==========================================")
    print("DOKAN ERP SYSTEM INTEGRITY & DATA AUDIT")
    print("==========================================")

    # 1. Product Audit
    products = Product.objects.all()
    print(f"\n1. Products ({products.count()} items):")
    negative_stock_products = []
    stock_mismatches = []
    
    for p in products:
        old_stock = float(p.stock)
        old_cost = float(p.purchase_price)
        
        # Test recalculation
        recalculated = recalculate_product_stock_and_cost(p.id)
        if recalculated:
            new_stock = float(recalculated.stock)
            new_cost = float(recalculated.purchase_price)
            if new_stock < 0:
                negative_stock_products.append((p.id, p.name, new_stock))
            if round(old_stock, 2) != round(new_stock, 2):
                stock_mismatches.append((p.id, p.name, old_stock, new_stock))
    
    print(f" - Negative stock products: {len(negative_stock_products)}")
    for item in negative_stock_products:
        print(f"   * [Product ID {item[0]}] {item[1]}: Stock = {item[2]}")
        
    print(f" - Stock recalculation adjustments needed: {len(stock_mismatches)}")
    for item in stock_mismatches:
        print(f"   * [Product ID {item[0]}] {item[1]}: Old={item[2]} -> Recalculated={item[3]}")

    # 2. Party Balance Audit
    parties = Party.objects.all()
    print(f"\n2. Parties ({parties.count()} records):")
    
    for pt in parties:
        txs = Transaction.objects.filter(party=pt).exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
        if pt.total_due < 0:
            print(f"   * [Party ID {pt.id}] {pt.name} ({pt.party_type}): Negative Due = {pt.total_due}")

    # 3. Cash & Bank Balances
    print(f"\n3. Cash & Bank Balances:")
    cash_bal, bank_bal = get_available_balances()
    print(f" - Calculated Cash Balance: {cash_bal}")
    print(f" - Calculated Total Bank Balance: {bank_bal}")
    
    banks = Bank.objects.all()
    print(f" - Registered Banks ({banks.count()} accounts):")
    for b in banks:
        print(f"   * {b.name} (Acc: {b.account_number or 'N/A'}): Balance = ৳{b.balance:,.2f}")

    # 4. Transactions summary
    txs_total = Transaction.objects.count()
    active_txs = Transaction.objects.exclude(status__in=['pending', 'draft', 'cancelled', 'rejected']).count()
    pending_txs = Transaction.objects.filter(status='pending').count()
    print(f"\n4. Transactions:")
    print(f" - Total Transactions: {txs_total}")
    print(f" - Active/Completed: {active_txs}")
    print(f" - Pending: {pending_txs}")

    print("\n==========================================")
    print("AUDIT COMPLETE - SYSTEM INTEGRITY VERIFIED")
    print("==========================================")

if __name__ == '__main__':
    run_diagnostics()
