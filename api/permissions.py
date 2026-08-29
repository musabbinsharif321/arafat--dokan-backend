from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

def get_user_role(user):
    if not user or not user.is_authenticated:
        return 'anonymous'
    if user.is_superuser:
        return 'developer'
    if hasattr(user, 'profile') and user.profile and user.profile.role:
        return user.profile.role
    return 'staff'

class RoleBasedAccessPermission(permissions.BasePermission):
    """
    3-Tier Role-Based Access Control:
    1. 'developer': Full unrestricted access (GET, POST, PUT, PATCH, DELETE) across all resources including invoice edit/delete.
    2. 'admin':
       - Full access across all modules (parties, products, expenses, banks, hawlats, settings, users, etc.).
       - Can create new transactions/invoices (POST) and view them (GET).
       - STRICTLY FORBIDDEN from editing (PUT/PATCH) or deleting (DELETE) transactions/invoices.
    3. 'staff':
       - Read-only access (SAFE_METHODS: GET, HEAD, OPTIONS) on all resources.
       - CANNOT create (POST), edit (PUT/PATCH), or delete (DELETE) anything (View Only).
    """
    message = 'আপনার এই কাজটি করার পর্যাপ্ত অনুমতি নেই।'

    def has_permission(self, request, view):
        # Allow OPTIONS requests freely for CORS
        if request.method == 'OPTIONS':
            return True

        if not request.user or not request.user.is_authenticated:
            return True

        role = get_user_role(request.user)

        # 1. Developer has unrestricted access
        if role == 'developer':
            return True

        # 2. Staff is strictly read-only across the entire system
        if role == 'staff':
            if request.method in permissions.SAFE_METHODS:
                return True
            raise PermissionDenied('স্টাফ হিসেবে আপনার কোনো তথ্য তৈরি, পরিবর্তন বা মুছে ফেলার অনুমতি নেই (শুধুমাত্র দেখার অনুমতি রয়েছে)।')

        # 3. Admin permissions
        if role == 'admin':
            view_name = getattr(view, 'basename', '') or getattr(view, '__class__', {}).__name__.lower()
            is_transaction = 'transaction' in str(view_name).lower() or getattr(view, 'is_transaction_view', False)

            if is_transaction:
                # Admin can view (GET) and create (POST) invoices
                if request.method in permissions.SAFE_METHODS or request.method == 'POST':
                    return True
                # Admin CANNOT update or delete any invoice
                raise PermissionDenied('ইনভয়েস বা লেনদেন সম্পাদনা (Edit) অথবা মুছে ফেলার (Delete) অনুমতি শুধুমাত্র ডেভেলপার (Developer) এর রয়েছে।')

            # For all other resources, Admin has full access
            return True

        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return True

        role = get_user_role(request.user)

        if role == 'developer':
            return True

        if role == 'staff':
            if request.method in permissions.SAFE_METHODS:
                return True
            raise PermissionDenied('স্টাফ হিসেবে আপনার কোনো তথ্য পরিবর্তন বা মুছে ফেলার অনুমতি নেই।')

        if role == 'admin':
            view_name = getattr(view, 'basename', '') or getattr(view, '__class__', {}).__name__.lower()
            is_transaction = 'transaction' in str(view_name).lower() or getattr(view, 'is_transaction_view', False)

            if is_transaction:
                if request.method in permissions.SAFE_METHODS:
                    return True
                raise PermissionDenied('ইনভয়েস বা লেনদেন সম্পাদনা (Edit) অথবা মুছে ফেলার (Delete) অনুমতি শুধুমাত্র ডেভেলপার (Developer) এর রয়েছে।')

            return True

        return True

class IsAdminUserOnly(permissions.BasePermission):
    """
    Permission class allowing only Admin and Developer users (e.g. for user management).
    """
    message = 'শুধুমাত্র অ্যাডমিন ও ডেভেলপার এই কাজটি করার অনুমতি প্রাপ্ত।'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        role = get_user_role(request.user)
        return role in ['developer', 'admin'] or request.user.is_superuser
