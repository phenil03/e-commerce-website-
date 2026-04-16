import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from ecom.models import Order, OrderItem

def reset_orders():
    print("Deleting all existing orders and order items...")
    OrderItem.objects.all().delete()
    Order.objects.all().delete()

    print("Resetting auto-increment counter...")
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='ecom_order';")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='ecom_orderitem';")
    
    print("Successfully reset! Your next order will be #1.")

if __name__ == "__main__":
    reset_orders()
