from django.test import TestCase
from decimal import Decimal
from .models import MenuItem, Order, OrderItem
from django.urls import reverse
from django.contrib.messages import get_messages # For testing messages

class MenuItemModelTests(TestCase):

    def test_create_menu_item(self):
        item = MenuItem.objects.create(
            name="Test Item",
            description="A delicious test item.",
            price=Decimal("9.99"),
            category="main_course"
        )
        self.assertEqual(item.name, "Test Item")
        self.assertEqual(item.price, Decimal("9.99"))
        self.assertEqual(str(item), "Test Item")

class OrderModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.item1 = MenuItem.objects.create(name="Coffee", price=Decimal("3.00"), category="beverage")
        cls.item2 = MenuItem.objects.create(name="Sandwich", price=Decimal("7.50"), category="main_course")
        cls.item3 = MenuItem.objects.create(name="Cake", price=Decimal("4.25"), category="dessert")

    def test_create_order(self):
        order = Order.objects.create()
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.total_amount, Decimal("0.00"))
        self.assertIsNotNone(order.timestamp)
        self.assertEqual(str(order), f"Order {order.id} - pending")

    def test_create_order_item_and_subtotal(self):
        order = Order.objects.create()
        order_item = OrderItem.objects.create(
            order=order,
            menu_item=self.item1,
            quantity=2
        )
        expected_subtotal = self.item1.price * 2
        self.assertEqual(order_item.subtotal, expected_subtotal)
        self.assertEqual(str(order_item), f"2 x {self.item1.name} for Order {order.id}")
        order.refresh_from_db() # Order total is updated by OrderItem save
        self.assertEqual(order.total_amount, expected_subtotal)


    def test_order_total_amount_calculation(self):
        order = Order.objects.create()

        oi1 = OrderItem.objects.create(order=order, menu_item=self.item1, quantity=2) # 2 * 3.00 = 6.00
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("6.00"))

        oi2 = OrderItem.objects.create(order=order, menu_item=self.item2, quantity=1) # 1 * 7.50 = 7.50
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("6.00") + Decimal("7.50"))

        oi1.quantity = 3
        oi1.save()
        order.refresh_from_db()
        self.assertEqual(order.total_amount, (self.item1.price * 3) + (self.item2.price * 1))

        expected_final_total = (self.item1.price * 3) + (self.item2.price * 1)
        self.assertEqual(order.total_amount, expected_final_total)

    def test_order_item_deletion_updates_total(self):
        order = Order.objects.create()
        oi1 = OrderItem.objects.create(order=order, menu_item=self.item1, quantity=2) # 6.00
        oi2 = OrderItem.objects.create(order=order, menu_item=self.item2, quantity=1) # 7.50
        order.refresh_from_db()
        self.assertEqual(order.total_amount, Decimal("13.50"))

        # Deleting oi2. The total amount should be updated by the view logic that calls order.update_total_amount()
        # Here in model tests, we are testing model logic, not view logic.
        # The model's OrderItem.delete() does not directly call order.update_total_amount().
        # So, we manually call it to test the recalculation logic of update_total_amount itself.
        oi2_id = oi2.id
        OrderItem.objects.get(id=oi2_id).delete() # Simulate deletion
        order.update_total_amount() # Manually trigger update
        self.assertEqual(order.total_amount, Decimal("6.00"))


    def test_order_status_and_string_representation(self):
        order = Order.objects.create(status='completed')
        self.assertEqual(str(order), f"Order {order.id} - completed")


class OrderViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.item1 = MenuItem.objects.create(name="Tea", price=Decimal("2.50"), category="beverage")
        cls.item2 = MenuItem.objects.create(name="Burger", price=Decimal("8.00"), category="main_course")
        cls.order1 = Order.objects.create()
        # OrderItem creation will trigger total_amount update on order1
        cls.order_item1 = OrderItem.objects.create(order=cls.order1, menu_item=cls.item1, quantity=2) # 5.00
        cls.order1.refresh_from_db() # Ensure order1 reflects the total from order_item1 creation

    def test_list_orders_view(self):
        response = self.client.get(reverse('core:list_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/order_list.html')
        self.assertIn(self.order1, response.context['orders'])

    def test_create_new_order_post(self):
        initial_order_count = Order.objects.count()
        response = self.client.post(reverse('core:create_new_order'))
        self.assertEqual(Order.objects.count(), initial_order_count + 1)
        new_order = Order.objects.latest('id')
        self.assertEqual(self.client.session.get('active_order_id'), new_order.id)
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': new_order.id}))

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertTrue(f"New order (ID: {new_order.id}) created." in str(messages[0]))


    def test_create_new_order_get(self):
        response = self.client.get(reverse('core:create_new_order'))
        self.assertRedirects(response, reverse('core:list_orders'))

    def test_view_order_detail(self):
        response = self.client.get(reverse('core:view_order', kwargs={'order_id': self.order1.id}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'core/order_detail.html')
        self.assertEqual(response.context['order'], self.order1)
        self.assertContains(response, self.item1.name)
        self.assertContains(response, self.order_item1.menu_item.name)

    def test_view_order_detail_not_found(self):
        response = self.client.get(reverse('core:view_order', kwargs={'order_id': 9999})) # Use a high ID
        self.assertEqual(response.status_code, 404)

    def test_add_item_to_order_post(self):
        order_for_test = Order.objects.create()
        item_to_add = self.item2 # Burger, 8.00
        url = reverse('core:add_item_to_order', kwargs={'order_id': order_for_test.id, 'menu_item_id': item_to_add.id})

        response = self.client.post(url, {'quantity': '3'})
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': order_for_test.id}))
        order_for_test.refresh_from_db()
        self.assertEqual(order_for_test.orderitem_set.count(), 1)
        new_order_item = order_for_test.orderitem_set.first()
        self.assertEqual(new_order_item.menu_item, item_to_add)
        self.assertEqual(new_order_item.quantity, 3)
        self.assertEqual(order_for_test.total_amount, item_to_add.price * 3) # 8.00 * 3 = 24.00

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f"{item_to_add.name} (x3) added to order." in str(m) for m in messages))

        # Test adding same item again (should update quantity)
        response = self.client.post(url, {'quantity': '2'}) # Add 2 more
        order_for_test.refresh_from_db()
        self.assertEqual(order_for_test.orderitem_set.count(), 1)
        updated_order_item = order_for_test.orderitem_set.first()
        self.assertEqual(updated_order_item.quantity, 3 + 2)
        self.assertEqual(order_for_test.total_amount, item_to_add.price * 5) # 8.00 * 5 = 40.00

    def test_add_item_to_order_get_not_allowed(self):
        url = reverse('core:add_item_to_order', kwargs={'order_id': self.order1.id, 'menu_item_id': self.item1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

    def test_update_order_item_quantity_post(self):
        # order1 has order_item1 (Tea x2, total 5.00)
        order_item_to_update = self.order_item1 # Tea x2
        url = reverse('core:update_order_item_quantity', kwargs={'order_item_id': order_item_to_update.id})

        # Update quantity to 5
        response = self.client.post(url, {'quantity': '5'})
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': self.order1.id}))
        order_item_to_update.refresh_from_db()
        self.order1.refresh_from_db()
        self.assertEqual(order_item_to_update.quantity, 5)
        self.assertEqual(self.order1.total_amount, self.item1.price * 5) # 2.50 * 5 = 12.50

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f"Quantity for {self.item1.name} updated to 5" in str(m) for m in messages))

        # Update quantity to 0 (should delete the item)
        initial_item_count = self.order1.orderitem_set.count()
        response = self.client.post(url, {'quantity': '0'})
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': self.order1.id}))
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.orderitem_set.count(), initial_item_count - 1)
        # Since order_item1 was the only item in order1, total should be 0
        self.assertEqual(self.order1.total_amount, Decimal("0.00"))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f"{self.item1.name} removed from order." in str(m) for m in messages))


    def test_remove_item_from_order_post(self):
        order_for_removal_test = Order.objects.create()
        item_to_be_removed = OrderItem.objects.create(order=order_for_removal_test, menu_item=self.item1, quantity=1)
        order_for_removal_test.refresh_from_db()
        self.assertEqual(order_for_removal_test.total_amount, self.item1.price * 1)

        url = reverse('core:remove_item_from_order', kwargs={'order_item_id': item_to_be_removed.id})
        item_count_before_delete = order_for_removal_test.orderitem_set.count()

        response = self.client.post(url)
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': order_for_removal_test.id}))
        order_for_removal_test.refresh_from_db()
        self.assertEqual(order_for_removal_test.orderitem_set.count(), item_count_before_delete - 1)
        self.assertEqual(order_for_removal_test.total_amount, Decimal("0.00"))

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f"{self.item1.name} removed from order" in str(m) for m in messages))

    def test_update_order_status_post(self):
        url = reverse('core:update_order_status', kwargs={'order_id': self.order1.id})
        new_status = 'completed'
        response = self.client.post(url, {'status': new_status})
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': self.order1.id}))
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, new_status)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any(f"Order {self.order1.id} status updated to {self.order1.get_status_display()}" in str(m) for m in messages))

    def test_update_order_status_invalid_status(self):
        url = reverse('core:update_order_status', kwargs={'order_id': self.order1.id})
        original_status = self.order1.status
        response = self.client.post(url, {'status': 'invalid_status_value'})
        self.assertRedirects(response, reverse('core:view_order', kwargs={'order_id': self.order1.id}))
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, original_status)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invalid status selected" in str(m) for m in messages))
