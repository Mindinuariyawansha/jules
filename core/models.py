from django.db import models

class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=6, decimal_places=2)
    category = models.CharField(max_length=50, choices=[
        ('appetizer', 'Appetizer'),
        ('main_course', 'Main Course'),
        ('dessert', 'Dessert'),
        ('beverage', 'Beverage'),
    ])

    def __str__(self):
        return self.name

class Order(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Order {self.id} - {self.status}"

    def update_total_amount(self):
        # Use self.orderitem_set.all() which is the reverse relationship for OrderItem's ForeignKey
        self.total_amount = sum(item.subtotal for item in self.orderitem_set.all())
        self.save(update_fields=['total_amount']) # Avoid recursion by only updating total_amount

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='orderitem_set', on_delete=models.CASCADE)
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    # Subtotal will be calculated on save
    subtotal = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)


    def save(self, *args, **kwargs):
        self.subtotal = self.menu_item.price * self.quantity
        super().save(*args, **kwargs) # Save OrderItem first
        if self.order_id: # Ensure order is associated
             self.order.update_total_amount() # Then update the order's total

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} for Order {self.order.id}"
