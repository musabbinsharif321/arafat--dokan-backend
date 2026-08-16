from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta

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
from .serializers import (
    ShopSettingsSerializer,
    PartySerializer,
    CategorySerializer,
    ProductSerializer,
    BankSerializer,
    TransactionSerializer,
    ExpenseCategorySerializer,
    ExpenseSerializer,
    HawlatSerializer
)

class ShopSettingsViewSet(viewsets.ModelViewSet):
    queryset = ShopSettings.objects.all()
    serializer_class = ShopSettingsSerializer

    def get_queryset(self):
        # Ensure at least one default settings object exists
        if not ShopSettings.objects.exists():
            ShopSettings.objects.create()
        return ShopSettings.objects.all()

class PartyViewSet(viewsets.ModelViewSet):
    queryset = Party.objects.all().order_by('-created_at')
    serializer_class = PartySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        party_type = self.request.query_params.get('party_type')
        search = self.request.query_params.get('search')

        if party_type:
            if party_type == 'customer':
                qs = qs.filter(Q(party_type='customer') | Q(party_type='both'))
            elif party_type == 'supplier':
                qs = qs.filter(Q(party_type='supplier') | Q(party_type='both'))
        
        if search:
            qs = qs.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search) |
                Q(business_name__icontains=search)
            )

        return qs

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer

from rest_framework.decorators import action
from .services import recalculate_product_stock_and_cost, generate_product_cost_log

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('name')
    serializer_class = ProductSerializer

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

        return qs

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

class BankViewSet(viewsets.ModelViewSet):
    queryset = Bank.objects.all().order_by('name')
    serializer_class = BankSerializer

from .services import recalculate_product_stock_and_cost

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all().order_by('-created_at')
    serializer_class = TransactionSerializer

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

        return qs

    def perform_destroy(self, instance):
        from decimal import Decimal
        import json
        old_party = Party.objects.filter(id=instance.party_id).first() if instance.party_id else None
        old_type = instance.transaction_type
        old_total = instance.total_amount or Decimal('0.00')
        old_due = instance.due_amount or Decimal('0.00')
        old_paid = instance.paid_amount or Decimal('0.00')

        if old_party:
            if old_type == 'sale':
                old_party.total_due = Decimal(str(old_party.total_due)) - old_due
                old_party.total_sales = Decimal(str(old_party.total_sales)) - old_total
                old_party.save()
            elif old_type == 'purchase':
                old_supplier_due = old_due
                if instance.notes and instance.notes.strip().startswith('{'):
                    try:
                        first_line = instance.notes.split('\n')[0]
                        meta = json.loads(first_line)
                        if 'supplierDue' in meta and meta['supplierDue'] is not None:
                            old_supplier_due = Decimal(str(meta['supplierDue']))
                    except Exception:
                        pass
                old_party.total_due = Decimal(str(old_party.total_due)) - old_supplier_due
                old_party.total_purchases = Decimal(str(old_party.total_purchases)) - old_total
                old_party.save()
            elif old_type in ['sale_return', 'purchase_return']:
                due_red = max(Decimal('0.00'), Decimal(str(old_total)) - Decimal(str(old_paid)))
                old_party.total_due = Decimal(str(old_party.total_due)) + due_red
                old_party.save()
            elif old_type in ['payment_in', 'payment_out']:
                old_party.total_due = Decimal(str(old_party.total_due)) + Decimal(str(old_paid))
                old_party.save()

        affected_product_ids = set(instance.items.exclude(product__isnull=True).values_list('product_id', flat=True))
        instance.delete()

        for pid in affected_product_ids:
            recalculate_product_stock_and_cost(pid)

class ExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all().order_by('name')
    serializer_class = ExpenseCategorySerializer

class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all().order_by('-date', '-created_at')
    serializer_class = ExpenseSerializer

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

class DashboardStatsView(APIView):
    """
    High performance server-side aggregator for instant ERP Dashboard loading.
    """
    def get(self, request):
        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sales aggregates
        sales_qs = Transaction.objects.filter(transaction_type='sale')
        total_sales = sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0
        sales_paid = sales_qs.aggregate(total=Sum('paid_amount'))['total'] or 0
        total_dues = sales_qs.aggregate(total=Sum('due_amount'))['total'] or 0
        monthly_sales = sales_qs.filter(created_at__gte=first_day_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

        # Purchase aggregates
        purchases_qs = Transaction.objects.filter(transaction_type='purchase')
        total_purchases = purchases_qs.aggregate(total=Sum('total_amount'))['total'] or 0
        purchases_paid = purchases_qs.aggregate(total=Sum('paid_amount'))['total'] or 0
        monthly_purchases = purchases_qs.filter(created_at__gte=first_day_of_month).aggregate(total=Sum('total_amount'))['total'] or 0

        # Expense aggregates
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        monthly_expenses = Expense.objects.filter(date__gte=first_day_of_month.date()).aggregate(total=Sum('amount'))['total'] or 0

        # Cash & Bank Balance (Real calculation)
        banks_total = Bank.objects.aggregate(total=Sum('balance'))['total'] or 0
        total_cash = max(0, float(sales_paid) - float(purchases_paid) - float(total_expenses))
        total_bank = float(banks_total)

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
            ).aggregate(total=Sum('total_amount'))['total'] or 0

            day_purchases = Transaction.objects.filter(
                transaction_type='purchase',
                created_at__date=day_date
            ).aggregate(total=Sum('total_amount'))['total'] or 0

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


