from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Customer, Invoice, InvoiceItem, MyUser


@admin.register(MyUser)
class MyUserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'is_admin', 'is_active')
    search_fields = ('email', 'username')
    ordering = ('email',)
    list_filter = ('is_admin', 'is_active')
    filter_horizontal = ()

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username',)}),
        ('Permissions', {'fields': ('is_admin', 'is_active')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'username',
                    'password1',
                    'password2',
                    'is_admin',
                    'is_active',
                ),
            },
        ),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'phone_number', 'phone_number2', 'created_at', 'updated_at')
    search_fields = ('name', 'phone_number', 'address')
    list_filter = ('created_at',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'invoice_number', 'invoice_date', 'advance_payment', 'status', 'payment_status', 'cod_number', 'payment_method', 'payment_status', 'updated_at', )
    search_fields = ('customer__name',)
    list_filter = ('created_at',)
    readonly_fields = ('total_amount',)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display    = ('invoice', 'product_name', 'quantity', 'price', 'subtotal')
    search_fields   = ('invoice__customer__name',)
    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ('subtotal',)
        return ()
