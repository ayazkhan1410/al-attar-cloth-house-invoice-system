from django.urls import path
from . import views


urlpatterns = [
    path('', views.customer_list, name='customer_list'),
    path('invoices/new/', views.invoice_create, name='invoice_new'),
    path('invoices/new/<int:customer_id>/', views.invoice_create, name='invoice_new_with_customer'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.update_invoice, name='invoice_edit'),
    path('invoices/<int:pk>/detail-pdf/', views.invoice_detail_pdf, name='invoice_detail_pdf'),

    path('invoices/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('invoices/', views.invoice_list, name='invoice_list'),
    path("one-invoice-details/<int:pk>/", views.one_invoice_detail, name="one_invoice"),
    path('invoices/bulk-action/', views.bulk_invoice_action, name='bulk_invoice_action'),
    path('invoices/summary/', views.invoice_summary, name='invoice_summary'),
    path('customers/<int:pk>/edit/', views.customer_update, name='customer_edit'),
]
