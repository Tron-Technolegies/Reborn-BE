import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfectfitsoftware.settings")
django.setup()

from django.test import Client
from adminApp.models import Customer, Product, Category, PhysicalUnit, RentalBooking

client = Client()

print("--- Running Verification Tests ---")

category, _ = Category.objects.get_or_create(name="Test Category", prefix="TST")
customer, _ = Customer.objects.get_or_create(phone="9998887776", defaults={"name": "Test User", "email": "test@example.com"})

product1, _ = Product.objects.get_or_create(code="TEST1", defaults={"name": "Test Suit", "description": "Test", "rental_price": 100, "colour": "black", "category": category})
product2, _ = Product.objects.get_or_create(code="TEST2", defaults={"name": "Test Pants", "description": "Test", "rental_price": 100, "colour": "black", "category": category})
product3, _ = Product.objects.get_or_create(code="TEST3", defaults={"name": "Test Shirt", "description": "Test", "rental_price": 100, "colour": "black", "category": category})

unit1, _ = PhysicalUnit.objects.get_or_create(product=product1, unit_id="TEST1-01", defaults={"status": "available"})
unit2, _ = PhysicalUnit.objects.get_or_create(product=product2, unit_id="TEST2-01", defaults={"status": "available"})
unit3, _ = PhysicalUnit.objects.get_or_create(product=product3, unit_id="TEST3-01", defaults={"status": "available"})

# Reset statuses to available for the test
PhysicalUnit.objects.filter(unit_id__in=["TEST1-01", "TEST2-01", "TEST3-01"]).update(status="available")

print(f"\n1. Create rental with 1 item...")
payload1 = {
    "phone": "9998887776", "name": "Test User", "email": "test@example.com",
    "rental_date": "2026-06-20", "return_date": "2026-06-25",
    "rental_amount": 100, "advance_paid": 50, "security_deposit": 10,
    "items": [{"product_id": product1.id, "unit_id": unit1.id}]
}
res1 = client.post('/api/orders/create/', data=json.dumps(payload1), content_type='application/json')
print(f"Status: {res1.status_code}, Resp: {res1.json()}")
order1_id = res1.json().get('order_id')
unit1.refresh_from_db()
print(f"Unit 1 Status: {unit1.status} (Expected: rented)")

print(f"\n2. Attempt double-booking same unit...")
res_double = client.post('/api/orders/create/', data=json.dumps(payload1), content_type='application/json')
print(f"Status: {res_double.status_code}, Resp: {res_double.json()}")
print(f"(Expected failure since unit is rented)")

print(f"\n3. Create rental with 3+ items...")
unit1_new, _ = PhysicalUnit.objects.get_or_create(product=product1, unit_id="TEST1-02", defaults={"status": "available"})
unit1_new.status = "available"
unit1_new.save()

payload2 = {
    "phone": "9998887776", "name": "Test User", "email": "test@example.com",
    "rental_date": "2026-06-20", "return_date": "2026-06-25",
    "rental_amount": 300, "advance_paid": 100, "security_deposit": 20,
    "items": [
        {"product_id": product1.id, "unit_id": unit1_new.id},
        {"product_id": product2.id, "unit_id": unit2.id},
        {"product_id": product3.id, "unit_id": unit3.id}
    ]
}

res3 = client.post('/api/orders/create/', data=json.dumps(payload2), content_type='application/json')
print(f"Status: {res3.status_code}, Resp: {res3.json()}")
order2_id = res3.json().get('order_id')

unit1_new.refresh_from_db()
unit2.refresh_from_db()
unit3.refresh_from_db()
print(f"Unit 1_New Status: {unit1_new.status}")
print(f"Unit 2 Status: {unit2.status}")
print(f"Unit 3 Status: {unit3.status}")

print(f"\n4. Return booking with multiple items...")
res4 = client.post(f'/api/orders/{order2_id}/return/', data=json.dumps({"damage_notes": "None"}), content_type='application/json')
print(f"Status: {res4.status_code}, Resp: {res4.json()}")
unit1_new.refresh_from_db()
unit2.refresh_from_db()
unit3.refresh_from_db()
print(f"Unit statuses after return: {unit1_new.status}, {unit2.status}, {unit3.status} (Expected: available)")

print(f"\n5. Attempt return twice...")
res5 = client.post(f'/api/orders/{order2_id}/return/', data=json.dumps({"damage_notes": "None"}), content_type='application/json')
print(f"Status: {res5.status_code}, Resp: {res5.json()}")

print(f"\n6. Cleanup test data...")
RentalBooking.objects.filter(customer=customer).delete()
PhysicalUnit.objects.filter(product__in=[product1, product2, product3]).delete()
Product.objects.filter(code__in=["TEST1", "TEST2", "TEST3"]).delete()
Category.objects.filter(prefix="TST").delete()
print("Done.")
