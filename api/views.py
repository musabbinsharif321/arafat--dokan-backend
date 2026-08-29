from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta

from .permissions import RoleBasedAccessPermission, IsAdminUserOnly, get_user_role
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
    Hawlat,
    UserProfile
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

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [RoleBasedAccessPermission]

from rest_framework.decorators import action
from .services import recalculate_product_stock_and_cost, generate_product_cost_log

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by('name')
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
        if role == 'viewer':
            return Response({'detail': 'ভিউয়ার হিসেবে আপনার কোনো ইনভয়েস অনুমোদন করার অনুমতি নেই।'}, status=status.HTTP_403_FORBIDDEN)
        
        instance = self.get_object()
        if instance.status in ['completed', 'approved']:
            return Response({'detail': 'ইনভয়েসটি ইতিমধ্যে অনুমোদিত হয়েছে', 'status': instance.status}, status=status.HTTP_200_OK)
        
        serializer = self.get_serializer(instance, data={'status': 'approved'}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'ইনভয়েস সফলভাবে অনুমোদন করা হয়েছে', 'data': serializer.data}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        from decimal import Decimal
        import json
        old_party = Party.objects.filter(id=instance.party_id).first() if instance.party_id else None
        old_type = instance.transaction_type
        old_total = instance.total_amount or Decimal('0.00')
        old_due = instance.due_amount or Decimal('0.00')
        old_paid = instance.paid_amount or Decimal('0.00')

        if old_party and instance.status not in ['pending', 'draft', 'cancelled', 'rejected']:
            if old_type == 'sale':
                old_party.total_due = Decimal(str(old_party.total_due)) - old_due
                old_party.total_sales = Decimal(str(old_party.total_sales)) - old_total
                old_party.save()
            elif old_type == 'purchase':
                old_supplier_due = Decimal(str(old_due))
                old_supplier_purchases = Decimal(str(old_total))
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

class DashboardStatsView(APIView):
    """
    High performance server-side aggregator for instant ERP Dashboard loading.
    """
    permission_classes = [RoleBasedAccessPermission]

    def get(self, request):
        now = timezone.now()
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Sales aggregates (excluding pending / unapproved)
        sales_qs = Transaction.objects.filter(transaction_type='sale').exclude(status__in=['pending', 'draft', 'cancelled', 'rejected'])
        total_sales = sales_qs.aggregate(total=Sum('total_amount'))['total'] or 0
        sales_paid = sales_qs.aggregate(total=Sum('paid_amount'))['total'] or 0
        total_dues = sales_qs.aggregate(total=Sum('due_amount'))['total'] or 0
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
        identifier = (
            request.data.get('email') or 
            request.data.get('username') or 
            request.data.get('identifier') or 
            ''
        ).strip()
        password = request.data.get('password', '').strip()

        if not identifier or not password:
            return Response({'detail': 'ইমেইল/ইউজারনেম এবং পাসওয়ার্ড প্রদান করুন।'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Lookup by Email
        user = User.objects.filter(email__iexact=identifier).first()

        # 2. Lookup by Username
        if not user:
            user = User.objects.filter(username__iexact=identifier).first()

        # 3. Lookup by Profile Phone
        if not user:
            profile = UserProfile.objects.filter(phone=identifier).first()
            if profile:
                user = profile.user

        if user and user.check_password(password):
            if not user.is_active:
                return Response({'detail': 'আপনার একাউন্টটি নিষ্ক্রিয় করা আছে। এডমিনের সাথে যোগাযোগ করুন।'}, status=status.HTTP_403_FORBIDDEN)

            token, _ = Token.objects.get_or_create(user=user)
            serializer = UserSerializer(user)
            return Response({
                'token': token.key,
                'user': serializer.data,
                'message': 'সফলভাবে লগইন হয়েছে।'
            }, status=status.HTTP_200_OK)

        return Response({'detail': 'ভুল ইমেইল/ইউজারনেম অথবা পাসওয়ার্ড! সঠিক তথ্য দিন।'}, status=status.HTTP_401_UNAUTHORIZED)


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
    Admin-only endpoint for managing Dokan ERP users (Admin, Staff, Viewer).
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUserOnly]

    def create(self, request, *args, **kwargs):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '').strip()
        role = request.data.get('role', 'staff').strip()
        full_name = request.data.get('full_name', '').strip()
        phone = request.data.get('phone', '').strip()
        email = request.data.get('email', '').strip()

        if not username or not password:
            return Response({'detail': 'ইউজারনেম এবং পাসওয়ার্ড প্রদান করা আবশ্যক।'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username__iexact=username).exists():
            return Response({'detail': f"'{username}' ইউজারনেম ইতিমধ্যে ব্যবহার করা হয়েছে। অন্য ইউজারনেম দিন।"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=full_name
        )
        if role == 'developer':
            user.is_staff = True
            user.is_superuser = True
            user.save()
        elif role == 'admin':
            user.is_staff = True
            user.is_superuser = False
            user.save()
        else:
            user.is_staff = False
            user.is_superuser = False
            user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.full_name = full_name
        profile.phone = phone
        profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        role = request.data.get('role')
        full_name = request.data.get('full_name')
        phone = request.data.get('phone')
        password = request.data.get('password')
        email = request.data.get('email')

        if password:
            user.set_password(password)

        if email is not None:
            user.email = email

        if full_name:
            user.first_name = full_name

        if role:
            if role == 'developer':
                user.is_superuser = True
                user.is_staff = True
            elif role == 'admin':
                user.is_superuser = False
                user.is_staff = True
            else:
                user.is_superuser = False
                user.is_staff = False
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if role:
            profile.role = role
        if full_name is not None:
            profile.full_name = full_name
        if phone is not None:
            profile.phone = phone
        profile.save()

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user == request.user:
            return Response({'detail': 'আপনি নিজের এডমিন একাউন্ট ডিলিট করতে পারবেন না।'}, status=status.HTTP_400_BAD_REQUEST)
        user.delete()
        return Response({'detail': 'ইউজার সফলভাবে মুছে ফেলা হয়েছে।'}, status=status.HTTP_204_NO_CONTENT)



