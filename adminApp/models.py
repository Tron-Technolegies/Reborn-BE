from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.contrib.auth.hashers import make_password, check_password

class Coupon(models.Model):
    DISCOUNT_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]

    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self, subtotal=0):
        now = timezone.now()
        if not self.active:
            return False, "Coupon is inactive"
        if now < self.valid_from:
            return False, "Coupon is not yet valid"
        if now > self.valid_to:
            return False, "Coupon has expired"
        if self.usage_limit and self.used_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        if Decimal(str(subtotal)) < self.min_purchase_amount:
            return False, f"Minimum purchase of ₹{self.min_purchase_amount} required"
        return True, ""

    def calculate_discount(self, subtotal):
        if self.discount_type == 'percentage':
            discount = (Decimal(str(subtotal)) * self.discount_value) / 100
        else:
            discount = self.discount_value
        return min(discount, Decimal(str(subtotal)))

    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percentage' else ' off'})"

class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    prefix = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return f"{self.name} ({self.prefix})"

class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    colour = models.CharField(max_length=50, blank=True, default='')
    description = models.TextField(blank=True, default='')
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0.0)
    product_type = models.CharField(max_length=50, blank=True, default='Supplement')
    image = models.ImageField(upload_to='rental_items/', blank=True, null=True)
    rental_price = models.DecimalField(max_digits=10, decimal_places=2)
    code = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.code:
            prefix = self.category.prefix
            last_item = Product.objects.filter(code__startswith=prefix).order_by('-code').first()
            next_number = (int(last_item.code.replace(prefix, "")) + 1) if last_item else 1
            self.code = f"{prefix}{str(next_number).zfill(3)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_stock(self):
        return self.units.count()

    @property
    def available_stock(self):
        return self.units.filter(status='available').count()

    @property
    def is_available(self):
        return self.available_stock > 0

    @property
    def total_rented_times(self):
        return self.rentalitem_set.count()

class PhysicalUnit(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('rented', 'Rented'),
        ('washing', 'In Washing'),
        ('repair', 'Under Repair'),
        ('damaged', 'Damaged'),
        ('retired', 'Retired'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='units')
    unit_id = models.CharField(max_length=50, unique=True) 
    barcode = models.CharField(max_length=50, unique=True, null=True, blank=True)
    barcode_generated_at = models.DateTimeField(null=True, blank=True)
    size = models.CharField(max_length=20, default='Free Size')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available', db_index=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.barcode:
            self.barcode = self.unit_id
            self.barcode_generated_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} - {self.unit_id} ({self.size})"


class AlterationType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Alteration(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('DELIVERED', 'Delivered'),
    ]

    booking = models.ForeignKey('RentalBooking', on_delete=models.CASCADE, related_name='alterations')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    alteration_type = models.ForeignKey(AlterationType, on_delete=models.PROTECT, null=True, blank=True)
    alteration_area = models.CharField(max_length=50, blank=True, null=True)
    restore_after_return = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    expected_completion_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.alteration_type.name} for {self.product.name} (Booking #{self.booking.id})"

class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('UPI', 'UPI'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]
    
    PAYMENT_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('REFUND', 'Refund'),
    ]

    CATEGORY = [
        ('rental', 'Rental'),
        ('purchase', 'Material Purchase'),
        ('stitching', 'Stitching'),
        ('accessory', 'Accessory Sale'),
        ('deposit', 'Security Deposit'),
        ('salary', 'Salary'),
        ('rent', 'Rent'),
        ('utilities', 'Utilities'),
        ('other', 'Other'),
    ]

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_type = models.CharField(max_length=10, choices=PAYMENT_TYPES, default='INCOME')
    transaction_reference = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    rental_booking = models.ForeignKey('RentalBooking', on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    stitching_order = models.ForeignKey('StitchingOrder', on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    accessory_sale = models.ForeignKey('AccessorySale', on_delete=models.CASCADE, null=True, blank=True, related_name='payments')
    
    expense_category = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.payment_type} - {self.amount} ({self.payment_method})"


class RentalBooking(models.Model):

    BOOKING_TYPE_CHOICES = [
        ('IMMEDIATE', 'Immediate'),
        ('PRE_BOOKING', 'Pre-Booking'),
    ]
    STATUS_CHOICES = [
        ('PRE_BOOKED', 'Pre-Booked'),
        ('READY_FOR_PICKUP', 'Ready for Pickup'),
        ('ACTIVE', 'Active'),
        ('RETURNED', 'Returned'),
        ('CANCELLED', 'Cancelled'),
    ]

    booking_type = models.CharField(max_length=20, choices=BOOKING_TYPE_CHOICES, default='IMMEDIATE')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    booking_date = models.DateTimeField(default=timezone.now)

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    rental_date = models.DateField(db_index=True)
    return_date = models.DateField(db_index=True)
    number_of_days = models.PositiveIntegerField(blank=True, null=True)

    rental_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    

    is_returned = models.BooleanField(default=False, db_index=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    returned_at = models.DateTimeField(null=True, blank=True)

    # Security Deposit Logic
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deposit_status = models.CharField(
        max_length=20, 
        choices=[
            ('held', 'Held'), 
            ('refunded', 'Refunded'), 
            ('deducted', 'Deducted'), 
            ('partially_refunded', 'Partially Refunded')
        ],
        default='held'
    )
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deducted_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    damage_notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.rental_date and self.return_date:
            self.number_of_days = (self.return_date - self.rental_date).days
        super().save(*args, **kwargs)

    def mark_as_returned(self, next_status='available'):
        if not self.is_returned:
            self.is_returned = True
            self.status = 'RETURNED'
            self.returned_at = timezone.now()
            for item in self.items.all():
                if item.unit:
                    item.unit.status = next_status
                    item.unit.save()
            self.save()

    @property
    def advance_paid(self):
        return sum(p.amount for p in self.payments.all() if p.payment_type == "INCOME" and p.expense_category != "deposit") - sum(p.amount for p in self.payments.all() if p.payment_type == "REFUND" and p.expense_category != "deposit")

    @property
    def due_amount(self):
        return (self.rental_amount - self.discount_amount) - self.advance_paid


class Material(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='materials/', blank=True, null=True)
    price_per_meter = models.DecimalField(max_digits=10, decimal_places=2)
    colour = models.CharField(max_length=50, blank=True, default="")
    total_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    available_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.code:
            last_item = Material.objects.order_by('-id').first()
            next_id = 1 if not last_item else last_item.id + 1
            self.code = f"MAT{str(next_id).zfill(3)}"
        super().save(*args, **kwargs)

class MaterialPurchase(models.Model):
    material = models.ForeignKey(Material, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    purchase_date = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_cost = self.quantity * self.cost_per_unit
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.material.total_stock += self.quantity
            self.material.available_stock += self.quantity
            self.material.save()

    def __str__(self):
        return f"{self.material.name} - {self.quantity}"

class StitchingOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.SET_NULL, null=True)
    outfit_type = models.CharField(max_length=100)
    material_used = models.DecimalField(max_digits=10, decimal_places=2, help_text="in meters", default=0)
    measurements_taken = models.BooleanField(default=False)
    order_date = models.DateField()
    delivery_date = models.DateField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.customer.name} - {self.outfit_type}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def advance_payment(self):
        return sum(p.amount for p in self.payments.all() if p.payment_type == "INCOME") - sum(p.amount for p in self.payments.all() if p.payment_type == "REFUND")

    @property
    def due_amount(self):
        return (self.total_amount - self.discount_amount) - self.advance_payment

class Accessory(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100) 
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='accessories/', blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if not self.code:
            last_item = Accessory.objects.order_by('-id').first()
            next_id = 1 if not last_item else last_item.id + 1
            self.code = f"ACC{str(next_id).zfill(3)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class AccessorySale(models.Model):
    accessory = models.ForeignKey(Accessory, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_address = models.TextField(blank=True, null=True)
    quantity = models.PositiveIntegerField()
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_date = models.DateField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            old_sale = AccessorySale.objects.get(pk=self.pk)
            stock_diff = self.quantity - old_sale.quantity
            if self.accessory.stock < stock_diff:
                raise ValidationError("Not enough stock available for update")
            self.accessory.stock -= stock_diff
            self.accessory.save()
        else:
            if self.accessory.stock < self.quantity:
                raise ValidationError("Not enough stock available")
            self.accessory.stock -= self.quantity
            self.accessory.save()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.accessory.stock += self.quantity
        self.accessory.save()
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.customer_name} - {self.accessory.name}"


class SystemSettings(models.Model):
    is_password_enabled = models.BooleanField(default=False)
    password_hash = models.CharField(max_length=128, blank=True, null=True)

    def set_password(self, raw_password):
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password_hash)

    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings

class RentalItem(models.Model):
    booking = models.ForeignKey(RentalBooking, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    unit = models.ForeignKey(PhysicalUnit, on_delete=models.SET_NULL, null=True, blank=True)

    def clean(self):
        if self.unit and self.unit.status != 'available' and not self.pk and getattr(self, 'booking', None) and self.booking.status == 'ACTIVE':
            raise ValidationError(f"Unit {self.unit.unit_id} is not available for active booking")

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.unit and self.booking.status == 'ACTIVE':
            self.unit.status = 'rented'
            self.unit.save()