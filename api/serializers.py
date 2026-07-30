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
    Expense
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
            if t_item.product:
                if transaction.transaction_type == 'sale':
                    t_item.product.stock -= t_item.quantity
                    t_item.product.save()
                elif transaction.transaction_type == 'purchase':
                    t_item.product.stock += t_item.quantity
                    t_item.product.save()
                elif transaction.transaction_type == 'sale_return':
                    t_item.product.stock += t_item.quantity
                    t_item.product.save()
                elif transaction.transaction_type == 'purchase_return':
                    t_item.product.stock -= t_item.quantity
                    t_item.product.save()

        if party:
            if transaction.transaction_type in ['sale', 'purchase']:
                party.total_due += transaction.due_amount
                party.total_purchases += transaction.total_amount
                party.save()

        return transaction

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

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
