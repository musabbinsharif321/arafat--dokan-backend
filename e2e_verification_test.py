import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dokan_backend.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from api.models import (
    ShopSettings, Party, Category, Product, Bank, 
    Transaction, TransactionItem, ExpenseCategory, 
    Expense, Hawlat, UserProfile
)
from api.services import recalculate_product_stock_and_cost
from api.serializers import get_available_balances

def test_full_erp_workflow():
    print("=" * 60)
    print("STARTING FULL DOKAN ERP END-TO-END VERIFICATION")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = 0

    def assert_test(condition, test_name):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f" [PASS] {test_name}")
        else:
            print(f" [FAIL] {test_name}")

    # TEST 1: Shop Settings
    settings = ShopSettings.objects.first()
    assert_test(settings is not None and len(settings.business_name) > 0, "1. Shop Settings exists and has business name")

    # TEST 2: Users and Roles
    dev_user = User.objects.filter(is_superuser=True).first()
    assert_test(dev_user is not None, "2. Developer / Superuser account exists")

    # TEST 3: Product Inventory Integrity
    products = Product.objects.all()
    assert_test(products.count() > 0, "3. Products exist in inventory")
    negative_stock = products.filter(stock__lt=0).exists()
    assert_test(not negative_stock, "4. No products with negative stock found")

    # TEST 4: Party Directory
    customers = Party.objects.filter(party_type__in=['customer', 'both'])
    suppliers = Party.objects.filter(party_type__in=['supplier', 'both'])
    assert_test(customers.count() > 0, "5. Customer directory has valid records")
    assert_test(suppliers.count() > 0, "6. Supplier directory has valid records")

    # TEST 5: Cash and Bank Balance calculations
    cash_bal, bank_bal = get_available_balances()
    assert_test(isinstance(cash_bal, Decimal) and isinstance(bank_bal, Decimal), "7. Cash & Bank balances computed successfully as Decimal")

    # TEST 6: Test API Endpoints with APIClient (Simulation)
    client = APIClient()
    if dev_user:
        client.force_authenticate(user=dev_user)

    # Check dashboard stats API
    res_dash = client.get('/api/dashboard/stats/')
    assert_test(res_dash.status_code == 200, "8. GET /api/dashboard/stats/ returned 200 OK")
    if res_dash.status_code == 200:
        data = res_dash.data
        assert_test('totalSales' in data and 'totalCash' in data and 'totalBank' in data, "9. Dashboard stats payload has all required financial keys")

    # Check product cost logs API
    res_cost = client.get('/api/products/cost_logs/')
    assert_test(res_cost.status_code == 200, "10. GET /api/products/cost_logs/ returned 200 OK")

    # Check transactions API
    res_tx = client.get('/api/transactions/')
    assert_test(res_tx.status_code == 200, "11. GET /api/transactions/ returned 200 OK")

    # Check parties API
    res_parties = client.get('/api/parties/')
    assert_test(res_parties.status_code == 200, "12. GET /api/parties/ returned 200 OK")

    # Check expenses API
    res_exp = client.get('/api/expenses/')
    assert_test(res_exp.status_code == 200, "13. GET /api/expenses/ returned 200 OK")

    # Check banks API
    res_banks = client.get('/api/banks/')
    assert_test(res_banks.status_code == 200, "14. GET /api/banks/ returned 200 OK")

    # Check hawlats API
    res_hawlat = client.get('/api/hawlats/')
    assert_test(res_hawlat.status_code == 200, "15. GET /api/hawlats/ returned 200 OK")

    pct = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    print("=" * 60)
    print(f"VERIFICATION SUMMARY: {passed_tests} / {total_tests} TESTS PASSED ({pct:.1f}%)")
    print("=" * 60)

if __name__ == '__main__':
    test_full_erp_workflow()
