from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ShopSettingsViewSet,
    PartyViewSet,
    CategoryViewSet,
    ProductViewSet,
    BankViewSet,
    TransactionViewSet,
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    HawlatViewSet,
    DashboardStatsView
)

router = DefaultRouter()
router.register(r'settings', ShopSettingsViewSet, basename='settings')
router.register(r'parties', PartyViewSet, basename='party')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'banks', BankViewSet, basename='bank')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'expense-categories', ExpenseCategoryViewSet, basename='expense-category')
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'hawlats', HawlatViewSet, basename='hawlat')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
]
