from django.db import models
from django.utils import timezone

class ShopSettings(models.Model):
    business_name = models.CharField(max_length=255, default='Dokan ERP')
    phone = models.CharField(max_length=50, default='01700000000')
    email = models.EmailField(blank=True, null=True, default='info@dokan.com')
    address = models.TextField(blank=True, default='Dhaka, Bangladesh')
    tax_number = models.CharField(max_length=100, blank=True, null=True)
    currency = models.CharField(max_length=20, default='৳')
    logo_url = models.TextField(blank=True, null=True)
    receipt_footer = models.TextField(blank=True, default='ধন্যবাদ, আবার আসবেন!')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Shop Settings'

    def __str__(self):
        return self.business_name

class Party(models.Model):
    PARTY_TYPES = [
        ('customer', 'Customer'),
        ('supplier', 'Supplier'),
        ('engineer', 'Engineer'),
        ('both', 'Both'),
    ]

    party_type = models.CharField(max_length=20, choices=PARTY_TYPES, default='customer')
    name = models.CharField(max_length=255)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    customer_type = models.CharField(max_length=100, default='খুচরা গ্রাহক')
    supply_type = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=50, db_index=True)
    alt_phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    country = models.CharField(max_length=100, default='বাংলাদেশ')
    division = models.CharField(max_length=100, default='ঢাকা')
    district = models.CharField(max_length=100, default='ঢাকা')
    thana = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, default='')
    postcode = models.CharField(max_length=20, blank=True, null=True)
    id_type = models.CharField(max_length=50, default='NID')
    nid = models.CharField(max_length=100, blank=True, null=True)
    tin_number = models.CharField(max_length=100, blank=True, null=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit_days = models.IntegerField(default=30)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    total_due = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_purchases = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    joined_date = models.DateField(default=timezone.localdate)
    note = models.TextField(blank=True, null=True)
    photo_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)
    sku = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    category_name = models.CharField(max_length=100, blank=True, null=True)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    unit = models.CharField(max_length=50, default='পিস')
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    brand = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)
    needs_price_review = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (Stock: {self.stock})"

class Bank(models.Model):
    name = models.CharField(max_length=255)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    account_number = models.CharField(max_length=100, blank=True, null=True)
    branch = models.CharField(max_length=100, blank=True, null=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} - {self.balance}"

class Transaction(models.Model):
    TYPE_CHOICES = [
        ('sale', 'Sale'),
        ('purchase', 'Purchase'),
        ('sale_return', 'Sale Return'),
        ('purchase_return', 'Purchase Return'),
        ('payment_in', 'Payment In'),
        ('payment_out', 'Payment Out'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('bank', 'Bank'),
        ('cheque', 'Cheque'),
        ('mobile_banking', 'Mobile Banking'),
        ('split', 'Split'),
    ]

    CHEQUE_STATUS = [
        ('pending', 'Pending'),
        ('cleared', 'Cleared'),
        ('bounced', 'Bounced'),
    ]

    invoice_no = models.CharField(max_length=100, unique=True, blank=True, null=True, db_index=True)
    party = models.ForeignKey(Party, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    party_name = models.CharField(max_length=255, blank=True, null=True)
    party_phone = models.CharField(max_length=50, blank=True, null=True)
    transaction_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='sale', db_index=True)
    status = models.CharField(max_length=30, default='completed')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    due_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=30, choices=PAYMENT_METHODS, default='cash')
    bank_account = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    cheque_number = models.CharField(max_length=100, blank=True, null=True)
    cheque_bank = models.CharField(max_length=100, blank=True, null=True)
    cheque_due_date = models.DateField(blank=True, null=True)
    cheque_status = models.CharField(max_length=20, choices=CHEQUE_STATUS, default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            year = timezone.now().year
            last_id = Transaction.objects.order_by('-id').first()
            next_id = (last_id.id + 1) if last_id else 1
            self.invoice_no = f"INV-{year}-{next_id:04d}"
        if self.party and not self.party_name:
            self.party_name = self.party.name
            self.party_phone = self.party.phone
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_no} ({self.transaction_type}) - {self.total_amount}"

class TransactionItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    product_name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    unit = models.CharField(max_length=50, default='পিস')
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name

class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    category_name = models.CharField(max_length=100, default='সাধারণ খরচ')
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(max_length=50, default='ক্যাশ')
    bank_account = models.ForeignKey(Bank, on_delete=models.SET_NULL, null=True, blank=True)
    reference_no = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"

class Hawlat(models.Model):
    person_name = models.CharField(max_length=255, default='সাধারণ হাওলাত')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    note = models.TextField(blank=True, null=True)
    date = models.DateField(default=timezone.localdate)
    is_settled = models.BooleanField(default=False)
    settled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Hawlats'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.person_name} - {self.amount}"


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('developer', 'ডেভেলপার (Developer - Full Access & Invoice Edit/Delete)'),
        ('admin', 'অ্যাডমিন (Admin - All Operations Except Invoice Edit/Delete)'),
        ('staff', 'স্টাফ (Staff - View Only)'),
    ]

    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='staff')
    full_name = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    @property
    def role_display_badge(self):
        if self.role == 'developer':
            return '🛠️ ডেভেলপার (সর্বোচ্চ ক্ষমতা)'
        elif self.role == 'admin':
            return '👑 অ্যাডমিন (ইনভয়েস এডিট/ডিলিট ব্যতীত সব ক্ষমতা)'
        elif self.role == 'staff':
            return '👔 স্টাফ (শুধুমাত্র দেখার অনুমতি)'
        return self.role


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        role = 'developer' if instance.is_superuser else 'admin'
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': role,
                'full_name': (f"{instance.first_name} {instance.last_name}".strip()) or instance.username
            }
        )


