import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce.settings')
django.setup()

from django.contrib.auth.models import User
from ecom.models import Customer, Product

def seed_data():
    print("Seeding data...")
    
    # 1. Create Admin (Superuser)
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Admin created: username='admin', password='admin123'")
    else:
        print("Admin already exists.")

    # 2. Create a Sample Customer
    if not User.objects.filter(username='customer').exists():
        user = User.objects.create_user('customer', 'customer@example.com', 'customer123')
        user.first_name = "John"
        user.last_name = "Doe"
        user.save()
        
        Customer.objects.create(
            user=user, 
            address="123 Default Street, City", 
            mobile="9876543210"
        )
        print("Customer created: username='customer', password='customer123'")
    else:
        print("Customer already exists.")

    # 3. Create Sample Products if none exist
    if not Product.objects.exists():
        Product.objects.create(
            name="Sample Laptop",
            price=50000,
            description="A high performance sample laptop.",
            category="Electronics",
            stock=10
        )
        Product.objects.create(
            name="Sample Watch",
            price=2000,
            description="An elegant sample watch.",
            category="Fashion",
            stock=15
        )
        print("Sample products created.")
    else:
        print("Products already exist.")

    print("Seeding completed!")

if __name__ == '__main__':
    seed_data()
