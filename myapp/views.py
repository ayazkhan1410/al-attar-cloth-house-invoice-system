from datetime import datetime, time
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Customer, Invoice, InvoiceItem
from django.db import models
from django.utils.timezone import now
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
import urllib.parse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.timezone import localtime
from uuid import uuid4
from django.utils.dateparse import parse_date


def generate_unique_invoice_number():
    while True:
        code = f"INV-{uuid4().hex[:6].upper()}"
        if not Invoice.objects.filter(invoice_number=code).exists():
            return code


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.status = 'downloaded' if invoice.status != 'printed' else 'both'
    invoice.save()

    customer_name = invoice.customer.name.strip().replace(" ", "_") if invoice.customer.name else "Customer"
    date_str = localtime(now()).strftime("%Y-%m-%d")
    filename = f"Invoice_{customer_name}_{date_str}.pdf"

    context = {"invoice": invoice}
    pdf_response = render_to_pdf("invoice_print.html", context)

    # Set content disposition so file downloads with the correct name
    pdf_response['Content-Disposition'] = f'attachment; filename="{urllib.parse.quote(filename)}"'
    return pdf_response


def invoice_detail_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    # Update invoice status
    invoice.status = 'downloaded' if invoice.status != 'printed' else 'both'
    invoice.save()

    # Totals
    items = invoice.items.all()
    subtotal = sum(item.subtotal for item in items)
    total_amount = subtotal + invoice.delivery_charge
    grand_total = total_amount - invoice.advance_payment

    context = {
        'invoice': invoice,
        'items': items,
        'subtotal': subtotal,
        'total_amount': total_amount,
        'grand_total': grand_total,
    }

    pdf = render_to_pdf('invoice_detail_pdf.html', context)
    if pdf:
        customer_name = invoice.customer.name.strip().replace(" ", "_") if invoice.customer.name else "Customer"
        date_str = now().strftime("%Y-%m-%d")
        filename = f"Invoice_{customer_name}_{date_str}.pdf"
        pdf['Content-Disposition'] = f'attachment; filename="{urllib.parse.quote(filename)}"'
        return pdf
    else:
        return HttpResponse("PDF generation failed.", status=500)


def invoice_create(request, customer_id=None):
    customer = None
    if customer_id:
        customer = get_object_or_404(Customer, pk=customer_id) if customer_id else None

    if request.method == 'POST':
        # Upsert customer
        name = request.POST.get('customer_name')
        phone = (request.POST.get('customer_phone') or '').replace("-", "").strip()
        phone2 = (request.POST.get('customer_phone2') or '').replace("-", "").strip()
        address = request.POST.get('customer_address')

        # If customer exists and phone numbers changed, validate
        if customer:
            if phone != customer.phone_number and Customer.objects.filter(phone_number=phone).exclude(pk=customer.pk).exists():
                messages.error(request, "This phone number is already assigned to another customer.")
                return redirect('invoice_new')

            if phone2 and phone2 != customer.phone_number2 and Customer.objects.filter(phone_number2=phone2).exclude(pk=customer.pk).exists():
                messages.error(request, "This secondary phone number is already assigned to another customer.")
                return redirect('invoice_new')

        # If creating new customer, validate without exclusion
        if not customer:
            if Customer.objects.filter(phone_number=phone).exists():
                messages.error(request, "This phone number is already assigned to another customer.")
                return redirect('invoice_new')

            if phone2 and Customer.objects.filter(phone_number2=phone2).exists():
                messages.error(request, "This secondary phone number is already assigned to another customer.")
                return redirect('invoice_new')

        customer, _ = Customer.objects.update_or_create(
            phone_number=phone,
            defaults={'name': name, 'address': address, 'phone_number2': phone2}
        )

        # Retrieve form data
        advance = Decimal(request.POST.get('advance_payment') or 0)
        delivery_charges = Decimal(request.POST.get('delivery_charges') or 0)
        payment_method = request.POST.get('payment_method')
        other_payment_method = request.POST.get('other_payment_method')
        payment_status = request.POST.get('payment_status')

        # Validate inputs
        if advance < 0 or delivery_charges < 0:
            messages.error(request, "Advance and Delivery Charges cannot be negative.")
            return redirect('invoice_new')

        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')
        product_names = request.POST.getlist('product_name[]')

        if not quantities or not prices:
            messages.error(request, "You must enter at least one line item.")
            return redirect('invoice_new')

        # Determine final payment method
        final_payment_method = other_payment_method if payment_method == 'Other' else payment_method

        # Create invoice
        invoice = Invoice.objects.create(
            customer=customer,
            advance_payment=advance,
            delivery_charge=delivery_charges,
            invoice_number=generate_unique_invoice_number(),
            payment_method=final_payment_method,
            payment_status=payment_status
        )

        # Create invoice items
        for name, q, p in zip(product_names, quantities, prices):
            if q and p:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product_name=name,
                    quantity=int(q),
                    price=Decimal(p)
                )

        # Determine action
        action = request.POST.get('action')
        if action == 'print':
            return redirect('invoice_detail', pk=invoice.pk)
        else:
            messages.success(request, "Invoice has been saved successfully.")
            return redirect('invoice_list')
    return render(request, 'invoice_form.html', {'customer': customer})


def invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    return render(request, 'invoice_print.html', {
        'invoice': invoice,
    })


def customer_list(request):
    q = request.GET.get('q', '')
    queryset = Customer.objects.filter(
        models.Q(name__icontains=q) | models.Q(phone_number__icontains=q)
    ).order_by('-created_at')

    paginator = Paginator(queryset, 50)
    page_number = request.GET.get('page')
    customers = paginator.get_page(page_number)

    return render(request, 'customer_list.html', {
        'customers': customers,
        'q': q,
        'start_index': customers.start_index(),
    })


def invoice_list(request):
    q = request.GET.get('q', '')
    invoices = Invoice.objects.filter(
        Q(customer__name__icontains=q) |
        Q(customer__phone_number__icontains=q) |
        Q(invoice_number__icontains=q) 
    ).order_by('-created_at')

    paginator = Paginator(invoices, 24)
    page_number = request.GET.get('page')
    paged_invoices = paginator.get_page(page_number)

    today = localtime(now()).date()
    this_month_start = today.replace(day=1)

    today_items = InvoiceItem.objects.filter(
        invoice__created_at__date=today
    )

    month_items = InvoiceItem.objects.filter(
        invoice__created_at__date__gte=this_month_start
    )

    # CONFIRM PRINTED CUSTOMER 
    confirm_printed_customer = Invoice.objects.filter(
        created_at__date=today,
        status='both'
    ).values('customer').distinct()

    todays_deal_customer = Invoice.objects.filter(
        created_at__date=today
    ).values('customer').distinct()

    month_deal_customer = Invoice.objects.filter(
        created_at__date__gte=this_month_start
    ).values('customer').distinct()

    summary = {
        "today_qty": sum(item.quantity for item in today_items),
        "today_total": sum(item.subtotal for item in today_items),
        "month_qty": sum(item.quantity for item in month_items),
        "month_total": sum(item.subtotal for item in month_items),
        'todays_deal_customer': len(todays_deal_customer),
        'month_deal_customer': len(month_deal_customer),
        "confirm_printed_customer": len(confirm_printed_customer),
    }

    return render(request, 'invoice_list.html', {
        'invoices': paged_invoices,
        'q': q,
        'start_index': paged_invoices.start_index(),
        'summary': summary,
        'month_deal_customer': month_deal_customer,
    })


def update_invoice(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    items = invoice.items.all()

    if request.method == 'POST':
        # Update invoice fields
        invoice.advance_payment = Decimal(request.POST.get('advance_payment') or 0)
        invoice.delivery_charge = Decimal(request.POST.get('delivery_charge') or 0)
        invoice.save()

        # Clear and recreate invoice items
        invoice.items.all().delete()

        product_names = request.POST.getlist('product_name[]')
        quantities = request.POST.getlist('quantity[]')
        prices = request.POST.getlist('price[]')

        for name, qty, price in zip(product_names, quantities, prices):
            if name.strip() and qty and price:
                InvoiceItem.objects.create(
                    invoice=invoice,
                    product_name=name.strip(),
                    quantity=int(qty),
                    price=Decimal(price)
                )

        messages.success(request, "Invoice updated successfully.")
        return redirect('one_invoice', pk=invoice.pk)

    return render(request, 'invoice_update.html', {
        'invoice': invoice,
        'items': items,
    })


def one_invoice_detail(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method == 'POST':
        invoice.payment_status = request.POST.get('payment_status', invoice.payment_status)
        invoice.cod_number = request.POST.get('cod_number', invoice.cod_number)
        invoice.save()
        messages.success(request, "Invoice payment details updated successfully.")
        return redirect('one_invoice', pk=invoice.pk)

    # Calculate subtotal and grand totals
    items = invoice.items.all()
    subtotal = sum(item.subtotal for item in items)
    total_amount = subtotal + invoice.delivery_charge
    grand_total = total_amount - invoice.advance_payment

    return render(request, 'invoice_detail.html', {
        'invoice': invoice,
        'subtotal': subtotal,
        'total_amount': total_amount,
        'grand_total': grand_total,
    })


def chunked(iterable, n):
    """Yield successive n-sized chunks from iterable."""
    for i in range(0, len(iterable), n):
        yield iterable[i:i + n]


def bulk_invoice_action(request):
    if request.method == 'POST':
        ids = request.POST.getlist('invoice_ids')
        action = request.POST.get('action')

        if not ids:
            messages.warning(request, "No invoices selected.")
            return redirect('invoice_list')

        invoices = list(Invoice.objects.filter(
            id__in=ids).select_related('customer').prefetch_related('items'))

        for invoice in invoices:
            invoice.total_quantity = sum(item.quantity for item in invoice.items.all())

        for invoice in invoices:
            if action == 'print':
                invoice.status = 'printed' if invoice.status != 'downloaded' else 'both'
            elif action == 'download':
                invoice.status = 'downloaded' if invoice.status != 'printed' else 'both'
            invoice.save()

        invoice_groups = list(chunked(invoices, 6))
        context = {'invoice_groups': invoice_groups}

        if action == 'print':
            return render(request, 'multiple_invoice_print.html', context)

        elif action == 'download':
            pdf_response = render_to_pdf('multiple_invoice_print.html', context)

            invoice_labels = [inv.invoice_number or f"INV{inv.id}" for inv in invoices]
            label_string = "_".join(invoice_labels)[:100]  # truncate to avoid file name too long

            now_str = localtime(now()).strftime('%Y-%m-%d_%H-%M')
            filename = f"Invoices_{label_string}_{now_str}.pdf"

            pdf_response['Content-Disposition'] = f'attachment; filename="{urllib.parse.quote(filename)}"'
            return pdf_response

    return redirect('invoice_list')


def invoice_summary(request):
    time_filter = request.GET.get('time_filter')
    status = request.GET.get('status')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    start_time_str = request.GET.get('start_time')
    end_time_str = request.GET.get('end_time')

    today = localtime(now()).date()
    if time_filter == 'today':
        start_date = end_date = today
    elif time_filter == 'monthly':
        start_date = today.replace(day=1)
        end_date = today
    elif time_filter == 'yearly':
        start_date = today.replace(month=1, day=1)
        end_date = today
    elif time_filter == 'custom' and start_date_str and end_date_str:
        start_date = parse_date(start_date_str)
        end_date = parse_date(end_date_str)
    else:
        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None

    invoices = Invoice.objects.all().select_related('customer').prefetch_related('items')

    # Time-based filtering
    if start_date and end_date:
        start_datetime = datetime.combine(start_date, time.min)
        end_datetime = datetime.combine(end_date, time.max)

        if start_time_str:
            h, m = map(int, start_time_str.split(":"))
            start_datetime = start_datetime.replace(hour=h, minute=m)

        if end_time_str:
            h, m = map(int, end_time_str.split(":"))
            end_datetime = end_datetime.replace(hour=h, minute=m)

        invoices = invoices.filter(created_at__range=(start_datetime, end_datetime))

    if status:
        invoices = invoices.filter(payment_status=status)

    for invoice in invoices:
        invoice.total_quantity = sum(item.quantity for item in invoice.items.all())
        invoice.total_price = sum(item.price * item.quantity for item in invoice.items.all())

        if invoice.payment_status == 'paid':
            invoice.cod_collected = (invoice.total_price + invoice.delivery_charge) - invoice.advance_payment
        else:
            invoice.cod_collected = 0

    paginator = Paginator(invoices, 100)
    page_number = request.GET.get('page')
    paged_invoices = paginator.get_page(page_number)

    summary = {
        "total": sum(inv.updated_total_amount for inv in invoices),
        "paid": sum(inv.advance_payment + inv.total_amount if inv.payment_status == 'paid' else 0 for inv in invoices),
        "pending": sum(inv.total_amount for inv in invoices if inv.payment_status != 'paid'),
        "total_advance": sum(inv.advance_payment for inv in invoices),
        "total_suits": sum(inv.total_quantity for inv in invoices),
        "cod_received": sum(inv.cod_collected for inv in invoices),
    }

    return render(request, 'invoice_summary.html', {
        'invoices': paged_invoices,
        'summary': summary,
        'time_filter': time_filter,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'start_time': start_time_str,
        'end_time': end_time_str,
        'status': status,
    })


def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone').replace("-", "").strip()
        phone2 = (request.POST.get('phone2') or '').replace("-", "").strip()
        address = request.POST.get('address')

        # Validate phone uniqueness
        if Customer.objects.exclude(pk=customer.pk).filter(phone_number=phone).exists():
            messages.error(request, "Primary phone number is already used by another customer.")
            return redirect('customer_edit', pk=pk)

        if phone2 and Customer.objects.exclude(pk=customer.pk).filter(phone_number2=phone2).exists():
            messages.error(request, "Secondary phone number is already used by another customer.")
            return redirect('customer_edit', pk=pk)

        # Save updates
        customer.name = name
        customer.phone_number = phone
        customer.phone_number2 = phone2
        customer.address = address
        customer.save()

        messages.success(request, "Customer updated successfully.")
        return redirect('customer_list')

    return render(request, 'customer_edit.html', {'customer': customer})
