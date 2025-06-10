from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('menu/', views.menu_list, name='menu_list'), # Keep previous menu URL

    # Order Management URLs
    path('orders/', views.list_orders, name='list_orders'), # To list active/all orders
    path('order/new/', views.create_new_order, name='create_new_order'),
    path('order/<int:order_id>/', views.view_order, name='view_order'),
    # Using POST to view_order for adding items is a common pattern,
    # but explicit URLs can be clearer initially.
    path('order/<int:order_id>/add_item/<int:menu_item_id>/', views.add_item_to_order, name='add_item_to_order'),
    path('order/item/<int:order_item_id>/update/', views.update_order_item_quantity, name='update_order_item_quantity'),
    path('order/item/<int:order_item_id>/remove/', views.remove_item_from_order, name='remove_item_from_order'),
    path('order/<int:order_id>/update_status/', views.update_order_status, name='update_order_status'),
]
