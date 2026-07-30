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
    Expense
)
from .serializers import (
    ShopSettingsSerializer,
    PartySerializer,
    CategorySerializer,
    ProductSerializer,
    BankSerializer,
    TransactionSerializer,
    ExpenseCategorySerializer,
    ExpenseSerializer
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

class BankViewSet(viewsets.ModelViewSet):
    queryset = Bank.objects.all().order_by('name')
    serializer_class = BankSerializer

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

