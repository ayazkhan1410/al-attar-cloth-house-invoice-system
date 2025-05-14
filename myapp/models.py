from django.db import models
from .helpers import MyUserManager
from django.contrib.auth.models import AbstractBaseUser


class MyUser(AbstractBaseUser):
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    username = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    objects = MyUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin


class Customer(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    address = models.CharField(max_length=500, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    phone_number2 = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name if self.name else "Unnamed Customer"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('printed', 'Printed'),
        ('downloaded', 'Downloaded'),
        ('both', 'Printed & Downloaded'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=255, null=True, blank=True)
    invoice_date = models.DateField(auto_now_add=True)
    advance_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')], default='unpaid')
    delivery_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cod_number = models.CharField(max_length=255, null=True, blank=True)
    payment_method = models.CharField(max_length=40, null=True, blank=True)
    payment_status = models.CharField(
        max_length=20,
        choices=[('paid', 'Paid'), ('unpaid', 'Unpaid')],
        default='unpaid'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        total = sum(item.subtotal for item in self.items.all())
        return total + self.delivery_charge - self.advance_payment

    @property
    def updated_total_amount(self):
        total = sum(item.subtotal for item in self.items.all())
        return total + self.delivery_charge

    def __str__(self):
        return f"{self.customer.name} - Total: {self.total_amount}"


class InvoiceItem(models.Model):
    invoice  = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price    = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self):
        if self.quantity is None or self.price is None:
            return 0
        return self.quantity * self.price

    def __str__(self):
        return f"Item {self.id} - Quantity: {self.quantity}, Price: {self.price}"
