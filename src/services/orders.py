from datetime import datetime

class Order:
    def __init__(self, order_id, user_id, product_id, quantity, status='pending'):
        self.order_id = order_id
        self.user_id = user_id
        self.product_id = product_id
        self.quantity = quantity
        self.status = status
        self.created_at = datetime.now()

    def update_status(self, new_status):
        self.status = new_status

    def to_dict(self):
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'quantity': self.quantity,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class OrderService:
    def __init__(self):
        self.orders = {}

    def create_order(self, user_id, product_id, quantity):
        order_id = len(self.orders) + 1
        order = Order(order_id, user_id, product_id, quantity)
        self.orders[order_id] = order
        return order.to_dict()

    def get_order(self, order_id):
        order = self.orders.get(order_id)
        return order.to_dict() if order else None

    def update_order(self, order_id, new_status):
        order = self.orders.get(order_id)
        if order:
            order.update_status(new_status)
            return order.to_dict()
        return None

    def list_orders(self):
        return [order.to_dict() for order in self.orders.values()]