from decimal import Decimal
from rest_framework import serializers
from .models import (
    ShopSettings,
    Party,
    Category,
    Product,
    Bank,
    Transaction,
    TransactionItem,
    ExpenseCategory,
    Expense,
    Hawlat
)

class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        fields = '__all__'

class PartySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Party
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    category_detail = CategorySerializer(source='category', read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

class BankSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = '__all__'

class RoundedDecimalField(serializers.DecimalField):
    def to_internal_value(self, data):
        if data is None or data == '':
            return None
        try:
            val = Decimal(str(data))
            rounded_val = val.quantize(Decimal('0.01'))
            return super().to_internal_value(rounded_val)
        except Exception:
            return super().to_internal_value(data)

class TransactionItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    quantity = RoundedDecimalField(max_digits=10, decimal_places=2, required=False)
    price = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    total = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    sell_price = RoundedDecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)

    class Meta:
        model = TransactionItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'sell_price', 'unit', 'total']

import re

import re

def normalize_bn_en_digits(text):
    if not text:
        return ""
    bn_digits = '০১২৩৪৫৬৭৮৯'
    en_digits = '0123456789'
    res = text
    for b, e in zip(bn_digits, en_digits):
        res = res.replace(b, e)
    return res

def find_or_create_product_for_purchase(item_name, unit, price, brand_param=None, sell_price=None):
    from .models import Product, Category
    if not item_name or not item_name.strip():
        return None

    raw_name = item_name.strip()
    # Remove duplicate consecutive repeating words e.g. "সিমেন্ট সিমেন্ট" -> "সিমেন্ট"
    cleaned_name = re.sub(r'(\b\S+\b)(?:\s+\1)+', r'\1', raw_name, flags=re.IGNORECASE)
    cleaned_norm = normalize_bn_en_digits(cleaned_name.lower())

    # 1. Direct Name Match or Cleaned Name Match
    exact_match = Product.objects.filter(name__iexact=raw_name).first() or Product.objects.filter(name__iexact=cleaned_name).first()
    if exact_match:
        return exact_match

    # Extract MM (Rod)
    mm_match = re.search(r'(\b\d{1,2}(?:\.\d+)?)\s*(?:mm|মিমি|মিলি)\b', cleaned_norm)
    mm_val = (mm_match.group(1) + 'mm') if mm_match else None
    if not mm_val and ('rod' in cleaned_norm or 'রড' in cleaned_norm):
        size_num = re.search(r'\b(8|10|12|16|20|22|25|32)\b', cleaned_norm)
        if size_num:
            mm_val = size_num.group(1) + 'mm'

    # Extract Size (Ring/Angle)
    size_match = re.search(r'(\d+(?:\.\d+)?(?:\s*["\']|\s*inch|\s*ইঞ্চি|\s*x\s*\d+|\s*×\s*\d+)?)\b', cleaned_norm)
    size_val = size_match.group(1) if size_match else None

    # Detect Brand dictionary in Bengali and English
    brand_dictionary = {
        'shah': ['shah', 'শাহ'],
        'bsrm': ['bsrm', 'বিএসআরএম', 'বি এস আর এম'],
        'ksrm': ['ksrm', 'কেএসআরএম', 'কে এস আর এম'],
        'aks': ['aks', 'একেএস', 'এ কে এস'],
        'gph': ['gph', 'জিপিএইচ', 'জি পি এইচ'],
        'anwar': ['anwar', 'আনোয়ার'],
        'seven rings': ['seven rings', 'sevenring', 'সেভেন রিংস', 'সেভেন রিং'],
        'supercream': ['supercream', 'সুপারক্রিম', 'সুপারক্যাপ'],
        'holcim': ['holcim', 'হোলসিম'],
        'fresh': ['fresh', 'ফ্রেশ'],
        'premier': ['premier', 'প্রিমিয়ার'],
        'crown': ['crown', 'ক্রাউন'],
        'akij': ['akij', 'আকিজ'],
        'king brand': ['king brand', 'কিং ব্র্যান্ড']
    }

    matched_brand_tokens = []
    for brand_key, aliases in brand_dictionary.items():
        if any(alias in cleaned_norm for alias in aliases):
            matched_brand_tokens = aliases
            break

    # Determine Category Head
    if 'rod' in cleaned_norm or 'রড' in cleaned_norm or mm_val:
        category_head = 'রড'
    elif 'cement' in cleaned_norm or 'সিমেন্ট' in cleaned_norm or any(alias in cleaned_norm for alias in brand_dictionary['shah'] + brand_dictionary['seven rings'] + brand_dictionary['holcim'] + brand_dictionary['fresh']):
        category_head = 'সিমেন্ট'
    elif 'ring' in cleaned_norm or 'রিং' in cleaned_norm or 'angle' in cleaned_norm or 'অ্যাঙ্গেল' in cleaned_norm:
        category_head = 'রিং'
    else:
        category_head = 'অন্যান্য'

    candidate_qs = Product.objects.all()

    # Match existing products
    for prod in candidate_qs:
        p_name_norm = normalize_bn_en_digits(prod.name.lower())
        p_brand_norm = normalize_bn_en_digits((prod.brand or '').lower())
        p_combined = f"{p_name_norm} {p_brand_norm}"

        # Check if product names normalized match
        clean_p_name = re.sub(r'(\b\S+\b)(?:\s+\1)+', r'\1', prod.name, flags=re.IGNORECASE)
        if cleaned_name.lower() == clean_p_name.lower():
            return prod

        if category_head == 'সিমেন্ট':
            if matched_brand_tokens:
                if any(alias in p_combined for alias in matched_brand_tokens):
                    return prod
            elif ('সিমেন্ট' in p_name_norm or (prod.category_name and 'সিমেন্ট' in prod.category_name)):
                brand_word = cleaned_name.replace('সিমেন্ট', '').strip().lower()
                if brand_word and brand_word in p_name_norm:
                    return prod

        elif category_head == 'রড':
            brand_matched = True
            if matched_brand_tokens:
                brand_matched = any(alias in p_combined for alias in matched_brand_tokens)

            mm_matched = True
            if mm_val:
                digit = mm_val.replace('mm', '')
                mm_matched = (digit in p_name_norm)

            if brand_matched and mm_matched:
                return prod

        elif category_head == 'রিং':
            brand_matched = True
            if matched_brand_tokens:
                brand_matched = any(alias in p_combined for alias in matched_brand_tokens)

            size_matched = True
            if size_val:
                size_digit = size_val.replace('"', '').replace("'", '').strip()
                size_matched = (size_digit in p_name_norm)

            if brand_matched and size_matched:
                return prod

    # If no existing product matched, create NEW product automatically with CLEANED NAME
    cat_obj = Category.objects.filter(name__iexact=category_head).first()
    if not cat_obj:
        cat_obj = Category.objects.create(name=category_head)

    sp = float(sell_price) if (sell_price and float(sell_price) > 0) else round((float(price or 0) * 1.1), 2)

    new_prod = Product.objects.create(
        name=cleaned_name,
        category=cat_obj,
        category_name=category_head,
        brand=brand_param or '',
        unit=unit or ('কেজি' if category_head == 'রড' else 'বস্তা' if category_head == 'সিমেন্ট' else 'পিস'),
        purchase_price=price or 0.00,
        sell_price=sp,
        stock=0.00
    )
    return new_prod


def get_available_balances(exclude_tx_id=None, exclude_expense_id=None):
    from django.db.models import Sum
    from .models import Transaction, Expense, Bank

    sales_qs = Transaction.objects.filter(transaction_type='sale').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
    purchases_qs = Transaction.objects.filter(transaction_type='purchase').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
    p_in_qs = Transaction.objects.filter(transaction_type='payment_in').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
    p_out_qs = Transaction.objects.filter(transaction_type='payment_out').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
    exp_qs = Expense.objects.all()

    if exclude_tx_id:
        sales_qs = sales_qs.exclude(id=exclude_tx_id)
        purchases_qs = purchases_qs.exclude(id=exclude_tx_id)
        p_in_qs = p_in_qs.exclude(id=exclude_tx_id)
        p_out_qs = p_out_qs.exclude(id=exclude_tx_id)

    if exclude_expense_id:
        exp_qs = exp_qs.exclude(id=exclude_expense_id)

    cash_in = Decimal('0.00')
    bank_in = Decimal('0.00')

    import json

    # Process all active sales and payment_in transactions
    for t in list(sales_qs) + list(p_in_qs):
        pm = (t.payment_method or 'cash').lower()
        paid = Decimal(str(t.paid_amount or 0))
        meta = {}
        if t.notes and t.notes.strip().startswith('{'):
            try:
                meta = json.loads(t.notes.split('\n')[0])
            except Exception:
                meta = {}

        if pm == 'split':
            # Split: Only the cash portion enters cash immediately
            c_part = Decimal(str(meta.get('cashPaidAmount') or meta.get('splitCashAmount') or 0))
            q_part = Decimal(str(meta.get('chequePaidAmount') or meta.get('splitChequeAmount') or 0))
            if c_part == 0 and q_part == 0:
                c_part = paid
            cash_in += c_part
            # Cheque portion ONLY enters cash balance once it is cleared/cashed
            if t.cheque_status == 'cleared':
                cash_in += q_part
        elif pm in ['cheque', 'check']:
            # Standalone cheque: ONLY enters balance once cashed/cleared
            if t.cheque_status == 'cleared':
                cash_in += paid
        elif pm in ['bank', 'banktobank', 'mobile_banking', 'mobile', 'bkash']:
            bank_in += paid
        else: # cash
            cash_in += paid
    
    # Calculate extra shipping and labor paid in cash from active purchases
    extra_purchase_cash_out = Decimal('0.00')
    for p in purchases_qs.filter(notes__startswith='{'):
        try:
            meta_p = json.loads(p.notes.split('\n')[0])
            s_p = Decimal(str(meta_p.get('shippingPaidAmount') or (meta_p.get('shippingCost') if meta_p.get('shippingStatus') == 'paid' else 0) or 0))
            l_p = Decimal(str(meta_p.get('laborPaidAmount') or (meta_p.get('laborCost') if meta_p.get('laborStatus') == 'paid' else 0) or 0))
            extra_purchase_cash_out += (s_p + l_p)
        except Exception:
            pass

    # Calculate extra cement loading paid in cash from active sales
    extra_sales_cash_out = Decimal('0.00')
    for s in sales_qs.filter(notes__startswith='{'):
        try:
            meta_s = json.loads(s.notes.split('\n')[0])
            c_p = Decimal(str(meta_s.get('cementLoadingPaidAmount') or (meta_s.get('cementLaborCost') if meta_s.get('cementLoadingPaid') else 0) or 0))
            extra_sales_cash_out += c_p
        except Exception:
            pass

    # Exclude any settlement payment_out/in transactions and duplicate expenses that duplicate purchase/sales notes
    filtered_p_out_qs = p_out_qs.exclude(notes__contains='গাড়ি ভাড়া').exclude(notes__contains='লেবার').exclude(notes__contains='লোডিং')
    filtered_p_in_qs = p_in_qs.exclude(notes__contains='গাড়ি ভাড়া').exclude(notes__contains='লেবার').exclude(notes__contains='লোডিং')
    filtered_exp_qs = exp_qs.exclude(title__contains='লোডিং চার্জ').exclude(title__contains='আনলোডিং চার্জ').exclude(title__contains='গাড়ি ভাড়া')

    cash_out = (
        (purchases_qs.filter(payment_method__in=['cash', 'split', None, '']).aggregate(tot=Sum('paid_amount'))['tot'] or Decimal('0.00')) +
        extra_purchase_cash_out +
        extra_sales_cash_out +
        (filtered_p_out_qs.filter(payment_method__in=['cash', 'split', None, '']).aggregate(tot=Sum('paid_amount'))['tot'] or Decimal('0.00')) +
        (filtered_exp_qs.filter(payment_method__in=['cash', 'split', None, '']).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00'))
    )
    cash_balance = cash_in - cash_out

    bank_out = (
        (purchases_qs.filter(payment_method__in=['bank', 'cheque', 'mobile_banking', 'mobile', 'bkash']).aggregate(tot=Sum('paid_amount'))['tot'] or Decimal('0.00')) +
        (filtered_p_out_qs.filter(payment_method__in=['bank', 'cheque', 'mobile_banking', 'mobile', 'bkash']).aggregate(tot=Sum('paid_amount'))['tot'] or Decimal('0.00')) +
        (filtered_exp_qs.filter(payment_method__in=['bank', 'cheque', 'mobile_banking', 'mobile', 'bkash']).aggregate(tot=Sum('amount'))['tot'] or Decimal('0.00'))
    )
    banks_initial = Bank.objects.aggregate(tot=Sum('balance'))['tot'] or Decimal('0.00')
    bank_balance = banks_initial + bank_in - bank_out

    return cash_balance, bank_balance


from .services import recalculate_product_stock_and_cost

class TransactionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    invoice_no = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    subtotal = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    discount = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    tax = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    total_amount = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    paid_amount = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    due_amount = RoundedDecimalField(max_digits=12, decimal_places=2, required=False)
    items = TransactionItemSerializer(many=True, required=False)

    class Meta:
        model = Transaction
        fields = '__all__'

    def validate(self, attrs):
        tx_type = attrs.get('transaction_type') or (self.instance.transaction_type if self.instance else None)
        paid_amt = attrs.get('paid_amount')
        if paid_amt is None and self.instance:
            paid_amt = self.instance.paid_amount
        paid_amt = Decimal(str(paid_amt or 0))

        pay_method = (attrs.get('payment_method') or (self.instance.payment_method if self.instance else 'cash') or 'cash').lower()
        curr_status = attrs.get('status') or (self.instance.status if self.instance else 'pending')

        # Enforce balance check on money outflows (purchase or payment_out) only when active/approved
        if tx_type in ['purchase', 'payment_out'] and curr_status not in ['pending', 'draft', 'cancelled', 'rejected']:
            exclude_id = self.instance.id if self.instance else None
            cash_bal, bank_bal = get_available_balances(exclude_tx_id=exclude_id)
            
            notes_val = attrs.get('notes') or (self.instance.notes if self.instance else '')
            meta = {}
            if notes_val and notes_val.strip().startswith('{'):
                try:
                    import json
                    meta = json.loads(notes_val.split('\n')[0])
                except Exception:
                    meta = {}

            is_bank_to_bank = 'banktobank' in pay_method or meta.get('paymentMethodName') == 'BankToBank' or 'bank_to_bank' in str(meta).lower()
            is_cheque = any(c in pay_method for c in ['cheque', 'check']) or meta.get('paymentMethodName') == 'Cheque'

            # Calculate additional cash paid for shipping and labor
            ship_paid = Decimal(str(meta.get('shippingPaidAmount') or (meta.get('shippingCost') if meta.get('shippingStatus') == 'paid' else 0) or 0))
            lab_paid = Decimal(str(meta.get('laborPaidAmount') or (meta.get('laborCost') if meta.get('laborStatus') == 'paid' else 0) or 0))
            extra_cash_expenses = ship_paid + lab_paid

            if is_bank_to_bank or is_cheque:
                # Bank-to-Bank and Cheque: Check the specifically selected bank account for goods payment
                target_bank = None
                bank_id = meta.get('bankId') or meta.get('bank_id')
                bank_name = meta.get('selectedShopBank') or meta.get('bankName') or meta.get('chequeBank')
                if bank_id:
                    target_bank = Bank.objects.filter(id=int(bank_id)).first()
                elif bank_name:
                    clean_bn = str(bank_name).split(' - ')[0].split(' (')[0].strip()
                    target_bank = Bank.objects.filter(name__icontains=clean_bn).first()

                avail_balance = target_bank.balance if target_bank else bank_bal
                bank_label = f"'{target_bank.name}'" if target_bank else "ব্যাংক"
                if paid_amt > avail_balance:
                    raise serializers.ValidationError({
                        'paid_amount': f"পর্যাপ্ত ব্যাংক ব্যালেন্স নেই! (নির্বাচিত {bank_label} একাউন্ট ব্যালেন্স: ৳ {avail_balance:,.2f}, পেমেন্ট দিতে চাচ্ছেন: ৳ {paid_amt:,.2f})। অনুগ্রহ করে আগে এই ব্যাংক একাউন্টে ব্যালেন্স জমা করুন অথবা বাকি চালান হিসেবে কাটুন।"
                    })
                
                # Check cash balance for shipping and labor if paid in cash
                if extra_cash_expenses > 0 and extra_cash_expenses > cash_bal:
                    raise serializers.ValidationError({
                        'paid_amount': f"পর্যাপ্ত নগদ ক্যাশ ব্যালেন্স নেই! (বর্তমান ক্যাশ ব্যালেন্স: ৳ {cash_bal:,.2f}, গাড়ি ভাড়া ও লেবার বাবদ নগদ পরিশোধ করতে চাচ্ছেন: ৳ {extra_cash_expenses:,.2f} [গাড়ি ভাড়া: ৳ {ship_paid:,.2f}, লেবার: ৳ {lab_paid:,.2f}])। ক্যাশে পর্যাপ্ত ব্যালেন্স না থাকলে গাড়ি ভাড়া/লেবার নগদ পরিশোধ করা যাবে না।"
                    })
            else:
                # Cash & Bank Transfer: Check Cash balance for total cash outflow (goods paid + shipping + labor)
                total_cash_needed = paid_amt + extra_cash_expenses
                if total_cash_needed > 0 and total_cash_needed > cash_bal:
                    breakdown = f"পণ্য বাবদ: ৳ {paid_amt:,.2f}"
                    if ship_paid > 0:
                        breakdown += f" + গাড়ি ভাড়া: ৳ {ship_paid:,.2f}"
                    if lab_paid > 0:
                        breakdown += f" + লেবার খরচ: ৳ {lab_paid:,.2f}"
                    raise serializers.ValidationError({
                        'paid_amount': f"পর্যাপ্ত নগদ ক্যাশ ব্যালেন্স নেই! (বর্তমান ক্যাশ ব্যালেন্স: ৳ {cash_bal:,.2f}, মোট নগদ পরিশোধ করতে চাচ্ছেন: ৳ {total_cash_needed:,.2f} [{breakdown}])। ক্যাশে পর্যাপ্ত ব্যালেন্স না থাকলে নগদ প্রদান বা গাড়ি ভাড়া/লেবার পরিশোধ করা যাবে না।"
                    })

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        if not validated_data.get('invoice_no'):
            from django.utils import timezone
            year = timezone.now().year
            last_id = Transaction.objects.order_by('-id').first()
            next_id = (last_id.id + 1) if last_id else 1
            validated_data['invoice_no'] = f"INV-{year}-{next_id:04d}"

        party = validated_data.get('party')
        if party and not validated_data.get('party_name'):
            validated_data['party_name'] = party.name
            validated_data['party_phone'] = party.phone

        transaction = Transaction.objects.create(**validated_data)

        affected_product_ids = set()

        for item_data in items_data:
            sell_price_input = item_data.pop('sell_price', None)
            item_data.pop('cost_price', None)

            t_item = TransactionItem.objects.create(transaction=transaction, **item_data)
            prod = t_item.product
            if not prod and t_item.product_name:
                prod = Product.objects.filter(name__iexact=t_item.product_name.strip()).first()
                if not prod:
                    prod = find_or_create_product_for_purchase(
                        item_name=t_item.product_name,
                        unit=t_item.unit,
                        price=t_item.price,
                        sell_price=sell_price_input
                    )
                if prod:
                    t_item.product = prod
                    t_item.save(update_fields=['product'])

            if prod:
                affected_product_ids.add(prod.id)
                # Update selling price if specified in purchase
                if transaction.transaction_type == 'purchase' and sell_price_input is not None and float(sell_price_input) > 0:
                    prod.sell_price = round(float(sell_price_input), 2)
                    prod.save(update_fields=['sell_price'])

        is_active = transaction.status not in ['pending', 'draft', 'cancelled', 'rejected']

        if party and is_active:
            if transaction.transaction_type == 'sale':
                party.total_due += transaction.due_amount
                party.total_sales += transaction.total_amount
                party.save()
            elif transaction.transaction_type == 'purchase':
                supplier_due = transaction.due_amount
                supplier_purchases = Decimal(str(transaction.total_amount or 0))
                if transaction.notes and transaction.notes.strip().startswith('{'):
                    try:
                        import json
                        first_line = transaction.notes.split('\n')[0]
                        meta = json.loads(first_line)
                        if 'supplierDue' in meta and meta['supplierDue'] is not None:
                            supplier_due = Decimal(str(meta['supplierDue']))
                        ship = Decimal(str(meta.get('shippingCost') or 0))
                        lab = Decimal(str(meta.get('laborCost') or 0))
                        supplier_purchases = max(Decimal('0.00'), supplier_purchases - (ship + lab))
                    except Exception:
                        pass
                party.total_due += supplier_due
                party.total_purchases += supplier_purchases
                party.save()
            elif transaction.transaction_type in ['sale_return', 'purchase_return']:
                due_reduction = max(Decimal('0.00'), Decimal(str(transaction.total_amount)) - Decimal(str(transaction.paid_amount)))
                party.total_due = max(Decimal('0.00'), Decimal(str(party.total_due)) - due_reduction)
                party.save()
            elif transaction.transaction_type in ['payment_in', 'payment_out']:
                party.total_due = max(Decimal('0.00'), Decimal(str(party.total_due)) - Decimal(str(transaction.paid_amount)))
                party.save()

        # Chronologically recalculate stock & weighted cost for all affected products
        if is_active:
            for pid in affected_product_ids:
                recalculate_product_stock_and_cost(pid)

        return transaction

    def update(self, instance, validated_data):
        import json
        items_data = validated_data.pop('items', None)
        old_party = Party.objects.filter(id=instance.party_id).first() if instance.party_id else None
        old_type = instance.transaction_type
        old_total = Decimal(str(instance.total_amount or 0))
        old_due = Decimal(str(instance.due_amount or 0))
        old_paid = Decimal(str(instance.paid_amount or 0))

        affected_product_ids = set(instance.items.exclude(product__isnull=True).values_list('product_id', flat=True))

        old_is_active = instance.status not in ['pending', 'draft', 'cancelled', 'rejected']

        # 1. Revert previous transaction effects on old party if it was active
        if old_party and old_is_active:
            if old_type == 'sale':
                old_party.total_due = Decimal(str(old_party.total_due)) - old_due
                old_party.total_sales = Decimal(str(old_party.total_sales)) - old_total
                old_party.save()
            elif old_type == 'purchase':
                old_supplier_due = old_due
                old_supplier_purchases = old_total
                if instance.notes and instance.notes.strip().startswith('{'):
                    try:
                        first_line = instance.notes.split('\n')[0]
                        meta = json.loads(first_line)
                        if 'supplierDue' in meta and meta['supplierDue'] is not None:
                            old_supplier_due = Decimal(str(meta['supplierDue']))
                        ship = Decimal(str(meta.get('shippingCost') or 0))
                        lab = Decimal(str(meta.get('laborCost') or 0))
                        old_supplier_purchases = max(Decimal('0.00'), old_supplier_purchases - (ship + lab))
                    except Exception:
                        pass
                old_party.total_due = Decimal(str(old_party.total_due)) - old_supplier_due
                old_party.total_purchases = Decimal(str(old_party.total_purchases)) - old_supplier_purchases
                old_party.save()
            elif old_type in ['sale_return', 'purchase_return']:
                due_red = max(Decimal('0.00'), old_total - old_paid)
                old_party.total_due = Decimal(str(old_party.total_due)) + due_red
                old_party.save()
            elif old_type in ['payment_in', 'payment_out']:
                old_party.total_due = Decimal(str(old_party.total_due)) + old_paid
                old_party.save()

        # 2. Delete old items
        if items_data is not None:
            instance.items.all().delete()

        # 3. Update instance attributes
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # 4. If items are provided, create new items
        if items_data is not None:
            for item_data in items_data:
                sell_price_input = item_data.pop('sell_price', None)
                item_data.pop('cost_price', None)
                t_item = TransactionItem.objects.create(transaction=instance, **item_data)
                prod = t_item.product

                if not prod and t_item.product_name:
                    prod = Product.objects.filter(name__iexact=t_item.product_name.strip()).first()
                    if not prod:
                        prod = find_or_create_product_for_purchase(
                            item_name=t_item.product_name,
                            unit=t_item.unit,
                            price=t_item.price,
                            sell_price=sell_price_input
                        )
                    if prod:
                        t_item.product = prod
                        t_item.save(update_fields=['product'])

                if prod:
                    affected_product_ids.add(prod.id)
                    if instance.transaction_type == 'purchase' and sell_price_input is not None and float(sell_price_input) > 0:
                        prod.sell_price = round(float(sell_price_input), 2)
                        prod.save(update_fields=['sell_price'])

        # 5. Apply new transaction effect on current/updated party ONLY if new transaction is active
        new_is_active = instance.status not in ['pending', 'draft', 'cancelled', 'rejected']
        if instance.party_id and new_is_active:
            new_party = Party.objects.filter(id=instance.party_id).first()
            if new_party:
                if instance.transaction_type == 'sale':
                    new_party.total_due = Decimal(str(new_party.total_due)) + Decimal(str(instance.due_amount or 0))
                    new_party.total_sales = Decimal(str(new_party.total_sales)) + Decimal(str(instance.total_amount or 0))
                    new_party.save()
                elif instance.transaction_type == 'purchase':
                    supplier_due = Decimal(str(instance.due_amount or 0))
                    supplier_purchases = Decimal(str(instance.total_amount or 0))
                    if instance.notes and instance.notes.strip().startswith('{'):
                        try:
                            first_line = instance.notes.split('\n')[0]
                            meta = json.loads(first_line)
                            if 'supplierDue' in meta and meta['supplierDue'] is not None:
                                supplier_due = Decimal(str(meta['supplierDue']))
                            ship = Decimal(str(meta.get('shippingCost') or 0))
                            lab = Decimal(str(meta.get('laborCost') or 0))
                            supplier_purchases = max(Decimal('0.00'), supplier_purchases - (ship + lab))
                        except Exception:
                            pass
                    new_party.total_due = Decimal(str(new_party.total_due)) + supplier_due
                    new_party.total_purchases = Decimal(str(new_party.total_purchases)) + supplier_purchases
                    new_party.save()
                elif instance.transaction_type in ['sale_return', 'purchase_return']:
                    due_reduction = max(Decimal('0.00'), Decimal(str(instance.total_amount or 0)) - Decimal(str(instance.paid_amount or 0)))
                    new_party.total_due = Decimal(str(new_party.total_due)) - due_reduction
                    new_party.save()
                elif instance.transaction_type in ['payment_in', 'payment_out']:
                    new_party.total_due = Decimal(str(new_party.total_due)) - Decimal(str(instance.paid_amount or 0))
                    new_party.save()

        # 6. Chronologically recalculate stock & weighted cost for all affected products
        for pid in affected_product_ids:
            recalculate_product_stock_and_cost(pid)

        return instance

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = '__all__'

class ExpenseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Expense
        fields = '__all__'

    def validate(self, attrs):
        cat_name = attrs.get('category_name') or (self.instance.category_name if self.instance else '')
        if not attrs.get('title'):
            attrs['title'] = cat_name or 'সাধারণ খরচ'

        amt = attrs.get('amount')
        if amt is None and self.instance:
            amt = self.instance.amount
        amt = Decimal(str(amt or 0))

        pay_method = (attrs.get('payment_method') or (self.instance.payment_method if self.instance else 'cash') or 'cash').lower()

        if amt > 0:
            exclude_id = self.instance.id if self.instance else None
            cash_bal, bank_bal = get_available_balances(exclude_expense_id=exclude_id)
            is_bank = any(b in pay_method for b in ['bank', 'cheque', 'mobile', 'bkash'])
            if is_bank:
                target_bank = attrs.get('bank_account') or (self.instance.bank_account if self.instance else None)
                if target_bank:
                    target_bank_bal = target_bank.balance
                    if amt > target_bank_bal:
                        raise serializers.ValidationError({
                            'amount': f"পর্যাপ্ত ব্যাংক ব্যালেন্স নেই! (নির্বাচিত '{target_bank.name}' একাউন্ট ব্যালেন্স: ৳ {target_bank_bal:,.2f}, খরচ দিতে চাচ্ছেন: ৳ {amt:,.2f})। অনুগ্রহ করে আগে এই ব্যাংক একাউন্টে ব্যালেন্স জমা করুন।"
                        })
                elif amt > bank_bal:
                    raise serializers.ValidationError({
                        'amount': f"পর্যাপ্ত ব্যাংক ব্যালেন্স নেই! (বর্তমান ব্যাংক ব্যালেন্স: ৳ {bank_bal:,.2f}, খরচ দিতে চাচ্ছেন: ৳ {amt:,.2f})। অনুগ্রহ করে আগে ব্যাংকে ব্যালেন্স জমা করুন।"
                    })
            else:
                if amt > cash_bal:
                    raise serializers.ValidationError({
                        'amount': f"পর্যাপ্ত নগদ ক্যাশ ব্যালেন্স নেই! (বর্তমান ক্যাশ ব্যালেন্স: ৳ {cash_bal:,.2f}, খরচ দিতে চাচ্ছেন: ৳ {amt:,.2f})। অনুগ্রহ করে আগে ক্যাশে ব্যালেন্স জমা করুন।"
                    })
        return attrs

    def create(self, validated_data):
        cat_name = validated_data.get('category_name')
        if cat_name and not validated_data.get('category'):
            cat, _ = ExpenseCategory.objects.get_or_create(name=cat_name.strip())
            validated_data['category'] = cat
        if not validated_data.get('title') and cat_name:
            validated_data['title'] = cat_name
        return super().create(validated_data)

    def update(self, instance, validated_data):
        cat_name = validated_data.get('category_name')
        if cat_name and not validated_data.get('category'):
            cat, _ = ExpenseCategory.objects.get_or_create(name=cat_name.strip())
            validated_data['category'] = cat
        if not validated_data.get('title') and cat_name:
            validated_data['title'] = cat_name
        return super().update(instance, validated_data)

class HawlatSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Hawlat
        fields = '__all__'


from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    role_badge = serializers.CharField(source='role_display_badge', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'role', 'role_display', 'role_badge', 'full_name', 'phone', 'is_active', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    role = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    role_badge = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'is_superuser', 'profile', 'role', 'role_display', 'role_badge', 'full_name', 'phone', 'date_joined']

    def get_role(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.role:
            return obj.profile.role
        if obj.is_superuser:
            return 'developer'
        return 'staff'

    def get_role_display(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.get_role_display()
        return 'ডেভেলপার' if obj.is_superuser else 'স্টাফ'

    def get_role_badge(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.role_display_badge
        return '🛠️ ডেভেলপার' if obj.is_superuser else '👔 স্টাফ'

    def get_full_name(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.full_name:
            return obj.profile.full_name
        name = f"{obj.first_name} {obj.last_name}".strip()
        return name or obj.username

    def get_phone(self, obj):
        if hasattr(obj, 'profile') and obj.profile:
            return obj.profile.phone or ''
        return ''


