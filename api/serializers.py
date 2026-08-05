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

class TransactionItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = TransactionItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'unit', 'total']

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

def find_or_create_product_for_purchase(item_name, unit, price, brand_param=None):
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

    new_prod = Product.objects.create(
        name=cleaned_name,
        category=cat_obj,
        category_name=category_head,
        brand=brand_param or '',
        unit=unit or ('কেজি' if category_head == 'রড' else 'বস্তা' if category_head == 'সিমেন্ট' else 'পিস'),
        purchase_price=price or 0.00,
        sell_price=round((float(price or 0) * 1.1), 2),
        stock=0.00
    )
    return new_prod


class TransactionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    invoice_no = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    items = TransactionItemSerializer(many=True, required=False)

    class Meta:
        model = Transaction
        fields = '__all__'

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
        
        for item_data in items_data:
            t_item = TransactionItem.objects.create(transaction=transaction, **item_data)
            prod = t_item.product

            if not prod and t_item.product_name:
                prod = find_or_create_product_for_purchase(
                    item_name=t_item.product_name,
                    unit=t_item.unit,
                    price=t_item.price
                )
                if prod:
                    t_item.product = prod
                    t_item.save(update_fields=['product'])

            if prod:
                old_stock = float(prod.stock or 0)
                old_price = float(prod.purchase_price or 0)
                qty = float(t_item.quantity or 0)
                unit_price = float(t_item.price or 0)

                if transaction.transaction_type == 'purchase':
                    # Weighted Average Purchase Price Calculation (ক্রয় মূল্য সমন্বয়)
                    if (old_stock + qty) > 0 and old_stock > 0 and old_price > 0:
                        weighted_price = ((old_stock * old_price) + (qty * unit_price)) / (old_stock + qty)
                        prod.purchase_price = round(weighted_price, 2)
                    elif unit_price > 0:
                        prod.purchase_price = round(unit_price, 2)

                    prod.stock = old_stock + qty
                    prod.save()

                elif transaction.transaction_type == 'sale':
                    prod.stock = max(0.0, old_stock - qty)
                    prod.save()

                elif transaction.transaction_type == 'sale_return':
                    prod.stock = old_stock + qty
                    prod.save()

                elif transaction.transaction_type == 'purchase_return':
                    prod.stock = max(0.0, old_stock - qty)
                    prod.save()

        if party:
            if transaction.transaction_type == 'sale':
                party.total_due += transaction.due_amount
                party.total_sales += transaction.total_amount
                party.save()
            elif transaction.transaction_type == 'purchase':
                party.total_due += transaction.due_amount
                party.total_purchases += transaction.total_amount
                party.save()
            elif transaction.transaction_type == 'sale_return':
                due_reduction = max(0.0, float(transaction.total_amount) - float(transaction.paid_amount))
                party.total_due = max(0.0, float(party.total_due) - due_reduction)
                party.save()
            elif transaction.transaction_type in ['payment_in', 'payment_out']:
                party.total_due = max(0.0, float(party.total_due) - float(transaction.paid_amount))
                party.save()

        return transaction

    def update(self, instance, validated_data):
        old_due = instance.due_amount
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if instance.party and 'due_amount' in validated_data:
            due_diff = instance.due_amount - old_due
            instance.party.total_due = max(0, instance.party.total_due + due_diff)
            instance.party.save()

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                TransactionItem.objects.create(transaction=instance, **item_data)
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

class HawlatSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Hawlat
        fields = '__all__'

