import os
import sys
import django

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "perfectfitsoftware.settings")
sys.path.append('d:/Tron-Projects/Perfect-Fit/backend')
django.setup()

from adminApp.models import RentalBooking, StitchingOrder, AccessorySale, Transaction, Payment
from django.db import transaction

@transaction.atomic
def run_backfill():
    print("Clearing existing payments...")
    Payment.objects.all().delete()

    print("1. Backfilling Rentals from advance_paid...")
    for r in RentalBooking.objects.all():
        if r.advance_paid > 0:
            Payment.objects.create(
                amount=r.advance_paid,
                payment_method='CASH',
                payment_type='INCOME',
                notes='Initial advance (Legacy)',
                rental_booking=r,
                created_at=r.booking_date if hasattr(r, 'booking_date') else r.rental_date
            )

    print("2. Backfilling Stitching from advance_payment...")
    for s in StitchingOrder.objects.all():
        if getattr(s, 'advance_payment', 0) > 0:
            Payment.objects.create(
                amount=s.advance_payment,
                payment_method='CASH',
                payment_type='INCOME',
                notes='Initial advance (Legacy)',
                stitching_order=s,
                created_at=s.order_date
            )

    print("3. Migrating Transactions...")
    for t in Transaction.objects.all():
        kwargs = {
            'amount': t.amount,
            'payment_method': 'CASH',
            'notes': t.description,
        }
        
        if t.transaction_type == 'income':
            kwargs['payment_type'] = 'INCOME'
        else:
            kwargs['payment_type'] = 'EXPENSE'

        should_migrate = True

        if t.category == 'rental':
            # Skip accrued total revenue
            if not t.description:
                should_migrate = False
            else:
                # It's a damage deduction or specific manual log
                if t.reference_id:
                    try:
                        kwargs['rental_booking'] = RentalBooking.objects.get(id=t.reference_id)
                    except:
                        kwargs['notes'] = f"{kwargs['notes']} (Ref: RNT-{t.reference_id})"
                else:
                    kwargs['expense_category'] = 'Rental Income (Legacy)'
                    
        elif t.category == 'stitching':
            # Skip accrued total revenue
            should_migrate = False
            
        elif t.category == 'accessory':
            if t.reference_id:
                try:
                    kwargs['accessory_sale'] = AccessorySale.objects.get(id=t.reference_id)
                except:
                    kwargs['notes'] = f"Legacy Sale (Ref: ACC-{t.reference_id})"
            else:
                kwargs['expense_category'] = 'Accessory Sale (Legacy)'
                
        else:
            # Material purchases or pure expenses
            kwargs['expense_category'] = t.category

        if should_migrate:
            p = Payment.objects.create(**kwargs)
            # Override created_at
            p.created_at = t.created_at
            p.save()

    print(f"Total Payments generated: {Payment.objects.count()}")

if __name__ == '__main__':
    run_backfill()
