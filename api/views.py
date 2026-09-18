import ipaddress
import ipaddress
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum, Count, F, Q, Case, When, Value, IntegerField
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .permissions import RoleBasedAccessPermission, IsAdminUserOnly, get_user_role
from .models import (
    ShopSettings,
    Party,
    CustomerSite,
    Category,
    Product,
    Bank,
    Transaction,
    TransactionItem,
    ExpenseCategory,
    Expense,
    Hawlat,
    UserProfile
)
from .serializers import (
    ShopSettingsSerializer,
    PartySerializer,
    CustomerSiteSerializer,
    CategorySerializer,
    ProductSerializer,
    BankSerializer,
    TransactionSerializer,
    ExpenseCategorySerializer,
    ExpenseSerializer,
    HawlatSerializer,
    UserSerializer,
    UserProfileSerializer
)

class ShopSettingsViewSet(viewsets.ModelViewSet):
    queryset = ShopSettings.objects.all()
    serializer_class = ShopSettingsSerializer
    permission_classes = [RoleBasedAccessPermission]

    def get_queryset(self):
        # Ensure at least one default settings object exists
        if not ShopSettings.objects.exists():
            ShopSettings.objects.create()
        return ShopSettings.objects.all()

class PartyViewSet(viewsets.ModelViewSet):
    queryset = Party.objects.all().order_by('-created_at')
    serializer_class = PartySerializer
    permission_classes = [RoleBasedAccessPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        party_type = self.request.query_params.get('party_type')
        search = self.request.query_params.get('search')

        if party_type:
            if party_type == 'customer':
                qs = qs.filter(Q(party_type='customer') | Q(party_type='both'))
            elif party_type == 'supplier':
                qs = qs.filter(Q(party_type='supplier') | Q(party_type='both'))
            elif party_type == 'engineer':
                qs = qs.filter(party_type='engineer')
        
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(business_name__icontains=search)
            )

        return qs

    def perform_create(self, serializer):
        from .serializers import recalculate_party_balances
        instance = serializer.save()
        recalculate_party_balances(instance)

    def perform_update(self, serializer):
        from .serializers import recalculate_party_balances
        instance = serializer.save()
        recalculate_party_balances(instance)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        parties_data = request.data.get('parties', [])
        if not isinstance(parties_data, list):
            return Response({'error': 'parties must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for idx, item in enumerate(parties_data):
                phone = str(item.get('phone', '')).strip()
                name = str(item.get('name', '')).strip()
                business_name = str(item.get('business_name', '')).strip()
                address = str(item.get('address', '')).strip()
                if not name:
                    errors.append(f"রো #{idx + 1}: কাস্টমার/সাপ্লায়ারের নাম প্রদান করা আবশ্যক।")
                    continue
                if not phone:
                    phone = f"01000{idx+1:06d}"
                    party = Party.objects.filter(name=name, address=address).first() if address else None
                else:
                    party = Party.objects.filter(phone=phone).first()

                party_type = item.get('party_type', 'customer')
                if party_type not in ['customer', 'supplier', 'engineer', 'both']:
                    party_type = 'customer'


                try:
                    opening_balance = Decimal(str(item.get('opening_balance', 0) or 0))
                except Exception:
                    opening_balance = Decimal('0.00')

                try:
                    total_due = Decimal(str(item.get('total_due', opening_balance) or opening_balance))
                except Exception:
                    total_due = opening_balance

                from .serializers import recalculate_party_balances
                if party:
                    party.name = name
                    if business_name:
                        party.business_name = business_name
                    if address:
                        party.address = address
                    if 'opening_balance' in item:
                        party.opening_balance = opening_balance
                    if 'total_due' in item or 'opening_balance' in item:
                        party.total_due = total_due
                    party.save()
                    recalculate_party_balances(party)
                    updated_count += 1
                else:
                    new_p = Party.objects.create(
                        name=name,
                        phone=phone,
                        party_type=party_type,
                        business_name=business_name,
                        address=address,
                        opening_balance=opening_balance,
                        total_due=total_due
                    )
                    recalculate_party_balances(new_p)
                    created_count += 1

        return Response({
            'success': True,
            'created_count': created_count,
            'updated_count': updated_count,
            'errors': errors
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='bulk-import-ledger')
    def bulk_import_ledger(self, request):
        """
        Bulk imports historical customer ledger entries from Excel / CSV.
        Guarantees ZERO adverse effects on live inventory stock, cash balances, or bank accounts.
        Just creates ledger transactions and items, and updates the customer's total_sales and total_due.
        """
        import json
        from datetime import datetime, date

        def parse_date(val):
            if not val:
                return timezone.now()
            if isinstance(val, (datetime, timezone.datetime)):
                return timezone.make_aware(val) if timezone.is_naive(val) else val
            if isinstance(val, date):
                return timezone.make_aware(datetime.combine(val, datetime.min.time()))
            try:
                fval = float(val)
                if 20000 < fval < 70000:
                    dt = datetime(1899, 12, 30) + timedelta(days=fval)
                    return timezone.make_aware(dt)
            except (ValueError, TypeError):
                pass
            val_str = str(val).strip()
            bn_to_en = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
            val_str = val_str.translate(bn_to_en)
            for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d.%m.%Y', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S']:
                try:
                    raw_p = val_str.split('T')[0] if ('T' in val_str and fmt in ['%Y-%m-%d', '%d-%m-%Y']) else val_str
                    dt = datetime.strptime(raw_p, fmt)
                    return timezone.make_aware(dt)
                except Exception:
                    continue
            return timezone.now()

        entries_data = request.data.get('entries', [])
        default_party_id = request.data.get('party_id')
        clear_existing = request.data.get('clear_existing', False)
        group_by_date = request.data.get('group_by_date', True)  # Default True: combine same date items into one invoice

        if not isinstance(entries_data, list):
            return Response({'error': 'entries must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        default_party = None
        if default_party_id:
            default_party = Party.objects.filter(id=default_party_id).first()

        created_transactions_count = 0
        affected_parties = set()
        errors = []

        with transaction.atomic():
            if clear_existing and default_party:
                Transaction.objects.filter(
                    Q(party=default_party) | Q(party_name__iexact=default_party.name),
                    Q(notes__icontains='isHistoricalLedger') | Q(invoice_no__icontains=f"-LEG-{default_party.id}-") | Q(invoice_no__icontains='-LEG-')
                ).delete()

            if group_by_date:
                # Group sales entries by (party_key, date_key) so they become 1 invoice with multiple items
                # And process payments individually or grouped
                grouped_orders = {}
                direct_receipts = []

                for idx, item in enumerate(entries_data):
                    # 1. Resolve Party
                    party = None
                    p_id = item.get('party_id')
                    if p_id:
                        party = Party.objects.filter(id=p_id).first()
                    if not party and default_party:
                        party = default_party

                    p_phone = str(item.get('phone', '') or item.get('customer_phone', '')).strip()
                    p_name = str(item.get('name', '') or item.get('customer_name', '') or item.get('party_name', '')).strip()

                    if not party and p_phone:
                        party = Party.objects.filter(phone=p_phone).first()
                    if not party and p_name:
                        clean_p_name = p_name.strip()
                        party = Party.objects.filter(name__iexact=clean_p_name).first()
                        if not party:
                            party = Party.objects.filter(name__icontains=clean_p_name).first()

                    if not party:
                        if p_name:
                            party = Party.objects.create(
                                name=p_name,
                                phone=p_phone or f"01000{Party.objects.count() + 1:06d}",
                                party_type='customer',
                                address=str(item.get('address', '')),
                                opening_balance=Decimal('0.00'),
                                total_due=Decimal('0.00'),
                                total_sales=Decimal('0.00')
                            )
                        else:
                            errors.append(f"রো #{idx + 1}: কাস্টমার চিহ্নিত করা যায়নি।")
                            continue

                    affected_parties.add(party)

                    # Parse values
                    entry_date = parse_date(item.get('date') or item.get('created_at'))
                    d_str = entry_date.strftime('%Y%m%d')
                    desc = str(item.get('description') or item.get('particulars') or item.get('product_name') or '').strip()
                    note_text = str(item.get('note') or item.get('notes') or item.get('remarks') or '').strip()
                    inv_no = str(item.get('invoice_no') or item.get('voucher_no') or item.get('ref_no') or '').strip()

                    method = str(item.get('payment_method') or 'cash').strip().lower()
                    if 'bank' in method or 'ব্যাংক' in method:
                        method = 'bank'
                    elif 'cheque' in method or 'চেক' in method:
                        method = 'cheque'
                    elif 'bkash' in method or 'nagad' in method or 'মোবাইল' in method:
                        method = 'mobile_banking'
                    else:
                        method = 'cash'

                    try:
                        debit = Decimal(str(item.get('debit', 0) or item.get('bill_amount', 0) or item.get('sale_amount', 0) or 0))
                    except Exception:
                        debit = Decimal('0.00')

                    try:
                        credit = Decimal(str(item.get('credit', 0) or item.get('paid_amount', 0) or item.get('deposit_amount', 0) or 0))
                    except Exception:
                        credit = Decimal('0.00')

                    try:
                        qty = Decimal(str(item.get('quantity', 1) or 1))
                    except Exception:
                        qty = Decimal('1.00')

                    try:
                        rate = Decimal(str(item.get('rate', 0) or item.get('price', 0) or 0))
                    except Exception:
                        rate = Decimal('0.00')

                    unit = str(item.get('unit') or 'টি').strip()

                    # Opening Balance Check
                    is_opening = (
                        'opening' in desc.lower() or
                        'প্রারম্ভিক' in desc or
                        'পূর্বের জের' in desc or
                        'পূর্বের বকেয়া' in desc or
                        'পূর্বের বকেয়া' in desc or
                        item.get('type') == 'opening'
                    )
                    if is_opening:
                        op_amt = debit if debit > 0 else (credit if credit > 0 else Decimal('0.00'))
                        if op_amt > 0:
                            party.opening_balance = op_amt
                            party.save(update_fields=['opening_balance'])
                        continue

                    # If this row is a sale item (debit > 0)
                    if debit > 0:
                        group_key = f"{party.id}_{d_str}_{inv_no}"
                        if group_key not in grouped_orders:
                            grouped_orders[group_key] = {
                                'party': party,
                                'date': entry_date,
                                'd_str': d_str,
                                'inv_no': inv_no,
                                'method': method,
                                'total_debit': Decimal('0.00'),
                                'total_credit': Decimal('0.00'),
                                'items': [],
                                'notes': []
                            }
                        grouped_orders[group_key]['total_debit'] += debit
                        grouped_orders[group_key]['total_credit'] += credit
                        grouped_orders[group_key]['items'].append({
                            'desc': desc or 'পণ্য বিক্রয়',
                            'qty': qty if qty > 0 else Decimal('1.00'),
                            'rate': rate if rate > 0 else debit,
                            'unit': unit,
                            'total': debit
                        })
                        if note_text:
                            grouped_orders[group_key]['notes'].append(note_text)

                    # If this row is a payment in (credit > 0 without debit)
                    elif credit > 0:
                        direct_receipts.append({
                            'party': party,
                            'date': entry_date,
                            'd_str': d_str,
                            'inv_no': inv_no,
                            'method': method,
                            'amount': credit,
                            'desc': desc or 'নগদ জমা',
                            'note': note_text
                        })

                # Create Grouped Sale Invoices (1 invoice per date)
                for g_idx, (g_key, g_data) in enumerate(grouped_orders.items()):
                    party = g_data['party']
                    total_amount = g_data['total_debit']
                    paid_amount = g_data['total_credit']
                    due_amount = max(Decimal('0.00'), total_amount - paid_amount)
                    base_inv = g_data['inv_no'] or f"INV-LEG-{party.id}-{g_data['d_str']}"
                    unique_inv = base_inv
                    c = 1
                    while Transaction.objects.filter(invoice_no=unique_inv).exists():
                        unique_inv = f"{base_inv}-{c}"
                        c += 1

                    notes_meta = {
                        'isHistoricalLedger': True,
                        'userNote': " | ".join(g_data['notes']) if g_data['notes'] else 'পূর্বের খতিয়ান চালান'
                    }

                    tx = Transaction.objects.create(
                        party=party,
                        party_name=party.name,
                        party_phone=party.phone,
                        transaction_type='sale',
                        status='completed',
                        subtotal=total_amount,
                        total_amount=total_amount,
                        paid_amount=paid_amount,
                        due_amount=due_amount,
                        payment_method=g_data['method'],
                        invoice_no=unique_inv,
                        created_at=g_data['date'],
                        notes=json.dumps(notes_meta)
                    )
                    created_transactions_count += 1

                    # Add all item lines to this single invoice
                    for itm in g_data['items']:
                        TransactionItem.objects.create(
                            transaction=tx,
                            product=None,
                            product_name=itm['desc'],
                            quantity=itm['qty'],
                            price=itm['rate'],
                            unit=itm['unit'],
                            total=itm['total']
                        )

                # Create Receipt Transactions
                for r_idx, r_data in enumerate(direct_receipts):
                    party = r_data['party']
                    base_inv = r_data['inv_no'] or f"RCV-LEG-{party.id}-{r_data['d_str']}-{r_idx+1:03d}"
                    unique_inv = base_inv
                    c = 1
                    while Transaction.objects.filter(invoice_no=unique_inv).exists():
                        unique_inv = f"{base_inv}-{c}"
                        c += 1

                    notes_meta = {
                        'isHistoricalLedger': True,
                        'userNote': r_data['note'] or r_data['desc'] or 'টাকা জমা'
                    }

                    Transaction.objects.create(
                        party=party,
                        party_name=party.name,
                        party_phone=party.phone,
                        transaction_type='payment_in',
                        status='completed',
                        subtotal=Decimal('0.00'),
                        total_amount=r_data['amount'],
                        paid_amount=r_data['amount'],
                        due_amount=Decimal('0.00'),
                        payment_method=r_data['method'],
                        invoice_no=unique_inv,
                        created_at=r_data['date'],
                        notes=json.dumps(notes_meta)
                    )
                    created_transactions_count += 1

            else:
                # Row by row mode (independent line entries)
                for idx, item in enumerate(entries_data):
                    # 1. Resolve Party
                    party = None
                    p_id = item.get('party_id')
                    if p_id:
                        party = Party.objects.filter(id=p_id).first()
                    if not party and default_party:
                        party = default_party

                    p_phone = str(item.get('phone', '') or item.get('customer_phone', '')).strip()
                    p_name = str(item.get('name', '') or item.get('customer_name', '') or item.get('party_name', '')).strip()

                    if not party and p_phone:
                        party = Party.objects.filter(phone=p_phone).first()
                    if not party and p_name:
                        clean_p_name = p_name.strip()
                        party = Party.objects.filter(name__iexact=clean_p_name).first()
                        if not party:
                            party = Party.objects.filter(name__icontains=clean_p_name).first()

                    if not party:
                        if p_name:
                            party = Party.objects.create(
                                name=p_name,
                                phone=p_phone or f"01000{Party.objects.count() + 1:06d}",
                                party_type='customer',
                                address=str(item.get('address', '')),
                                opening_balance=Decimal('0.00'),
                                total_due=Decimal('0.00'),
                                total_sales=Decimal('0.00')
                            )
                        else:
                            errors.append(f"রো #{idx + 1}: কাস্টমার চিহ্নিত করা যায়নি।")
                            continue

                    affected_parties.add(party)

                    # 2. Parse Date & Details
                    entry_date = parse_date(item.get('date') or item.get('created_at'))
                    d_str = entry_date.strftime('%Y%m%d')

                    desc = str(item.get('description') or item.get('particulars') or item.get('product_name') or '').strip()
                    note_text = str(item.get('note') or item.get('notes') or item.get('remarks') or '').strip()
                    inv_no = str(item.get('invoice_no') or item.get('voucher_no') or item.get('ref_no') or '').strip()
                    method = str(item.get('payment_method') or 'cash').strip().lower()
                    if 'bank' in method or 'ব্যাংক' in method:
                        method = 'bank'
                    elif 'cheque' in method or 'চেক' in method:
                        method = 'cheque'
                    elif 'bkash' in method or 'nagad' in method or 'মোবাইল' in method:
                        method = 'mobile_banking'
                    else:
                        method = 'cash'

                    try:
                        debit = Decimal(str(item.get('debit', 0) or item.get('bill_amount', 0) or item.get('sale_amount', 0) or 0))
                    except Exception:
                        debit = Decimal('0.00')

                    try:
                        credit = Decimal(str(item.get('credit', 0) or item.get('paid_amount', 0) or item.get('deposit_amount', 0) or 0))
                    except Exception:
                        credit = Decimal('0.00')

                    try:
                        qty = Decimal(str(item.get('quantity', 1) or 1))
                    except Exception:
                        qty = Decimal('1.00')

                    try:
                        rate = Decimal(str(item.get('rate', 0) or item.get('price', 0) or 0))
                    except Exception:
                        rate = Decimal('0.00')

                    unit = str(item.get('unit') or 'টি').strip()

                    # Check if Opening Balance
                    is_opening = (
                        'opening' in desc.lower() or
                        'প্রারম্ভিক' in desc or
                        'পূর্বের জের' in desc or
                        'পূর্বের বকেয়া' in desc or
                        'পূর্বের বকেয়া' in desc or
                        item.get('type') == 'opening'
                    )

                    if is_opening:
                        op_amt = debit if debit > 0 else (credit if credit > 0 else Decimal('0.00'))
                        if op_amt > 0:
                            party.opening_balance = op_amt
                            party.save(update_fields=['opening_balance'])
                        continue

                    notes_meta = {
                        'isHistoricalLedger': True,
                        'userNote': note_text or desc or 'পূর্বের খতিয়ান এন্ট্রি'
                    }

                    # Sale / Bill entry
                    if debit > 0:
                        base_inv = inv_no or f"INV-LEG-{party.id}-{d_str}-{idx+1:03d}"
                        unique_inv = base_inv
                        c = 1
                        while Transaction.objects.filter(invoice_no=unique_inv).exists():
                            unique_inv = f"{base_inv}-{c}"
                            c += 1

                        due = max(Decimal('0.00'), debit - credit)
                        tx = Transaction.objects.create(
                            party=party,
                            party_name=party.name,
                            party_phone=party.phone,
                            transaction_type='sale',
                            status='completed',
                            subtotal=debit,
                            total_amount=debit,
                            paid_amount=credit,
                            due_amount=due,
                            payment_method=method,
                            invoice_no=unique_inv,
                            created_at=entry_date,
                            notes=json.dumps(notes_meta)
                        )
                        created_transactions_count += 1

                        TransactionItem.objects.create(
                            transaction=tx,
                            product=None,
                            product_name=desc or 'পণ্য বিক্রয়',
                            quantity=qty if qty > 0 else Decimal('1.00'),
                            price=rate if rate > 0 else debit,
                            unit=unit,
                            total=debit
                        )

                    elif credit > 0:
                        base_inv = inv_no or f"RCV-LEG-{party.id}-{d_str}-{idx+1:03d}"
                        unique_inv = base_inv
                        c = 1
                        while Transaction.objects.filter(invoice_no=unique_inv).exists():
                            unique_inv = f"{base_inv}-{c}"
                            c += 1

                        Transaction.objects.create(
                            party=party,
                            party_name=party.name,
                            party_phone=party.phone,
                            transaction_type='payment_in',
                            status='completed',
                            subtotal=Decimal('0.00'),
                            total_amount=credit,
                            paid_amount=credit,
                            due_amount=Decimal('0.00'),
                            payment_method=method,
                            invoice_no=unique_inv,
                            created_at=entry_date,
                            notes=json.dumps(notes_meta)
                        )
                        created_transactions_count += 1

            # 3. Synchronize party total_sales, total_due, and advance_balance
            from .serializers import recalculate_party_balances
            for party in affected_parties:
                recalculate_party_balances(party)

        return Response({
            'success': True,
            'created_count': created_transactions_count,
            'affected_parties_count': len(affected_parties),
            'errors': errors
        }, status=status.HTTP_200_OK)

class CustomerSiteViewSet(viewsets.ModelViewSet):
    queryset = CustomerSite.objects.all().order_by('-created_at')
    serializer_class = CustomerSiteSerializer
    permission_classes = [RoleBasedAccessPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        customer_id = self.request.query_params.get('customer') or self.request.query_params.get('customer_id') or self.request.query_params.get('party')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search) |
                Q(contact_person__icontains=search) |
                Q(contact_phone__icontains=search)
            )
        return qs

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [RoleBasedAccessPermission]

from rest_framework.decorators import action
from .services import recalculate_product_stock_and_cost, generate_product_cost_log

def apply_product_custom_ordering(qs):
    cat_order = Case(
        When(Q(category_name='রড') | Q(category__name='রড') | Q(name__icontains='রড') | Q(brand__iexact='BSRM') | Q(brand__iexact='SCRM') | Q(brand__iexact='SCRM TMX') | Q(brand__iexact='KSML') | Q(brand__iexact='HKG') | Q(brand__iexact='DSRM'), then=Value(1)),
        When(Q(category_name='রিং') | Q(category__name='রিং') | Q(name__icontains='রিং') | Q(name__icontains='ring'), then=Value(2)),
        When(Q(category_name='সিমেন্ট') | Q(category__name='সিমেন্ট') | Q(name__icontains='সিমেন্ট') | Q(name__icontains='cement') | Q(brand__icontains='Holcim') | Q(brand__icontains='King') | Q(brand__icontains='Aman'), then=Value(3)),
        default=Value(4),
        output_field=IntegerField()
    )

    sub_order = Case(
        # Rods: BSRM (1), SCRM (2), SCRM TMX (3), KSML (4), HKG (5), DSRM (6)
        When(Q(brand__iexact='BSRM') | Q(name__icontains='BSRM'), then=Value(10)),
        When(Q(brand__iexact='SCRM TMX') | Q(name__icontains='SCRM TMX') | Q(name__icontains='TMX'), then=Value(30)),
        When(Q(brand__iexact='SCRM') | Q(name__icontains='SCRM'), then=Value(20)),
        When(Q(brand__iexact='KSML') | Q(name__icontains='KSML'), then=Value(40)),
        When(Q(brand__iexact='HKG') | Q(name__icontains='HKG'), then=Value(50)),
        When(Q(brand__iexact='DSRM') | Q(name__icontains='DSRM'), then=Value(60)),

        # Rings: 3-3, 3-4, 3-7, 7-7, 7-9, Pistol
        When(Q(name__icontains='3-3') | Q(name__icontains='3*3') | Q(name__icontains='3x3') | Q(name__icontains='৩-৩'), then=Value(100)),
        When(Q(name__icontains='3-4') | Q(name__icontains='3*4') | Q(name__icontains='3x4') | Q(name__icontains='৩-৪'), then=Value(110)),
        When(Q(name__icontains='3-7') | Q(name__icontains='3*7') | Q(name__icontains='3x7') | Q(name__icontains='৩-৭'), then=Value(120)),
        When(Q(name__icontains='7-7') | Q(name__icontains='7*7') | Q(name__icontains='7x7') | Q(name__icontains='৭-৭'), then=Value(130)),
        When(Q(name__icontains='7-9') | Q(name__icontains='7*9') | Q(name__icontains='7x9') | Q(name__icontains='৭-৯'), then=Value(140)),
        When(Q(name__icontains='pistol') | Q(name__icontains='পিস্তল'), then=Value(150)),

        # Cements: Strong Structure, Supercrete, Supercrete Plus, Coastal Guard, Waterprotect, King Brand, Aman
        When(Q(name__icontains='Strong Structure') | Q(name__icontains='স্ট্রং স্ট্রাকচার'), then=Value(200)),
        When(Q(name__icontains='Supercrete Plus') | Q(name__icontains='সুপারক্রিট প্লাস'), then=Value(220)),
        When(Q(name__icontains='Supercrete') | Q(name__icontains='সুপারক্রিট'), then=Value(210)),
        When(Q(name__icontains='Coastal Guard') | Q(name__icontains='কোস্টাল গার্ড'), then=Value(230)),
        When(Q(name__icontains='Waterprotect') | Q(name__icontains='ওয়াটারপ্রটেক্ট'), then=Value(240)),
        When(Q(brand__icontains='King Brand') | Q(name__icontains='King Brand') | Q(name__icontains='কিং ব্র্যান্ড'), then=Value(250)),
        When(Q(brand__icontains='Aman') | Q(name__icontains='Aman') | Q(name__icontains='আমান'), then=Value(260)),

        default=Value(999),
        output_field=IntegerField()
    )

    size_order = Case(
        When(Q(name__icontains='৮ মিলি') | Q(name__icontains='8mm') | Q(name__icontains='8 মিলি') | Q(name__icontains='8 মি.লি') | Q(name__icontains='8মি.লি'), then=Value(8)),
        When(Q(name__icontains='১০ মিলি') | Q(name__icontains='10mm') | Q(name__icontains='10 মিলি') | Q(name__icontains='10 মি.লি') | Q(name__icontains='10মি.লি'), then=Value(10)),
        When(Q(name__icontains='১২ মিলি') | Q(name__icontains='12mm') | Q(name__icontains='12 মিলি') | Q(name__icontains='12 মি.লি') | Q(name__icontains='12মি.লি'), then=Value(12)),
        When(Q(name__icontains='১৬ মিলি') | Q(name__icontains='16mm') | Q(name__icontains='16 মিলি') | Q(name__icontains='16 মি.লি') | Q(name__icontains='16মি.লি'), then=Value(16)),
        When(Q(name__icontains='২০ মিলি') | Q(name__icontains='20mm') | Q(name__icontains='20 মিলি') | Q(name__icontains='20 মি.লি') | Q(name__icontains='20মি.লি'), then=Value(20)),
        When(Q(name__icontains='২৫ মিলি') | Q(name__icontains='25mm') | Q(name__icontains='25 মিলি') | Q(name__icontains='25 মি.লি') | Q(name__icontains='25মি.লি'), then=Value(25)),
        default=Value(999),
        output_field=IntegerField()
    )

    return qs.annotate(
        cat_order=cat_order,
        sub_order=sub_order,
        size_order=size_order
    ).order_by('cat_order', 'sub_order', 'size_order', 'name')

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [RoleBasedAccessPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        low_stock = self.request.query_params.get('low_stock')
        category_id = self.request.query_params.get('category')
        search = self.request.query_params.get('search')

        if low_stock == 'true':
            qs = qs.filter(stock__lte=F('min_stock'))

        if category_id:
            qs = qs.filter(category_id=category_id)

        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(brand__icontains=search)
            )

        return apply_product_custom_ordering(qs)

    @action(detail=False, methods=['get'], url_path='cost_logs')
    def cost_logs(self, request):
        product_id = request.query_params.get('product_id')
        if product_id:
            data = generate_product_cost_log(product_id)
            return Response(data if data else {'error': 'পণ্য খুঁজে পাওয়া যায়নি'}, status=status.HTTP_200_OK if data else status.HTTP_404_NOT_FOUND)
        
        # If no product_id specified, return logs for all products with transactions
        all_logs = []
        for p in Product.objects.all().order_by('name'):
            p_log = generate_product_cost_log(p)
            if p_log and p_log['logs']:
                all_logs.append(p_log)
        return Response(all_logs, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        products_data = request.data.get('products', [])
        if not isinstance(products_data, list):
            return Response({'error': 'products must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        updated_count = 0
        errors = []

        with transaction.atomic():
            for idx, item in enumerate(products_data):
                name = str(item.get('name', '')).strip()
                if not name:
                    errors.append(f"রো #{idx + 1}: পণ্যের নাম প্রদান করা আবশ্যক।")
                    continue

                category_name = str(item.get('category_name', '') or item.get('category', '') or '').strip()
                category = None
                if category_name:
                    category, _ = Category.objects.get_or_create(name=category_name)

                try:
                    stock = Decimal(str(item.get('stock', 0) or 0))
                except Exception:
                    stock = Decimal('0.00')

                try:
                    min_stock = Decimal(str(item.get('min_stock', 5) or 5))
                except Exception:
                    min_stock = Decimal('5.00')

                try:
                    purchase_price = Decimal(str(item.get('purchase_price', 0) or 0))
                except Exception:
                    purchase_price = Decimal('0.00')

                try:
                    sell_price = Decimal(str(item.get('sell_price', 0) or 0))
                except Exception:
                    sell_price = Decimal('0.00')

                unit = str(item.get('unit', 'পিস') or 'পিস').strip()
                sku = str(item.get('sku', '') or '').strip() or None
                brand = str(item.get('brand', '') or '').strip()

                product = None
                if sku:
                    product = Product.objects.filter(sku=sku).first()
                if not product:
                    product = Product.objects.filter(name__iexact=name).first()

                if product:
                    product.stock = stock
                    product.purchase_price = purchase_price
                    product.sell_price = sell_price
                    if category:
                        product.category = category
                        product.category_name = category.name
                    if unit:
                        product.unit = unit
                    if brand:
                        product.brand = brand
                    product.save()
                    updated_count += 1
                else:
                    Product.objects.create(
                        name=name,
                        sku=sku,
                        category=category,
                        category_name=category.name if category else '',
                        stock=stock,
                        min_stock=min_stock,
                        unit=unit,
                        purchase_price=purchase_price,
                        sell_price=sell_price,
                        brand=brand
                    )
                    created_count += 1

        return Response({
            'success': True,
            'created_count': created_count,
            'updated_count': updated_count,
            'errors': errors
        }, status=status.HTTP_200_OK)

class BankViewSet(viewsets.ModelViewSet):
    queryset = Bank.objects.all().order_by('name')
    serializer_class = BankSerializer
    permission_classes = [RoleBasedAccessPermission]

from .services import recalculate_product_stock_and_cost

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer
    permission_classes = [RoleBasedAccessPermission]
    is_transaction_view = True

    def get_queryset(self):
        qs = super().get_queryset()
        transaction_type = self.request.query_params.get('transaction_type')
        party_id = self.request.query_params.get('party')
        cheque_status = self.request.query_params.get('cheque_status')
        search = self.request.query_params.get('search')

        if transaction_type:
            qs = qs.filter(transaction_type=transaction_type)

        if party_id:
            qs = qs.filter(party_id=party_id)

        if cheque_status:
            qs = qs.filter(cheque_status=cheque_status)

        if search:
            qs = qs.filter(
                Q(invoice_no__icontains=search) |
                Q(party_name__icontains=search) |
                Q(party_phone__icontains=search) |
                Q(cheque_number__icontains=search)
            )

        # Historical ledger entries should strictly only be visible in party-specific history/ledger views
        # Never in general orders, sales lists, transactions lists, or dashboards
        include_historical = self.request.query_params.get('include_historical')
        if include_historical == 'false':
            qs = qs.exclude(notes__contains='isHistoricalLedger')
        elif include_historical != 'true' and not party_id:
            qs = qs.exclude(notes__contains='isHistoricalLedger')

        return qs

    def update(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role != 'developer':
            return Response({'detail': 'ইনভয়েস বা লেনদেন সম্পাদনা (Edit) করার অনুমতি শুধুমাত্র ডেভেলপার (Developer) এর রয়েছে।'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role != 'developer':
            return Response({'detail': 'ইনভয়েস বা লেনদেন সম্পাদনা (Edit) করার অনুমতি শুধুমাত্র ডেভেলপার (Developer) এর রয়েছে।'}, status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        role = get_user_role(request.user)
        if role != 'developer':
            return Response({'detail': 'ইনভয়েস বা লেনদেন মুছে ফেলার (Delete) অনুমতি শুধুমাত্র ডেভেলপার (Developer) এর রয়েছে।'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        role = get_user_role(request.user)
        if role not in ['admin', 'developer']:
            return Response({'detail': 'ইনভয়েস অনুমোদন (Approve) করার অনুমতি শুধুমাত্র অ্যাডমিন (Admin) বা ডেভেলপার (Developer) এর রয়েছে।'}, status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        if instance.status in ['completed', 'approved']:
            return Response({'detail': 'ইনভয়েসটি ইতিমধ্যে অনুমোদিত হয়েছে', 'status': instance.status}, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(instance, data={'status': 'approved'}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'ইনভয়েস সফলভাবে অনুমোদন করা হয়েছে', 'data': serializer.data}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        from .serializers import recalculate_party_balances, recalculate_product_stock_and_cost
        old_party = Party.objects.filter(id=instance.party_id).first() if instance.party_id else None
        was_active = instance.status not in ['pending', 'draft', 'cancelled', 'rejected']

        affected_product_ids = set(instance.items.exclude(product__isnull=True).values_list('product_id', flat=True))
        for item in instance.items.filter(product__isnull=True):
            if item.product_name:
                matched_p = Product.objects.filter(name__iexact=item.product_name.strip()).first()
                if matched_p:
                    affected_product_ids.add(matched_p.id)

        instance.delete()

        if old_party and was_active:
            recalculate_party_balances(old_party)

        if was_active:
            for pid in affected_product_ids:
                recalculate_product_stock_and_cost(pid)

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all().order_by('name')
    serializer_class = ExpenseCategorySerializer
    permission_classes = [RoleBasedAccessPermission]

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-date', '-created_at')
    serializer_class = ExpenseSerializer
    permission_classes = [RoleBasedAccessPermission]

    def get_queryset(self):
        qs = super().get_queryset()
        category_id = self.request.query_params.get('category')
        search = self.request.query_params.get('search')

        if category_id:
            qs = qs.filter(category_id=category_id)

        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(category_name__icontains=search) |
                Q(reference_no__icontains=search)
            )

        return qs

    @action(detail=False, methods=['post'], url_path='bulk-import')
    def bulk_import(self, request):
        expenses_data = request.data.get('expenses', [])
        if not isinstance(expenses_data, list):
            return Response({'error': 'expenses must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        created_count = 0
        errors = []

        with transaction.atomic():
            for idx, item in enumerate(expenses_data):
                title = str(item.get('title', '')).strip()
                if not title:
                    errors.append(f"রো #{idx + 1}: খরচের বিবরণ প্রদান করা আবশ্যক।")
                    continue

                category_name = str(item.get('category_name', '') or item.get('category', 'সাধারণ খরচ') or 'সাধারণ খরচ').strip()
                cat, _ = ExpenseCategory.objects.get_or_create(name=category_name)

                try:
                    amount = Decimal(str(item.get('amount', 0) or 0))
                except Exception:
                    amount = Decimal('0.00')

                date_str = item.get('date')
                payment_method = str(item.get('payment_method', 'ক্যাশ') or 'ক্যাশ').strip()

                expense = Expense(
                    title=title,
                    category=cat,
                    category_name=cat.name,
                    amount=amount,
                    payment_method=payment_method,
                    notes=item.get('notes', '')
                )
                if date_str:
                    expense.date = date_str
                expense.save()
                created_count += 1

        return Response({
            'success': True,
            'created_count': created_count,
            'errors': errors
        }, status=status.HTTP_200_OK)

class DashboardStatsView(APIView):
    """
    High performance server-side aggregator for instant ERP Dashboard loading.
    """
    permission_classes = [RoleBasedAccessPermission]

    def get(self, request):
        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sales aggregates (excluding pending / unapproved and historical ledger import)
        sales_qs = Transaction.objects.filter(transaction_type='sale').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected']).exclude(notes__contains='isHistoricalLedger')
        total_sales = sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0
        sales_paid = sales_qs.aggregate(total=Sum('paid_amount'))['total'] or 0
        # Customer total due should reflect actual Party accounts
        customer_dues = Party.objects.filter(party_type='customer').aggregate(total=Sum('total_due'))['total'] or 0
        customer_advances = Party.objects.filter(party_type='customer').aggregate(total=Sum('advance_balance'))['total'] or 0
        total_dues = customer_dues
        total_advances = customer_advances
        monthly_sales = sales_qs.filter(created_at__gte=first_day_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

        # Purchase aggregates (excluding pending / unapproved)
        purchases_qs = Transaction.objects.filter(transaction_type='purchase').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
        total_purchases = purchases_qs.aggregate(total=Sum('total_amount'))['total'] or 0
        purchases_paid = purchases_qs.aggregate(total=Sum('paid_amount'))['total'] or 0
        monthly_purchases = purchases_qs.filter(created_at__gte=first_day_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

        # Expense aggregates
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        monthly_expenses = Expense.objects.filter(date__gte=first_day_of_month.date()).aggregate(total=Sum('amount'))['total'] or 0

        # Cash & Bank Balance (Unified real calculation)
        from .serializers import get_available_balances
        cash_balance, bank_balance = get_available_balances()
        total_cash = float(cash_balance)
        total_bank = float(bank_balance)

        # Inventory Low Stock
        low_stock_count = Product.objects.filter(stock__lte=F('min_stock')).count()
        total_products_count = Product.objects.count()

        # Last 7 Days Sales & Purchase Trend
        weekly_data = []
        bn_days = {0: 'সোম', 1: 'মঙ্গল', 2: 'বুধ', 3: 'বৃহস্পতি', 4: 'শুক্র', 5: 'শনি', 6: 'রবি'}
        today = now.date()
        for i in range(6, -1, -1):
            day_date = today - timedelta(days=i)
            day_name = bn_days[day_date.weekday()]
            
            day_sales = Transaction.objects.filter(
                transaction_type='sale',
                created_at__date=day_date
            ).exclude(status__in=['pending', 'draft', 'cancelled', 'rejected']).aggregate(total=Sum('total_amount'))['total'] or 0

            day_purchases = Transaction.objects.filter(
                transaction_type='purchase',
                created_at__date=day_date
            ).exclude(status__in=['pending', 'draft', 'cancelled', 'rejected']).aggregate(total=Sum('total_amount'))['total'] or 0

            weekly_data.append({
                'name': day_name,
                'বিক্রয়': float(day_sales),
                'ক্রয়': float(day_purchases)
            })

        # Recent Transactions
        recent_txs = Transaction.objects.all().order_by('-created_at')[:10]
        recent_tx_serializer = TransactionSerializer(recent_txs, many=True)

        return Response({
            'totalSales': float(total_sales),
            'monthlySales': float(monthly_sales),
            'totalPurchases': float(total_purchases),
            'monthlyPurchases': float(monthly_purchases),
            'totalDues': float(total_dues),
            'totalAdvances': float(total_advances),
            'totalExpenses': float(total_expenses),
            'monthlyExpenses': float(monthly_expenses),
            'totalCash': total_cash,
            'totalBank': total_bank,
            'lowStockCount': low_stock_count,
            'totalProductsCount': total_products_count,
            'weeklyData': weekly_data,
            'recentTransactions': recent_tx_serializer.data,
        })

class HawlatViewSet(viewsets.ModelViewSet):
    queryset = Hawlat.objects.all().order_by('-created_at')
    serializer_class = HawlatSerializer
    permission_classes = [RoleBasedAccessPermission]


# ==========================================
# AUTHENTICATION & USER MANAGEMENT API VIEWS
# ==========================================

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        def to_en_digits(val):
            if not val:
                return ''
            val = str(val).strip()
            bn = "০১২৩৪৫৬৭৮৯"
            en = "0123456789"
            for b, e in zip(bn, en):
                val = val.replace(b, e)
            return val

        raw_id = str(
            request.data.get('email') or 
            request.data.get('username') or 
            request.data.get('identifier') or 
            ''
        ).strip()
        raw_pass = str(request.data.get('password') or '').strip()

        identifier = to_en_digits(raw_id)
        password = to_en_digits(raw_pass)

        if not identifier or not raw_pass:
            return Response({'detail': 'আপনার অনুমোদিত জিমেইল (Gmail) এবং পাসওয়ার্ড প্রদান করুন।'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Lookup by Email / Gmail
        user = User.objects.filter(email__iexact=identifier).first() or User.objects.filter(email__iexact=raw_id).first()

        # 2. Lookup by Username (backward compatibility)
        if not user:
            user = User.objects.filter(username__iexact=identifier).first() or User.objects.filter(username__iexact=raw_id).first()

        # 3. Lookup by Profile Phone
        if not user:
            profile = UserProfile.objects.filter(phone=identifier).first() or UserProfile.objects.filter(phone=raw_id).first()
            if profile:
                user = profile.user

        # If user does not exist or has no access in the system
        if not user:
            return Response({
                'detail': 'এই জিমেইল অ্যাকাউন্টে প্রবেশের কোনো অনুমতি (অ্যাক্সেস) দেওয়া হয়নি। অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করে অ্যাক্সেস নিন।'
            }, status=status.HTTP_403_FORBIDDEN)

        # If user account is deactivated / access revoked
        if not user.is_active or (hasattr(user, 'profile') and user.profile and not user.profile.is_active):
            return Response({
                'detail': 'আপনার জিমেইল অ্যাকাউন্টটির অ্যাক্সেস বন্ধ/নিষ্ক্রিয় করা হয়েছে। অ্যাডমিনের সাথে যোগাযোগ করুন।'
            }, status=status.HTTP_403_FORBIDDEN)

        # Check password correctness
        if not (user.check_password(raw_pass) or user.check_password(password)):
            return Response({
                'detail': 'পাসওয়ার্ড ভুল হয়েছে! সঠিক পাসওয়ার্ড দিন।'
            }, status=status.HTTP_401_UNAUTHORIZED)

        token, _ = Token.objects.get_or_create(user=user)
        serializer = UserSerializer(user)
        return Response({
            'token': token.key,
            'user': serializer.data,
            'message': 'সফলভাবে লগইন হয়েছে।'
        }, status=status.HTTP_200_OK)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            if hasattr(request.user, 'auth_token'):
                request.user.auth_token.delete()
        except Exception:
            pass
        logout(request)
        return Response({'message': 'সফলভাবে লগআউট হয়েছে।'}, status=status.HTTP_200_OK)


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    Admin-only endpoint for managing Dokan ERP users (Admin, Manager, Staff, Developer).
    Allows giving Gmail access, revoking access (is_active), and assigning specific roles.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUserOnly]

    def create(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        role = request.data.get('role', 'staff').strip()
        full_name = request.data.get('full_name', '').strip()
        phone = request.data.get('phone', '').strip()
        is_active = request.data.get('is_active', True)

        if isinstance(is_active, str):
            is_active = is_active.lower() in ('true', '1', 'yes')

        if not password:
            return Response({'detail': 'পাসওয়ার্ড প্রদান করা আবশ্যক।'}, status=status.HTTP_400_BAD_REQUEST)

        if not email and not username:
            return Response({'detail': 'অনুমোদিত জিমেইল (Gmail) অথবা ইউজারনেম দিন।'}, status=status.HTTP_400_BAD_REQUEST)

        # Check unique email
        if email and User.objects.filter(email__iexact=email).exists():
            return Response({'detail': f"'{email}' জিমেইলটি ইতিমধ্যে সিস্টেমে তালিকাভুক্ত রয়েছে।"}, status=status.HTTP_400_BAD_REQUEST)

        # Auto-generate username from email if not provided
        if not username and email:
            base_username = email.split('@')[0].replace('.', '_').replace('-', '_')
            username = base_username
            counter = 1
            while User.objects.filter(username__iexact=username).exists():
                username = f"{base_username}_{counter}"
                counter += 1

        if User.objects.filter(username__iexact=username).exists():
            return Response({'detail': f"'{username}' ইউজারনেম ইতিমধ্যে ব্যবহার করা হয়েছে। অন্য নাম দিন।"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=full_name
        )
        user.is_active = bool(is_active)

        if role == 'developer':
            user.is_staff = True
            user.is_superuser = True
        elif role == 'admin':
            user.is_staff = True
            user.is_superuser = False
        else:
            user.is_staff = False
            user.is_superuser = False
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.full_name = full_name
        profile.phone = phone
        profile.is_active = bool(is_active)
        profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        role = request.data.get('role')
        full_name = request.data.get('full_name')
        phone = request.data.get('phone')
        password = request.data.get('password')
        email = request.data.get('email')
        is_active = request.data.get('is_active')

        if password and str(password).strip():
            user.set_password(str(password).strip())

        if email is not None:
            email = email.strip().lower()
            if email and User.objects.filter(email__iexact=email).exclude(id=user.id).exists():
                return Response({'detail': f"'{email}' জিমেইলটি ইতিমধ্যে অন্য ব্যবহারকারীর জন্য ব্যবহৃত হয়েছে।"}, status=status.HTTP_400_BAD_REQUEST)
            user.email = email

        if full_name is not None:
            user.first_name = full_name.strip()

        if is_active is not None:
            if isinstance(is_active, str):
                is_active = is_active.lower() in ('true', '1', 'yes')
            user.is_active = bool(is_active)

        if role:
            if role == 'developer':
                user.is_superuser = True
                user.is_staff = True
            elif role == 'admin':
                user.is_superuser = False
                user.is_staff = True
            elif role == 'manager':
                user.is_superuser = False
                user.is_staff = False
            else:
                user.is_superuser = False
                user.is_staff = False
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if role:
            profile.role = role
        if full_name is not None:
            profile.full_name = full_name.strip()
        if phone is not None:
            profile.phone = phone.strip()
        if is_active is not None:
            profile.is_active = bool(is_active)
        profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'আপনি নিজের এডমিন একাউন্ট ডিলিট করতে পারবেন না।'}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({'detail': 'ব্যবহারকারী সফলভাবে মুছে ফেলা হয়েছে।'}, status=status.HTTP_204_NO_CONTENT)



