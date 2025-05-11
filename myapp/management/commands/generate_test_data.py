from django.core.management.base import BaseCommand
from myapp.models import Customer, Invoice, InvoiceItem
from django.utils import timezone
from decimal import Decimal
from uuid import uuid4
import random

class Command(BaseCommand):
    help = 'Generate 200 customers, 400 invoices, and 800 invoice items'

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Creating test data...")

        # Create Customers
        customers = []
        for i in range(1, 201):
            cust = Customer.objects.create(
                name=f"Test Customer {i}",
                address=f"{i} Example Street",
                phone_number=f"0300{i:07d}",
                phone_number2=f"0311{i:07d}" if i % 2 == 0 else "",
            )
            customers.append(cust)

        # Create Invoices
        invoices = []
        for i in range(1, 401):
            invoice = Invoice.objects.create(
                customer=random.choice(customers),
                advance_payment=Decimal(random.randint(0, 500)),
                delivery_charge=Decimal(random.randint(50, 300)),
                invoice_number=f"INV-{uuid4().hex[:6].upper()}",
                payment_method=random.choice(['Cash', 'JazzCash', 'UBL', 'Meezan Bank']),
                payment_status=random.choice(['paid', 'unpaid']),
                cod_number=f"COD{i:05d}",
                status=random.choice(['pending', 'printed', 'downloaded', 'both']),
            )
            invoices.append(invoice)

        # Create Invoice Items
        for i in range(800):
            InvoiceItem.objects.create(
                invoice=random.choice(invoices),
                product_name=f"Product {random.randint(1, 100)}",
                quantity=random.randint(1, 10),
                price=Decimal(random.randint(100, 1000)),
            )

        self.stdout.write(self.style.SUCCESS("✅ Successfully created test data"))
