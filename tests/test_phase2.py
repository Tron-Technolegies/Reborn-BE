import os
import django
import json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfectfitsoftware.settings")
django.setup()

from django.test import Client
from adminApp.models import Customer, Product, Category, PhysicalUnit, RentalBooking, AlterationType, Alteration

client = Client()

print("--- Running Verification Tests for Phase 2 ---")

category, _ = Category.objects.get_or_create(name="Phase 2 Cat", prefix="PH2")
customer, _ = Customer.objects.get_or_create(phone="1112223334", defaults={"name": "Test User 2", "email": "test2@example.com"})
product1, _ = Product.objects.get_or_create(code="PH2-001", defaults={"name": "Test Dress", "description": "Test", "rental_price": 200, "colour": "red", "category": category})

unit1, _ = PhysicalUnit.objects.get_or_create(product=product1, unit_id="PH2-01", defaults={"status": "available"})
unit1.status = "available"
unit1.save()

# 1. Create Alteration Type
res_type = client.post('/api/alteration-types/create/', data=json.dumps({
    "name": "Sleeve Adjustment",
    "description": "Shorten or lengthen sleeves"
}), content_type='application/json')
print(f"Alteration Type Create: {res_type.status_code}, {res_type.json()}")

# 2. Create PRE_BOOKING
payload = {
    "phone": "1112223334", "name": "Test User 2", "email": "test2@example.com",
    "rental_date": "2026-07-01", "return_date": "2026-07-05",
    "booking_type": "PRE_BOOKING",
    "rental_amount": 200, "advance_paid": 50, "security_deposit": 10,
    "items": [{"product_id": product1.id, "unit_id": unit1.id}]
}
res_book1 = client.post('/api/orders/create/', data=json.dumps(payload), content_type='application/json')
print(f"Pre-Booking Create: {res_book1.status_code}, {res_book1.json()}")
order1_id = res_book1.json().get('order_id')
unit1.refresh_from_db()
print(f"Unit 1 Status after Pre-Booking: {unit1.status} (Expected: available)")

# 3. Create Overlapping PRE_BOOKING (should fail)
payload_overlap = {
    "phone": "1112223334", "name": "Test User 2", "email": "test2@example.com",
    "rental_date": "2026-07-03", "return_date": "2026-07-07",
    "booking_type": "PRE_BOOKING",
    "rental_amount": 200, "advance_paid": 50, "security_deposit": 10,
    "items": [{"product_id": product1.id, "unit_id": unit1.id}]
}
res_overlap = client.post('/api/orders/create/', data=json.dumps(payload_overlap), content_type='application/json')
print(f"Overlapping Pre-Booking Create: {res_overlap.status_code}, {res_overlap.json()}")

# 4. Create Alteration for Booking
if order1_id:
    alt_type_id = res_type.json().get("id")
    res_alt = client.post('/api/alterations/create/', data=json.dumps({
        "booking_id": order1_id,
        "product_id": product1.id,
        "alteration_type_id": alt_type_id,
        "notes": "Shorten by 2 inches",
        "expected_completion_date": "2026-06-25"
    }), content_type='application/json')
    print(f"Alteration Create: {res_alt.status_code}, {res_alt.json()}")

print("Done.")

# Cleanup
RentalBooking.objects.filter(customer=customer).delete()
PhysicalUnit.objects.filter(product=product1).delete()
Product.objects.filter(code="PH2-001").delete()
Category.objects.filter(prefix="PH2").delete()
AlterationType.objects.filter(name="Sleeve Adjustment").delete()
