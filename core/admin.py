from django.contrib import admin
from .models import MenuItem, Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1 # Number of empty forms to display
    readonly_fields = ('subtotal',) # Subtotal is calculated

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'status', 'total_amount')
    list_filter = ('status', 'timestamp')
    inlines = [OrderItemInline]
    readonly_fields = ('total_amount',) # Total amount is calculated

class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price')
    list_filter = ('category',)

admin.site.register(MenuItem, MenuItemAdmin)
admin.site.register(Order, OrderAdmin)
# OrderItem is managed through OrderAdmin inline, but can be registered separately if direct access is needed
# admin.site.register(OrderItem)
