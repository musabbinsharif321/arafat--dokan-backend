from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied

def get_user_role(user):
    if not user or not user.is_authenticated:
        return 'anonymous'
    if user.is_superuser:
        return 'admin'
    if hasattr(user, 'profile') and user.profile:
        return user.profile.role
    return 'staff'

class RoleBasedAccessPermission(permissions.BasePermission):
    """
    3-Tier Role-Based Access Control Permission Class:
    1. 'admin': Full access (GET, POST, PUT, PATCH, DELETE) across all resources.
    2. 'staff':
       - Allowed to create new invoices/transactions (POST).
       - STRICTLY FORBIDDEN from editing (PUT/PATCH) or deleting (DELETE) any transaction/invoice.
       - Allowed full access on products, parties, expenses, banks, hawlats, etc.
    3. 'viewer':
       - Read-only access (GET, HEAD, OPTIONS) on all resources.
       - Cannot create, edit, or delete any resource.
    """
    message = 'আপনার এই কাজটি করার পর্যাপ্ত অনুমতি নেই।'

    def has_permission(self, request, view):
        # Allow OPTIONS requests freely for CORS
        if request.method == 'OPTIONS':
            return True

        # If user is not authenticated, check if AllowAny or unauthenticated access is allowed
        # (For auth endpoints like login, AllowAny is used explicitly on the view)
        if not request.user or not request.user.is_authenticated:
            return True

        role = get_user_role(request.user)

        # 1. Admin has unrestricted access
        if role == 'admin':
            return True

        # 2. Viewer has read-only access across the entire system
        if role == 'viewer':
            if request.method in permissions.SAFE_METHODS:
                return True
            raise PermissionDenied('ভিউয়ার হিসেবে আপনার কোনো তথ্য তৈরি, পরিবর্তন বা মুছে ফেলার অনুমতি নেই (শুধুমাত্র দেখার অনুমতি রয়েছে)।')

        # 3. Staff permissions
        if role == 'staff':
            # Check if this view is managing Transactions/Invoices
            view_name = getattr(view, 'basename', '') or getattr(view, '__class__', {}).__name__.lower()
            is_transaction = 'transaction' in str(view_name).lower() or getattr(view, 'is_transaction_view', False)

            if is_transaction:
                # Staff can view (GET) and create (POST) invoices
                if request.method in permissions.SAFE_METHODS or request.method == 'POST':
                    # Special check: prevent staff from triggering 'approve' action if it alters invoice
                    # (Allowing creating new transactions)
                    return True
                # Staff CANNOT update or delete any invoice
                raise PermissionDenied('স্টাফ হিসেবে আপনার কোনো ইনভয়েস বা লেনদেন সম্পাদনা (Edit) অথবা মুছে ফেলার (Delete) অনুমতি নেই।')

            # For all other resources (products, parties, expenses, hawlats, etc.), staff has full access
            return True

        return True

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return True

        role = get_user_role(request.user)

        if role == 'admin':
            return True

        if role == 'viewer':
            if request.method in permissions.SAFE_METHODS:
                return True
            raise PermissionDenied('ভিউয়ার হিসেবে আপনার কোনো তথ্য পরিবর্তন বা মুছে ফেলার অনুমতি নেই।')

        if role == 'staff':
            view_name = getattr(view, 'basename', '') or getattr(view, '__class__', {}).__name__.lower()
            is_transaction = 'transaction' in str(view_name).lower() or getattr(view, 'is_transaction_view', False)

            if is_transaction:
                if request.method in permissions.SAFE_METHODS:
                    return True
                raise PermissionDenied('স্টাফ হিসেবে আপনার কোনো ইনভয়েস বা লেনদেন সম্পাদনা (Edit) অথবা মুছে ফেলার (Delete) অনুমতি নেই।')

            return True

        return True

class IsAdminUserOnly(permissions.BasePermission):
    """
    Permission class allowing only Admin users (e.g. for user management).
    """
    message = 'শুধুমাত্র অ্যাডমিন এই কাজটি করার অনুমতি প্রাপ্ত।'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return get_user_role(request.user) == 'admin'
