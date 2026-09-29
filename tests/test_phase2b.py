import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfectfitsoftware.settings")
django.setup()

from adminApp.models import RentalBooking, Alteration, AlterationType, Product, PhysicalUnit, Customer
from datetime import datetime, timedelta

def test():
    customer = Customer.objects.first()
    product = Product.objects.first()
    unit = PhysicalUnit.objects.filter(product=product).first()
    alt_type = AlterationType.objects.first()

    if not all([customer, product, unit, alt_type]):
        print("Missing required initial data.")
        return

    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)

    # 1. Test Alteration Overdue
    b1 = RentalBooking.objects.create(customer=customer, rental_date=today, return_date=tomorrow, booking_type='PRE_BOOKING', status='PRE_BOOKED', rental_amount=100)
    a1 = Alteration.objects.create(booking=b1, product=product, alteration_type=alt_type, expected_completion_date=today - timedelta(days=2), status='PENDING')

    # 2. Test Pickups Tomorrow
    b2 = RentalBooking.objects.create(customer=customer, rental_date=tomorrow, return_date=tomorrow + timedelta(days=2), booking_type='PRE_BOOKING', status='PRE_BOOKED', rental_amount=100)

    # Check views.py get_urgent_alerts logic
    from django.test import RequestFactory
    from adminApp.views import get_urgent_alerts
    import json

    request = RequestFactory().get('/api/dashboard/urgent-alerts/')
    response = get_urgent_alerts(request)
    data = json.loads(response.content)

    print("Overdue:", len(data['overdue_alterations']))
    print("Pickups Tomorrow:", len(data['pickups_tomorrow']))

    assert len(data['overdue_alterations']) >= 1
    assert len(data['pickups_tomorrow']) >= 1
    print("Test passed!")

    # Cleanup
    b1.delete()
    b2.delete()

if __name__ == "__main__":
    test()
