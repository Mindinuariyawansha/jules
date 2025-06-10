from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages # For displaying messages to the user
from .models import MenuItem, Order, OrderItem

# Existing menu_list view
def menu_list(request):
    menu_items = MenuItem.objects.all().order_by('category', 'name')
    context = {
        'menu_items': menu_items,
        'categories': MenuItem._meta.get_field('category').choices
    }
    return render(request, 'core/menu.html', context)

# Order Management Views

def list_orders(request):
    # Example: List pending and in-progress orders, newest first
    orders = Order.objects.filter(status__in=['pending', 'in_progress']).order_by('-timestamp')
    # For simplicity, let's list all for now, or a fixed number
    # orders = Order.objects.all().order_by('-timestamp')[:20] # Get latest 20
    context = {'orders': orders}
    return render(request, 'core/order_list.html', context) # Template to be created

def create_new_order(request):
    if request.method == 'POST':
        # Potentially take some initial info if needed, e.g., table number
        order = Order.objects.create() # Defaults status to 'pending'
        request.session['active_order_id'] = order.id
        messages.success(request, f"New order (ID: {order.id}) created.")
        return redirect('core:view_order', order_id=order.id)
    # If GET, perhaps redirect to a page that has a "Create New Order" button
    # For now, let's assume this is mostly POST-driven or redirects to a general order page/dashboard
    return redirect('core:list_orders') # Or to a dashboard page if one exists

def view_order(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    menu_items = MenuItem.objects.all().order_by('category', 'name') # To select items from
    # order_items are accessible via order.orderitem_set.all() in template
    context = {
        'order': order,
        'menu_items': menu_items,
        'all_status_choices': Order._meta.get_field('status').choices, # For status update dropdown
    }
    return render(request, 'core/order_detail.html', context) # Template to be created

@require_POST
def add_item_to_order(request, order_id, menu_item_id):
    order = get_object_or_404(Order, id=order_id)
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)

    quantity = int(request.POST.get('quantity', 1))
    if quantity <= 0:
        messages.error(request, "Quantity must be a positive number.")
        return redirect('core:view_order', order_id=order.id)

    # Check if item already in order, if so update quantity
    order_item, created = OrderItem.objects.get_or_create(
        order=order,
        menu_item=menu_item,
        defaults={'quantity': quantity}
    )

    if not created:
        order_item.quantity += quantity

    order_item.save() # This will update subtotal and order total via model's save method
    messages.success(request, f"{menu_item.name} (x{quantity}) added to order.")
    return redirect('core:view_order', order_id=order.id)

@require_POST
def update_order_item_quantity(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id)
    new_quantity = int(request.POST.get('quantity', 0))

    if new_quantity > 0:
        order_item.quantity = new_quantity
        order_item.save()
        messages.success(request, f"Quantity for {order_item.menu_item.name} updated to {new_quantity}.")
    elif new_quantity == 0:
        item_name = order_item.menu_item.name
        order_id = order_item.order.id
        order_item.delete()
        # Manually update order total after deletion, as signals aren't set up for post_delete
        # The OrderItem.save() on other items will keep it correct, but direct delete needs this.
        order = Order.objects.get(id=order_id)
        order.update_total_amount()
        messages.success(request, f"{item_name} removed from order.")
        return redirect('core:view_order', order_id=order_id) # Redirect to the order after deletion

    return redirect('core:view_order', order_id=order_item.order.id)


@require_POST
def remove_item_from_order(request, order_item_id):
    order_item = get_object_or_404(OrderItem, id=order_item_id)
    order_id = order_item.order.id
    item_name = order_item.menu_item.name

    order_item.delete()

    # Manually update total after delete, because OrderItem.delete() doesn't trigger OrderItem.save()
    # which is where the order total update is currently called from.
    # A better long-term solution is Django signals (post_delete).
    order = get_object_or_404(Order, id=order_id)
    order.update_total_amount()

    messages.success(request, f"{item_name} removed from order.")
    return redirect('core:view_order', order_id=order_id)

@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')

    # Validate if new_status is a valid choice
    valid_statuses = [choice[0] for choice in Order._meta.get_field('status').choices]
    if new_status in valid_statuses:
        order.status = new_status
        order.save()
        messages.success(request, f"Order {order.id} status updated to {order.get_status_display()}.")
    else:
        messages.error(request, "Invalid status selected.")

    return redirect('core:view_order', order_id=order.id)
