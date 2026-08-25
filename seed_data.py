import os
import sys
import django

# Setup django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dokan_backend.settings')
django.setup()

from django.contrib.auth.models import User
from api.models import (
    ShopSettings,
    Party,
    Category,
    Product,
    Bank,
    Transaction,
    TransactionItem,
    ExpenseCategory,
    Expense,
    UserProfile
)

def seed():
    print("Seeding Dokan ERP initial database...")

    # 0. Initial Users with 3 Roles (Admin, Staff, Viewer)
    admin_u, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@dokan.com', 'first_name': 'দোকান মালিক (এডমিন)', 'is_staff': True, 'is_superuser': True})
    admin_u.set_password('admin123')
    admin_u.is_staff = True
    admin_u.is_superuser = True
    admin_u.save()
    p_admin, _ = UserProfile.objects.get_or_create(user=admin_u)
    p_admin.role = 'admin'
    p_admin.full_name = 'দোকান মালিক (এডমিন)'
    p_admin.phone = '01711000000'
    p_admin.save()

    staff_u, _ = User.objects.get_or_create(username='staff', defaults={'email': 'staff@dokan.com', 'first_name': 'স্টাফ ম্যানেজার', 'is_staff': False, 'is_superuser': False})
    staff_u.set_password('staff123')
    staff_u.save()
    p_staff, _ = UserProfile.objects.get_or_create(user=staff_u)
    p_staff.role = 'staff'
    p_staff.full_name = 'স্টাফ ম্যানেজার'
    p_staff.phone = '01711000001'
    p_staff.save()

    viewer_u, _ = User.objects.get_or_create(username='viewer', defaults={'email': 'viewer@dokan.com', 'first_name': 'রিপোর্ট ভিউয়ার', 'is_staff': False, 'is_superuser': False})
    viewer_u.set_password('viewer123')
    viewer_u.save()
    p_viewer, _ = UserProfile.objects.get_or_create(user=viewer_u)
    p_viewer.role = 'viewer'
    p_viewer.full_name = 'রিপোর্ট ভিউয়ার'
    p_viewer.phone = '01711000002'
    p_viewer.save()

    print("Users initialized: admin (Full Access), staff (No Invoice Edit/Delete), viewer (Read-Only).")

    # 1. Shop Settings
    settings, created = ShopSettings.objects.get_or_create(id=1, defaults={
        'business_name': 'দোকান ইআরপি (Dokan ERP)',
        'phone': '01711-000000',
        'email': 'contact@dokanerp.com',
        'address': 'মিরপুর ১০, ঢাকা - ১২১৬',
        'currency': '৳',
        'receipt_footer': 'আমাদের সাথে থাকার জন্য ধন্যবাদ!'
    })
    print(f"Shop settings initialized: {settings.business_name}")

    # 2. Categories
    cat_grocery, _ = Category.objects.get_or_create(name='মুদি সামগ্রী', defaults={'description': 'দৈনন্দিন মুদি মালামাল'})
    cat_electronics, _ = Category.objects.get_or_create(name='ইলেকট্রনিক্স', defaults={'description': 'হোম অ্যাপ্লায়েন্স ও গ্যাজেটস'})
    cat_beverage, _ = Category.objects.get_or_create(name='পানীয়', defaults={'description': 'সফট ড্রিংকস ও জুস'})

    # 3. Products
    p1, _ = Product.objects.get_or_create(sku='PRD-001', defaults={
        'name': 'মিনিকেট চাল ২৫ কেজি',
        'category': cat_grocery,
        'category_name': cat_grocery.name,
        'stock': 45,
        'min_stock': 10,
        'unit': 'বস্তা',
        'purchase_price': 1650.00,
        'sell_price': 1850.00,
        'brand': 'তীর',
        'description': 'উন্নত মানের সুগন্ধি মিনিকেট চাল'
    })

    p2, _ = Product.objects.get_or_create(sku='PRD-002', defaults={
        'name': 'সয়াবিন তেল ৫ লিটার',
        'category': cat_grocery,
        'category_name': cat_grocery.name,
        'stock': 3,
        'min_stock': 10,
        'unit': 'বোতল',
        'purchase_price': 780.00,
        'sell_price': 840.00,
        'brand': 'রূপচাঁদা',
        'description': 'বিশুদ্ধ ফর্টিফাইড সয়াবিন তেল'
    })

    p3, _ = Product.objects.get_or_create(sku='PRD-003', defaults={
        'name': 'কোকা কোলা ১.৫ লিটার',
        'category': cat_beverage,
        'category_name': cat_beverage.name,
        'stock': 120,
        'min_stock': 20,
        'unit': 'বোতল',
        'purchase_price': 85.00,
        'sell_price': 100.00,
        'brand': 'Coca-Cola'
    })

    print("Products initialized.")

    # 4. Parties
    c1, _ = Party.objects.get_or_create(phone='01812345678', defaults={
        'name': 'রফিকুল ইসলাম',
        'business_name': 'রফিক ট্র্রেডার্স',
        'party_type': 'customer',
        'customer_type': 'পাইকারি গ্রাহক',
        'address': 'ধানমন্ডি, ঢাকা',
        'opening_balance': 5000.00,
        'credit_limit': 50000.00,
        'total_due': 12500.00
    })

    s1, _ = Party.objects.get_or_create(phone='01987654321', defaults={
        'name': 'আবুল কালাম',
        'business_name': 'কালাম ডিস্ট্রিবিউশন',
        'party_type': 'supplier',
        'supply_type': 'মুদি পাইকারি',
        'address': 'কারওয়ান বাজার, ঢাকা',
        'opening_balance': 0.00,
        'credit_limit': 100000.00,
        'total_due': 0.00
    })

    print("Parties initialized.")

    # 5. Banks
    b1, _ = Bank.objects.get_or_create(name='ডাচ বাংলা ব্যাংক', defaults={
        'bank_name': 'Dutch-Bangla Bank',
        'account_number': '123-456-7890',
        'branch': 'মিরপুর শাখা',
        'balance': 350000.00
    })

    # 6. Expenses
    exp_cat, _ = ExpenseCategory.objects.get_or_create(name='দোকান ভাড়া')
    Expense.objects.get_or_create(title='চলতি মাসের দোকান ভাড়া', defaults={
        'category': exp_cat,
        'category_name': exp_cat.name,
        'amount': 15000.00,
        'payment_method': 'ক্যাশ',
        'notes': 'জুলাই ২০২৬ ভাড়া'
    })

    # 7. Sample Transaction
    t1, created_t1 = Transaction.objects.get_or_create(invoice_no='INV-2026-0001', defaults={
        'party': c1,
        'party_name': c1.name,
        'party_phone': c1.phone,
        'transaction_type': 'sale',
        'status': 'completed',
        'subtotal': 3700.00,
        'discount': 100.00,
        'tax': 0.00,
        'total_amount': 3600.00,
        'paid_amount': 2000.00,
        'due_amount': 1600.00,
        'payment_method': 'cash',
        'notes': 'নগদ ও বকেয়া বিক্রি'
    })

    if created_t1:
        TransactionItem.objects.create(
            transaction=t1,
            product=p1,
            product_name=p1.name,
            quantity=2,
            price=p1.sell_price,
            unit=p1.unit,
            total=3700.00
        )

    print("Sample Transactions initialized.")
    print("Database seeding finished successfully!")

if __name__ == '__main__':
    seed()
