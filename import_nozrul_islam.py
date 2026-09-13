import os
import sys
import django
import json
from decimal import Decimal
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dokan_backend.settings')
django.setup()

from django.utils import timezone
from api.models import Party, Product, Transaction, TransactionItem

# 1. Create or get party: নজরুল ইসলাম
party, created = Party.objects.get_or_create(
    name="নজরুল ইসলাম",
    defaults={
        'party_type': 'customer',
        'address': 'নবীন বাগ',
        'phone': '01712000000',
        'customer_type': 'খুচরা গ্রাহক',
        'joined_date': datetime.strptime('2024-09-05', '%Y-%m-%d').date(),
        'opening_balance': Decimal('0.00'),
        'total_sales': Decimal('3352839.40'),
        'total_due': Decimal('67823.40'),
    }
)
if not created:
    # Clear existing transactions for fresh import if rerun
    Transaction.objects.filter(party=party).delete()
    party.address = 'নবীন বাগ'
    party.joined_date = datetime.strptime('2024-09-05', '%Y-%m-%d').date()
    party.total_sales = Decimal('3352839.40')
    party.total_due = Decimal('67823.40')
    party.save()

print(f"Party: {party.name} (ID: {party.id})")

# 2. Products mapping
prod_names = [
    ("10 মি.লি বি এস আর এম", "কেজি"),
    ("12 মি.লি বি এস আর এম", "কেজি"),
    ("16 মি.লি বি এস আর এম", "কেজি"),
    ("20 মি.লি বি এস আর এম", "কেজি"),
    ("সিমেন্ট হোলসিম", "বস্তা"),
    ("সিমেন্ট এ্যাংকর আপ", "বস্তা"),
]

prod_map = {}
for p_name, p_unit in prod_names:
    p_obj, _ = Product.objects.get_or_create(
        name=p_name,
        defaults={
            'unit': p_unit,
            'category_name': 'রড' if 'মি.লি' in p_name else 'সিমেন্ট',
            'stock': Decimal('10000.00'),
            'purchase_price': Decimal('80.00'),
            'sell_price': Decimal('90.00'),
        }
    )
    prod_map[p_name] = p_obj

# 3. Transaction definitions
# Each item is either:
# {'type': 'sale', 'date': 'YYYY-MM-DD', 'items': [(name, qty, rate, total)], 'labor': X, 'shipping': Y, 'paid': Z}
# or
# {'type': 'payment_in', 'date': 'YYYY-MM-DD', 'amount': X}

tx_list = [
    # 05-09-2024
    {
        'type': 'sale', 'date': '2024-09-05',
        'items': [
            ("10 মি.লি বি এস আর এম", Decimal('649.1'), Decimal('94.0'), Decimal('61015.4')),
            ("16 মি.লি বি এস আর এম", Decimal('1815.9'), Decimal('94.0'), Decimal('170694.6')),
            ("20 মি.লি বি এস আর এম", Decimal('1536.5'), Decimal('94.0'), Decimal('144431.0')),
            ("16 মি.লি বি এস আর এম", Decimal('980.3'), Decimal('94.0'), Decimal('92148.2')),
        ],
        'labor': Decimal('1250.0'), 'shipping': Decimal('1000.0'), 'paid': Decimal('136000.0')
    },
    # 11-09-2024
    {
        'type': 'payment_in', 'date': '2024-09-11', 'amount': Decimal('329000.0')
    },
    # 15-10-2024
    {
        'type': 'sale', 'date': '2024-10-15',
        'items': [
            ("20 মি.লি বি এস আর এম", Decimal('1417.9'), Decimal('91.0'), Decimal('129028.9')),
            ("12 মি.লি বি এস আর এম", Decimal('520.9'), Decimal('91.0'), Decimal('47401.9')),
            ("10 মি.লি বি এস আর এম", Decimal('788.9'), Decimal('91.0'), Decimal('71789.9')),
            ("16 মি.লি বি এস আর এম", Decimal('1955.8'), Decimal('91.0'), Decimal('177977.8')),
        ],
        'labor': Decimal('1170.0'), 'shipping': Decimal('1000.0'), 'paid': Decimal('0.0')
    },
    # 16-10-2024
    {
        'type': 'payment_in', 'date': '2024-10-16', 'amount': Decimal('421300.0')
    },
    # 17-10-2024
    {
        'type': 'sale', 'date': '2024-10-17',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('20.0'), Decimal('530.0'), Decimal('10600.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('200.0'), 'paid': Decimal('0.0')
    },
    # 26-10-2024
    {
        'type': 'sale', 'date': '2024-10-26',
        'items': [
            ("10 মি.লি বি এস আর এম", Decimal('4183.5'), Decimal('91.0'), Decimal('380698.5')),
            ("12 মি.লি বি এস আর এম", Decimal('373.4'), Decimal('91.0'), Decimal('33979.4')),
        ],
        'labor': Decimal('1140.0'), 'shipping': Decimal('1000.0'), 'paid': Decimal('319000.0')
    },
    # 30-10-2024
    {
        'type': 'payment_in', 'date': '2024-10-30', 'amount': Decimal('92000.0')
    },
    # 01-11-2024
    {
        'type': 'sale', 'date': '2024-11-01',
        'items': [
            ("10 মি.লি বি এস আর এম", Decimal('234.7'), Decimal('91.0'), Decimal('21357.7')),
            ("সিমেন্ট হোলসিম", Decimal('400.0'), Decimal('524.0'), Decimal('209600.0')),
        ],
        'labor': Decimal('58.0'), 'shipping': Decimal('200.0'), 'paid': Decimal('0.0')
    },
    # 03-11-2024
    {
        'type': 'payment_in', 'date': '2024-11-03', 'amount': Decimal('209600.0')
    },
    # 14-11-2024
    {
        'type': 'sale', 'date': '2024-11-14',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 17-11-2024
    {
        'type': 'sale', 'date': '2024-11-17',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('150.0'), 'paid': Decimal('0.0')
    },
    # 21-11-2024
    {
        'type': 'sale', 'date': '2024-11-21',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 24-11-2024
    {
        'type': 'sale', 'date': '2024-11-24',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 26-11-2024
    {
        'type': 'sale', 'date': '2024-11-26',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    {
        'type': 'payment_in', 'date': '2024-11-26', 'amount': Decimal('26000.0')
    },
    # 29-11-2024
    {
        'type': 'sale', 'date': '2024-11-29',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 02-12-2024
    {
        'type': 'sale', 'date': '2024-12-02',
        'items': [
            ("20 মি.লি বি এস আর এম", Decimal('2134.8'), Decimal('87.5'), Decimal('186795.0')),
            ("16 মি.লি বি এস আর এম", Decimal('1800.8'), Decimal('87.5'), Decimal('157570.0')),
            ("10 মি.লি বি এস আর এম", Decimal('654.4'), Decimal('87.5'), Decimal('57260.0')),
        ],
        'labor': Decimal('1147.0'), 'shipping': Decimal('1000.0'), 'paid': Decimal('0.0')
    },
    # 03-12-2024
    {
        'type': 'payment_in', 'date': '2024-12-03', 'amount': Decimal('80000.0')
    },
    # 04-12-2024
    {
        'type': 'payment_in', 'date': '2024-12-04', 'amount': Decimal('327700.0')
    },
    # 07-12-2024
    {
        'type': 'sale', 'date': '2024-12-07',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('20.0'), Decimal('530.0'), Decimal('10600.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('240.0'), 'paid': Decimal('0.0')
    },
    # 09-12-2024
    {
        'type': 'sale', 'date': '2024-12-09',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('20.0'), Decimal('530.0'), Decimal('10600.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('240.0'), 'paid': Decimal('0.0')
    },
    # 11-12-2024
    {
        'type': 'sale', 'date': '2024-12-11',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    {
        'type': 'payment_in', 'date': '2024-12-11', 'amount': Decimal('26000.0')
    },
    # 14-12-2024
    {
        'type': 'sale', 'date': '2024-12-14',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 18-12-2024
    {
        'type': 'sale', 'date': '2024-12-18',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    {
        'type': 'payment_in', 'date': '2024-12-18', 'amount': Decimal('10400.0')
    },
    # 01-01-2025
    {
        'type': 'sale', 'date': '2025-01-01',
        'items': [
            ("20 মি.লি বি এস আর এম", Decimal('1175.9'), Decimal('88.0'), Decimal('103479.2')),
            ("16 মি.লি বি এস আর এম", Decimal('2112.5'), Decimal('88.0'), Decimal('185900.0')),
            ("12 মি.লি বি এস আর এম", Decimal('434.3'), Decimal('88.0'), Decimal('38218.4')),
            ("10 মি.লি বি এস আর এম", Decimal('686.7'), Decimal('88.0'), Decimal('60429.6')),
        ],
        'labor': Decimal('1102.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('380116.0')
    },
    # 06-01-2025
    {
        'type': 'sale', 'date': '2025-01-06',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 10-01-2025
    {
        'type': 'payment_in', 'date': '2025-01-10', 'amount': Decimal('9700.0')
    },
    {
        'type': 'sale', 'date': '2025-01-10',
        'items': [
            ("10 মি.লি বি এস আর এম", Decimal('4683.6'), Decimal('93.0'), Decimal('435574.8')),
        ],
        'labor': Decimal('1170.0'), 'shipping': Decimal('1500.0'), 'paid': Decimal('0.0')
    },
    # 11-01-2025
    {
        'type': 'sale', 'date': '2025-01-11',
        'items': [
            ("10 মি.লি বি এস আর এম", Decimal('80.3'), Decimal('93.0'), Decimal('7467.9')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 12-01-2025
    {
        'type': 'sale', 'date': '2025-01-12',
        'items': [
            ("12 মি.লি বি এস আর এম", Decimal('442.3'), Decimal('93.0'), Decimal('41133.9')),
            ("16 মি.লি বি এস আর এম", Decimal('148.3'), Decimal('93.0'), Decimal('13791.9')),
        ],
        'labor': Decimal('167.0'), 'shipping': Decimal('400.0'), 'paid': Decimal('0.0')
    },
    # 17-01-2025
    {
        'type': 'sale', 'date': '2025-01-17',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('380.0'), Decimal('525.0'), Decimal('199500.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    {
        'type': 'payment_in', 'date': '2025-01-17', 'amount': Decimal('697500.0')
    },
    # 29-01-2025
    {
        'type': 'sale', 'date': '2025-01-29',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 30-01-2025
    {
        'type': 'sale', 'date': '2025-01-30',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 02-02-2025
    {
        'type': 'sale', 'date': '2025-02-02',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 03-02-2025
    {
        'type': 'sale', 'date': '2025-02-03',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 04-02-2025
    {
        'type': 'sale', 'date': '2025-02-04',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    {
        'type': 'payment_in', 'date': '2025-02-04', 'amount': Decimal('20800.0')
    },
    # 05-02-2025
    {
        'type': 'sale', 'date': '2025-02-05',
        'items': [
            ("10 মি.লি বি এস আর এম", Decimal('277.1'), Decimal('91.5'), Decimal('25354.6')),
            ("12 মি.লি বি এস আর এম", Decimal('224.5'), Decimal('91.5'), Decimal('20541.8')),
        ],
        'labor': Decimal('125.0'), 'shipping': Decimal('200.0'), 'paid': Decimal('0.0')
    },
    # 06-02-2025
    {
        'type': 'sale', 'date': '2025-02-06',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 13-02-2025
    {
        'type': 'sale', 'date': '2025-02-13',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 14-02-2025
    {
        'type': 'sale', 'date': '2025-02-14',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 17-02-2025
    {
        'type': 'sale', 'date': '2025-02-17',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 19-02-2025
    {
        'type': 'payment_in', 'date': '2025-02-19', 'amount': Decimal('71700.0')
    },
    # 23-02-2025
    {
        'type': 'sale', 'date': '2025-02-23',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 24-02-2025
    {
        'type': 'sale', 'date': '2025-02-24',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 25-02-2025 (1st)
    {
        'type': 'sale', 'date': '2025-02-25',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 25-02-2025 (2nd)
    {
        'type': 'sale', 'date': '2025-02-25',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 02-03-2025 (1st)
    {
        'type': 'sale', 'date': '2025-03-02',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 02-03-2025 (2nd)
    {
        'type': 'sale', 'date': '2025-03-02',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 04-03-2025
    {
        'type': 'sale', 'date': '2025-03-04',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('20.0'), Decimal('530.0'), Decimal('10600.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('240.0'), 'paid': Decimal('0.0')
    },
    {
        'type': 'payment_in', 'date': '2025-03-04', 'amount': Decimal('31200.0')
    },
    # 06-03-2025
    {
        'type': 'sale', 'date': '2025-03-06',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 18-03-2025
    {
        'type': 'sale', 'date': '2025-03-18',
        'items': [
            ("সিমেন্ট হোলসিম", Decimal('10.0'), Decimal('530.0'), Decimal('5300.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('120.0'), 'paid': Decimal('0.0')
    },
    # 19-03-2025
    {
        'type': 'payment_in', 'date': '2025-03-19', 'amount': Decimal('20800.0')
    },
    # 10-04-2025
    {
        'type': 'sale', 'date': '2025-04-10',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 11-04-2025
    {
        'type': 'sale', 'date': '2025-04-11',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 13-04-2025
    {
        'type': 'sale', 'date': '2025-04-13',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 15-04-2025
    {
        'type': 'sale', 'date': '2025-04-15',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 18-04-2025
    {
        'type': 'payment_in', 'date': '2025-04-18', 'amount': Decimal('20400.0')
    },
    # 05-05-2025
    {
        'type': 'sale', 'date': '2025-05-05',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 06-05-2025
    {
        'type': 'sale', 'date': '2025-05-06',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 09-05-2025
    {
        'type': 'sale', 'date': '2025-05-09',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 11-05-2025
    {
        'type': 'sale', 'date': '2025-05-11',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 12-05-2025
    {
        'type': 'sale', 'date': '2025-05-12',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 14-05-2025
    {
        'type': 'sale', 'date': '2025-05-14',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 15-05-2025
    {
        'type': 'sale', 'date': '2025-05-15',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 17-05-2025
    {
        'type': 'sale', 'date': '2025-05-17',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 18-05-2025
    {
        'type': 'payment_in', 'date': '2025-05-18', 'amount': Decimal('25500.0')
    },
    # 19-05-2025 (1st)
    {
        'type': 'sale', 'date': '2025-05-19',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 19-05-2025 (2nd)
    {
        'type': 'sale', 'date': '2025-05-19',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 21-05-2025
    {
        'type': 'sale', 'date': '2025-05-21',
        'items': [
            ("সিমেন্ট এ্যাংকর আপ", Decimal('10.0'), Decimal('510.0'), Decimal('5100.0')),
        ],
        'labor': Decimal('0.0'), 'shipping': Decimal('0.0'), 'paid': Decimal('0.0')
    },
    # 31-07-2025
    {
        'type': 'payment_in', 'date': '2025-07-31', 'amount': Decimal('30300.0')
    },
]

total_sales_sum = Decimal('0.00')
total_paid_sum = Decimal('0.00')

inv_count = 1
for tx_data in tx_list:
    d_str = tx_data['date']
    t_date = datetime.strptime(d_str, '%Y-%m-%d')
    aware_date = timezone.make_aware(t_date, timezone.get_current_timezone())

    if tx_data['type'] == 'payment_in':
        amt = tx_data['amount']
        total_paid_sum += amt
        tx = Transaction.objects.create(
            party=party,
            party_name=party.name,
            party_phone=party.phone,
            transaction_type='payment_in',
            status='completed',
            subtotal=amt,
            total_amount=amt,
            paid_amount=amt,
            due_amount=Decimal('0.00'),
            payment_method='cash',
            invoice_no=f"RCV-{d_str.replace('-', '')}-{inv_count:03d}",
            created_at=aware_date,
            notes='ক্যাশ জমা'
        )
        inv_count += 1
    else:
        # Sale invoice
        items = tx_data['items']
        labor = tx_data.get('labor', Decimal('0.00'))
        shipping = tx_data.get('shipping', Decimal('0.00'))
        paid = tx_data.get('paid', Decimal('0.00'))

        subtot = sum(it[3] for it in items)
        tot = subtot + labor + shipping
        due = max(Decimal('0.00'), tot - paid)

        total_sales_sum += tot
        total_paid_sum += paid

        notes_meta = {
            'laborCost': float(labor),
            'shippingCost': float(shipping)
        }

        inv_num = f"INV-{d_str.replace('-', '')}-{inv_count:03d}"
        tx = Transaction.objects.create(
            party=party,
            party_name=party.name,
            party_phone=party.phone,
            transaction_type='sale',
            status='completed',
            subtotal=subtot,
            total_amount=tot,
            paid_amount=paid,
            due_amount=due,
            payment_method='cash',
            invoice_no=inv_num,
            created_at=aware_date,
            notes=json.dumps(notes_meta)
        )
        inv_count += 1

        for it in items:
            p_name, qty, rate, line_tot = it
            p_obj = prod_map.get(p_name)
            TransactionItem.objects.create(
                transaction=tx,
                product=p_obj,
                product_name=p_name,
                quantity=qty,
                price=rate,
                unit='কেজি' if 'মি.লি' in p_name else 'বস্তা',
                total=line_tot
            )

party.total_sales = total_sales_sum
party.total_due = total_sales_sum - total_paid_sum
party.save()

print("\n--- IMPORT SUMMARY ---")
print(f"Total Transactions Created: {len(tx_list)}")
print(f"Total Sales Calculated: {total_sales_sum} (Expected: 3352839.40)")
print(f"Total Paid Calculated:  {total_paid_sum} (Expected: 3285016.00)")
print(f"Party Total Due:        {party.total_due} (Expected: 67823.40)")
print("SUCCESS!")
