from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import io
import os
from django.conf import settings
from django.http import FileResponse, JsonResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle

# ── Health check ──────────────────────────────────────────────────────────────
from django.http import JsonResponse

def health_check(request):
    return JsonResponse({"status": "ok"})

from django.http import JsonResponse
from .models import Material, MaterialPurchase, Product, StitchingOrder, Accessory, AccessorySale, PhysicalUnit, Payment
import json
from django.views.decorators.csrf import csrf_exempt

from .models import Category

#  CREATE

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Product, Category
import json

@csrf_exempt
def create_rental_item(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST method required"},
            status=405
        )

    # Handle JSON and FormData
    if request.content_type == "application/json":
        data = json.loads(request.body)
        image = None
    else:
        data = request.POST
        image = request.FILES.get("image")

    try:
        category = Category.objects.get(
            id=data.get("category_id")
        )
    except Category.DoesNotExist:
        return JsonResponse(
            {"error": "Invalid category"},
            status=400
        )

    item = Product.objects.create(
        name=data.get("name"),
        category=category,
        colour=data.get("colour", ""),
        description=data.get("description"),
        rental_price=data.get("rental_price"),
        image=image
    )

    # Stock quantity
    stock_data = data.get("stock_data")

    # FormData sends stock_data as a JSON string
    if stock_data and isinstance(stock_data, str):
        try:
            stock_data = json.loads(stock_data)
        except (json.JSONDecodeError, TypeError):
            stock_data = None

    # Create physical units
    if isinstance(stock_data, list) and stock_data:

        unit_index = 1

        for group in stock_data:
            size = group.get("size") or "Free Size"
            qty = int(group.get("qty", 1))

            if qty < 1:
                continue

            for _ in range(qty):
                PhysicalUnit.objects.create(
                    product=item,
                    unit_id=f"{item.code}-{str(unit_index).zfill(2)}",
                    size=size,
                    status="available"
                )

                unit_index += 1

    else:
        # Fallback: simple total_stock
        qty = int(data.get("total_stock", 1))
        size = data.get("size") or "Free Size"

        for i in range(qty):
            PhysicalUnit.objects.create(
                product=item,
                unit_id=f"{item.code}-{str(i + 1).zfill(2)}",
                size=size,
                status="available"
            )

    return JsonResponse({
        "message": "Item created",
        "id": item.id,
        "code": item.code,
        "image_url": item.image.url if item.image else None
    })

#  GET ALL
def get_all_rental_items(request):
    if request.method == "GET":
        from .models import RentalBooking, Alteration
        items = Product.objects.all()

        data = []
        for item in items:
            data.append({
                "id": item.id,
                "code": item.code,
                "name": item.name,
                "category": item.category.name,
                "category_id": item.category.id,
                "size": ", ".join(set(item.units.values_list("size", flat=True))),
                "colour": item.colour,
                "description": item.description,
                "rental_price": float(item.rental_price),
                "total_stock": item.total_stock,
                "available_stock": item.available_stock,
                "condition": "ready" if item.is_available else "out_of_stock",
                "is_available": item.is_available,
                "times_rented": item.total_rented_times,
                "image_url": item.image.url if item.image else None,
                "has_rented": item.units.filter(status='rented').exists(),
                "has_prebooked": RentalBooking.objects.filter(items__product=item, status='PRE_BOOKED').exists(),
                "has_returned": RentalBooking.objects.filter(items__product=item, status='RETURNED').exists(),
                "has_alteration": Alteration.objects.filter(product=item, status__in=['PENDING', 'IN_PROGRESS']).exists(),
            })

        return JsonResponse(data, safe=False)

# GET SINGLE ITEM
def get_rental_item(request, item_id):
    try:
        item = Product.objects.get(id=item_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    data = {
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "category": item.category.name,
        "category_id": item.category.id,
        "size": ", ".join(set(item.units.values_list("size", flat=True))),
        "colour": item.colour,
        "description": item.description,
        "rental_price": float(item.rental_price),
        "total_stock": item.total_stock,
        "available_stock": item.available_stock,
        "condition": "ready" if item.is_available else "out_of_stock",
        "is_available": item.is_available,
        "times_rented": item.total_rented_times,
        "image_url": item.image.url if item.image else None  #  added
    }

    return JsonResponse(data)

#  UPDATE
from .models import Product, Category
from django.http import JsonResponse
import json


@csrf_exempt
def update_rental_item(request, item_id):
    if request.method != "PUT":
        return JsonResponse(
            {"error": "Invalid request method"},
            status=405
        )

    # Handle both JSON & form-data
    if request.content_type == "application/json":
        data = json.loads(request.body)
        image = None
    else:
        data = request.POST
        image = request.FILES.get("image")

    try:
        item = Product.objects.get(id=item_id)
    except Product.DoesNotExist:
        return JsonResponse(
            {"error": "Item not found"},
            status=404
        )

    # Update basic fields
    item.name = data.get("name", item.name)
    item.colour = data.get("colour", item.colour)
    item.description = data.get(
        "description",
        item.description
    )
    item.rental_price = data.get(
        "rental_price",
        item.rental_price
    )

    # Update image if provided
    if image:
        item.image = image

    # Update category
    if "category_id" in data:
        try:
            category = Category.objects.get(
                id=data.get("category_id")
            )
            item.category = category
        except Category.DoesNotExist:
            return JsonResponse(
                {"error": "Invalid category"},
                status=400
            )

    # --------------------------------------------------
    # UPDATE STOCK QUANTITY
    # --------------------------------------------------

    if "total_stock" in data:

        try:
            requested_stock = int(data.get("total_stock"))
        except (TypeError, ValueError):
            return JsonResponse(
                {"error": "Invalid stock quantity"},
                status=400
            )

        if requested_stock < 0:
            return JsonResponse(
                {"error": "Stock quantity cannot be negative"},
                status=400
            )

        units = PhysicalUnit.objects.filter(
            product=item
        )

        current_stock = units.count()

        # Units that cannot be removed automatically
        unavailable_units = units.exclude(
            status="available"
        )

        unavailable_count = unavailable_units.count()

        # We cannot reduce below rented/washing/repair/etc. units
        if requested_stock < unavailable_count:
            return JsonResponse(
                {
                    "error": (
                        f"Cannot reduce stock to {requested_stock}. "
                        f"{unavailable_count} unit(s) are currently "
                        f"not available."
                    )
                },
                status=400
            )

        # Increase stock
        if requested_stock > current_stock:

            units_to_add = requested_stock - current_stock

            available_units = units.filter(
                status="available"
            )

            # Find the next unit number
            existing_numbers = []

            for unit in units:
                try:
                    number = int(
                        unit.unit_id.rsplit("-", 1)[1]
                    )
                    existing_numbers.append(number)
                except (ValueError, IndexError):
                    pass

            next_number = (
                max(existing_numbers) + 1
                if existing_numbers
                else 1
            )

            for _ in range(units_to_add):
                PhysicalUnit.objects.create(
                    product=item,
                    unit_id=(
                        f"{item.code}-"
                        f"{str(next_number).zfill(2)}"
                    ),
                    size="Free Size",
                    status="available"
                )

                next_number += 1

        # Reduce stock
        elif requested_stock < current_stock:

            units_to_remove = current_stock - requested_stock

            removable_units = list(
                units.filter(
                    status="available"
                ).order_by("-id")[:units_to_remove]
            )

            if len(removable_units) < units_to_remove:
                return JsonResponse(
                    {
                        "error": (
                            "Not enough available units "
                            "to reduce stock."
                        )
                    },
                    status=400
                )

            for unit in removable_units:
                unit.delete()

    item.save()

    return JsonResponse({
        "message": "Item updated successfully",
        "code": item.code,
        "total_stock": item.total_stock,
        "available_stock": item.available_stock,
        "image_url": (
            item.image.url
            if item.image
            else None
        )
    })

# DELETE
@csrf_exempt
def delete_rental_item(request, item_id):
    if request.method == "DELETE":
        try:
            item = Product.objects.get(id=item_id)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Item not found"}, status=404)

        item.delete()

        return JsonResponse({"message": "Item deleted"})
    


from .models import RentalBooking, RentalItem, Product, Customer, Alteration, AlterationType
from django.http import JsonResponse
import json

def get_item_by_code(request, code):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        item = Product.objects.get(code=code)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    return JsonResponse({
        "id": item.id,
        "code": item.code,
        "name": item.name,
        "category": item.category.name,
        "available_stock": item.available_stock,
        "is_available": item.is_available  #  useful
    })


@csrf_exempt
@transaction.atomic
def create_rental_order(request):
    if request.method != "POST":
        return JsonResponse(
            {"error": "POST method required"},
            status=405
        )

    try:
        data = json.loads(request.body)

        # Get or create customer
        customer, _ = Customer.objects.get_or_create(
            phone=data.get("phone"),
            defaults={
                "name": data.get("name"),
                "email": data.get("email")
            }
        )

        items_data = data.get("items", [])

        # Backward compatibility
        if not items_data:
            if data.get("item_id"):
                items_data = [{
                    "product_id": data.get("item_id"),
                    "unit_id": data.get("unit_id"),
                    "quantity": 1
                }]
            else:
                return JsonResponse(
                    {"error": "No items provided"},
                    status=400
                )

        # Validate products and quantities
        for item_data in items_data:
            try:
                product = Product.objects.get(
                    id=item_data.get("product_id")
                )
            except Product.DoesNotExist:
                return JsonResponse(
                    {"error": "Product not found"},
                    status=404
                )

            quantity = int(item_data.get("quantity", 1))

            if quantity < 1:
                return JsonResponse(
                    {"error": f"Invalid quantity for {product.name}"},
                    status=400
                )

            # If a specific unit is provided,
            # this is a single-unit booking.
            if item_data.get("unit_id"):
                quantity = 1

            # Check available stock before creating booking
            else:
                available_count = PhysicalUnit.objects.filter(
                    product=product,
                    status="available"
                ).count()

                if available_count < quantity:
                    return JsonResponse(
                        {
                            "error": (
                                f"Only {available_count} unit(s) "
                                f"available for {product.name}. "
                                f"You requested {quantity}."
                            )
                        },
                        status=400
                    )

        # Rental dates
        r_date = data.get("rental_date")
        ret_date = data.get("return_date")

        if isinstance(r_date, str):
            r_date = datetime.strptime(
                r_date,
                "%Y-%m-%d"
            ).date()

        if isinstance(ret_date, str):
            ret_date = datetime.strptime(
                ret_date,
                "%Y-%m-%d"
            ).date()

        # Coupon Logic
        coupon_id = data.get("coupon_id")
        coupon = None
        discount_amount = Decimal("0")

        if coupon_id:
            try:
                coupon = Coupon.objects.get(id=coupon_id)

                is_valid, msg = coupon.is_valid(
                    data.get("rental_amount")
                )

                if is_valid:
                    discount_amount = coupon.calculate_discount(
                        data.get("rental_amount")
                    )

                    coupon.used_count += 1
                    coupon.save()

            except Coupon.DoesNotExist:
                pass

        # Decide status based on rental date
        today = date.today()

        if r_date > today:
            status = "PRE_BOOKED"
            booking_type = "PRE_BOOKING"
        else:
            booking_type = data.get(
                "booking_type",
                "IMMEDIATE"
            )

            status = (
                "PRE_BOOKED"
                if booking_type == "PRE_BOOKING"
                else "ACTIVE"
            )

        # Create booking
        booking = RentalBooking.objects.create(
            customer=customer,
            rental_date=r_date,
            return_date=ret_date,
            booking_type=booking_type,
            status=status,
            rental_amount=Decimal(
                str(data.get("rental_amount", 0))
            ),
            discount_amount=discount_amount,
            coupon=coupon,
            security_deposit=Decimal(
                str(data.get("security_deposit", 0))
            ),
            collected_at=(
                timezone.now()
                if status == "ACTIVE"
                else None
            )
        )

        # Handle payments
        payments_data = data.get("payments", [])

        if not payments_data:
            sale_amount = Decimal(
                str(data.get("rental_amount", 0))
            )

            if sale_amount > 0:
                payments_data = [{
                    "amount": sale_amount,
                    "method": data.get(
                        "payment_method",
                        "CASH"
                    ),
                    "reference": data.get(
                        "payment_reference",
                        ""
                    )
                }]

        for p in payments_data:
            amt = Decimal(str(p.get("amount", 0)))

            if amt > 0:
                Payment.objects.create(
                    amount=amt,
                    payment_method=p.get(
                        "method",
                        "CASH"
                    ),
                    payment_type="INCOME",
                    transaction_reference=p.get(
                        "reference",
                        ""
                    ),
                    rental_booking=booking
                )

        # Security deposit
        if booking.security_deposit > 0:
            Payment.objects.create(
                amount=booking.security_deposit,
                payment_method=(
                    payments_data[0].get(
                        "method",
                        "CASH"
                    )
                    if payments_data
                    else "CASH"
                ),
                payment_type="INCOME",
                expense_category="deposit",
                notes=(
                    f"Security deposit collected "
                    f"for Booking #{booking.id}"
                ),
                rental_booking=booking
            )

        # Create rental items based on quantity
        for item_data in items_data:

            product = Product.objects.get(
                id=item_data.get("product_id")
            )

            unit_id = item_data.get("unit_id")
            quantity = int(
                item_data.get("quantity", 1)
            )

            # Specific physical unit
            if unit_id:
                unit = (
                    PhysicalUnit.objects
                    .select_for_update()
                    .get(id=unit_id)
                )

                units = [unit]

            # Product + quantity
            else:
                units = list(
                    PhysicalUnit.objects
                    .select_for_update()
                    .filter(
                        product=product,
                        status="available"
                    )[:quantity]
                )

                if len(units) < quantity:
                    raise Exception(
                        f"Only {len(units)} unit(s) available "
                        f"for {product.name}. "
                        f"You requested {quantity}."
                    )

            for unit in units:

                # Check overlapping bookings
                overlapping_bookings = (
                    RentalBooking.objects.filter(
                        items__unit=unit,
                        status__in=[
                            "PRE_BOOKED",
                            "READY_FOR_PICKUP",
                            "ACTIVE"
                        ],
                        rental_date__lte=ret_date,
                        return_date__gte=r_date
                    )
                )

                if overlapping_bookings.exists():
                    raise Exception(
                        f"Unit {unit.unit_id} for "
                        f"{product.name} is not available "
                        f"for the selected dates."
                    )

                # Immediate booking must have available unit
                if (
                    booking_type == "IMMEDIATE"
                    and unit.status != "available"
                ):
                    raise Exception(
                        f"Selected unit for {product.name} "
                        f"is currently not available "
                        f"for immediate pickup."
                    )

                # One RentalItem = one physical unit
                RentalItem.objects.create(
                    booking=booking,
                    product=product,
                    unit=unit
                )

                # Mark unit as rented
                if status == "ACTIVE":
                    unit.status = "rented"
                    unit.save()

        # Alterations
        alterations_data = data.get(
            "alterations",
            []
        )

        for alt_data in alterations_data:

            product = Product.objects.get(
                id=alt_data["product_id"]
            )

            exp_date_str = alt_data.get(
                "expected_completion_date"
            )

            exp_date = (
                datetime.strptime(
                    exp_date_str,
                    "%Y-%m-%d"
                ).date()
                if exp_date_str
                else None
            )

            alt_type = None

            if alt_data.get("alteration_type_id"):
                alt_type = AlterationType.objects.get(
                    id=alt_data["alteration_type_id"]
                )

            Alteration.objects.create(
                booking=booking,
                product=product,
                alteration_type=alt_type,
                alteration_area=alt_data.get(
                    "alteration_area"
                ),
                restore_after_return=alt_data.get(
                    "restore_after_return",
                    False
                ),
                notes=alt_data.get(
                    "notes",
                    ""
                ),
                expected_completion_date=exp_date,
                status="PENDING"
            )

        return JsonResponse({
            "message": "Order created",
            "order_id": booking.id
        })

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=400
        )


def get_all_rental_orders(request):
    if request.method == "GET":
        today = date.today()
        orders = RentalBooking.objects.select_related('customer').prefetch_related('items__product', 'items__product__category', 'items__unit', 'payments').all().order_by('-rental_date')

        data = []
        for o in orders:
            items = []
            for i in o.items.all():
                items.append({
                    "product_id": i.product.id,
                    "product_name": i.product.name,
                    "product_code": i.product.code,
                    "unit_id": i.unit.unit_id if i.unit else None,
                    "unit_status": i.unit.status if i.unit else None,
                })
            
            # Use first item for top-level display if needed (backward compatibility)
            first_item = items[0] if items else {}
            
            data.append({
                "id": o.id,
                "order_code": f"RNT-{o.id:04d}",
                "customer_name": o.customer.name,
                "customer_phone": o.customer.phone,
                "items": items,
                "item_name": first_item.get("product_name"),
                "item_code": first_item.get("product_code"),
                "unit_id": first_item.get("unit_id"),
                "unit_status": first_item.get("unit_status"),
                "rental_date": o.rental_date,
                "return_date": o.return_date,
                "rental_amount": float(o.rental_amount),
                "discount_amount": float(o.discount_amount),
                "coupon_code": o.coupon.code if o.coupon else None,
                "advance_paid": float(o.advance_paid),
                "due_amount": float(o.due_amount),
                "security_deposit": float(o.security_deposit),
                "deposit_status": o.deposit_status,
                "refunded_amount": float(o.refunded_amount),
                "deducted_amount": float(o.deducted_amount),
                "damage_notes": o.damage_notes,
                "is_returned": o.is_returned,
                "collected_at": o.collected_at.isoformat() if o.collected_at else None,
                "returned_at": o.returned_at.isoformat() if o.returned_at else None,
                "booking_type": o.booking_type,
                "booking_date": o.booking_date.isoformat() if o.booking_date else None,
                "status": "OVERDUE" if o.status == 'ACTIVE' and not o.is_returned and o.return_date < today else o.status,
                "alterations_count": o.alterations.count(),
                "payments": [{"id": p.id, "amount": float(p.amount), "method": p.payment_method, "reference": p.transaction_reference, "date": p.created_at.isoformat()} for p in o.payments.all()]
            })

        return JsonResponse(data, safe=False)

    
@csrf_exempt
@transaction.atomic
def return_rental_order(request, order_id):
    if request.method == "POST":
        data = json.loads(request.body) if request.body else {}
        try:
            order = RentalBooking.objects.select_for_update().get(id=order_id)
        except RentalBooking.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        #  Prevent double return
        if order.is_returned:
            return JsonResponse({"error": "Item already returned"}, status=400)

        # Handle additional payment for due amount
        collected_amount = data.get("collected_amount", 0)
        if collected_amount:
            Payment.objects.create(
                amount=Decimal(str(collected_amount)),
                payment_method=data.get("payment_method", "CASH"),
                payment_type="INCOME",
                notes="Collected upon return",
                rental_booking=order
            )

        # Handle Security Deposit Refund/Deduction
        deducted = Decimal(str(data.get("deducted_amount", 0)))
        refunded = Decimal(str(data.get("refunded_amount", 0)))
        notes = data.get("damage_notes", "")

        order.deducted_amount = deducted
        order.refunded_amount = refunded
        order.damage_notes = notes

        if deducted > 0:
            order.deposit_status = 'deducted' if refunded == 0 else 'partially_refunded'
            # Record deduction as income
            Payment.objects.create(
                amount=deducted,
                payment_method='CASH',
                payment_type='INCOME',
                expense_category='rental',
                notes=f"Damage deduction for Rental #{order.id}. Notes: {notes}",
                rental_booking=order,
            )
        elif order.security_deposit > 0:
            order.deposit_status = 'refunded'

        if refunded > 0:
            Payment.objects.create(
                amount=refunded,
                payment_method=data.get("refund_method", "CASH"),
                payment_type="REFUND",
                expense_category="deposit",
                notes=f"Security deposit refunded. Ref: {data.get('refund_reference', '')}",
                rental_booking=order
            )

        # Core logic
        order.mark_as_returned()

        return JsonResponse({
            "message": "Item returned successfully",
            "available_stock": order.items.first().product.available_stock if order.items.first() else 0,
            "due_amount": float(order.due_amount),
            "refunded_amount": float(order.refunded_amount)
        })
    
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def check_item_availability(request):
    if request.method == "POST":
        data = json.loads(request.body)

        item_id = data.get("item_id")
        rental_date = data.get("rental_date")
        return_date = data.get("return_date")

        #  Convert string to date
        rental_date = datetime.strptime(rental_date, "%Y-%m-%d").date()
        return_date = datetime.strptime(return_date, "%Y-%m-%d").date()

        try:
            item = Product.objects.get(id=item_id)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Item not found"}, status=404)

        # If item not ready
        if not item.is_available:
            return JsonResponse({
                "available": False,
                "message": "Item is not ready (washing/repair)"
            })

        #  Find overlapping bookings
        overlapping_orders = RentalBooking.objects.filter(items__product=item, is_returned=False, rental_date__lte=return_date, return_date__gte=rental_date)

        booked_count = overlapping_orders.count()
        available_quantity = item.total_stock - booked_count

        return JsonResponse({
            "item_id": item.id,
            "total_stock": item.total_stock,
            "booked": booked_count,
            "available_quantity": max(0, available_quantity),
            "can_book": available_quantity > 0
        })
    
def get_item_history(request, item_id):
    try:
        item = Product.objects.get(id=item_id)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Item not found"}, status=404)

    # 🔥 Get all orders for this item
    orders = RentalBooking.objects.filter(items__product=item).select_related('customer').order_by('-rental_date')

    history = []
    for order in orders:
        history.append({
            "order_id": order.id,
            "customer_name": order.customer.name,
            "phone": order.customer.phone,
            "rental_date": order.rental_date,
            "return_date": order.return_date,
            "is_returned": order.is_returned,
            "rental_amount": float(order.rental_amount),
            "advance_paid": float(order.advance_paid),
            "due_amount": float(order.due_amount)
        })

    data = {
        "item_id": item.id,
        "name": item.name,
        "total_stock": item.total_stock,
        "available_stock": item.available_stock,
        "condition": "ready" if item.is_available else "out_of_stock",
        "total_rented_times": item.total_rented_times,
        "history": history
    }

    return JsonResponse(data)



from django.core.mail import send_mail
from django.conf import settings
from django.utils.timezone import now
from datetime import timedelta
from django.http import JsonResponse


def check_and_send_reminders(request):
    today = now().date()
    tomorrow = today + timedelta(days=1)

    # Get relevant orders (due soon OR overdue)
    orders = RentalBooking.objects.filter(
        is_returned=False,
        return_date__lte=tomorrow
    ).select_related('customer').prefetch_related('items__product')

    reminder_list = []

    for order in orders:

        #  Skip if no email
        if not order.customer.email:
            continue

        # 🔥 Decide message type
        if order.return_date < today:
            #  OVERDUE MESSAGE
            subject = "Overdue Reminder"
            message = f"""
Hi {order.customer.name},

The item "{order.items.first().product.name if order.items.first() else ""}" was due on {order.return_date}.

It is now overdue by {(today - order.return_date).days} day(s).

Please return it as soon as possible.

Thank you!
"""
        else:
            #  NORMAL REMINDER
            subject = "Return Reminder"
            message = f"""
Hi {order.customer.name},

This is a reminder to return the item:
"{order.items.first().product.name if order.items.first() else ""}"

Return Date: {order.return_date}

Thank you!
"""

        # SEND EMAIL
        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [order.customer.email],
            fail_silently=False,
        )

        # Track sent reminder
        reminder_list.append({
            "order_id": order.id,
            "customer": order.customer.name,
            "email": order.customer.email,
            "type": "overdue" if order.return_date < today else "normal"
        })

        # Mark as sent (Temporarily commented out as field doesn't exist)
        # order.reminder_sent = True
        # order.save()

    return JsonResponse({
        "total_reminders_sent": len(reminder_list),
        "details": reminder_list
    })




from django.utils.timezone import now

@csrf_exempt
def get_overdue_items(request):
    today = now().date()
    tomorrow = today + timedelta(days=1)

    # Get overdue AND upcoming orders
    orders = RentalBooking.objects.filter(
        is_returned=False,
        return_date__lte=tomorrow
    ).select_related('customer').prefetch_related('items__product').order_by('return_date')

    data = []

    for order in orders:
        is_overdue = order.return_date < today
        overdue_days = (today - order.return_date).days if is_overdue else 0

        data.append({
            "order_id": order.id,
            "customer_name": order.customer.name,
            "phone": order.customer.phone,
            "email": order.customer.email,
            "item_name": order.items.first().product.name if order.items.first() else "",
            "return_date": order.return_date,
            "is_overdue": is_overdue,
            "overdue_days": overdue_days,
            "status": "Overdue" if is_overdue else "Upcoming"
        })

    return JsonResponse({
        "total_overdue": len([d for d in data if d['is_overdue']]),
        "total_upcoming": len([d for d in data if not d['is_overdue']]),
        "overdue_items": data
    })


import json
@csrf_exempt
def create_category(request):
    if request.method == "POST":
        data = json.loads(request.body)

        category = Category.objects.create(
            name=data.get("name"),
            prefix=data.get("prefix")
        )

        return JsonResponse({
            "message": "Category created",
            "id": category.id
        })

    return JsonResponse({"error": "Invalid request method"}, status=405)

from .models import Category
from django.http import JsonResponse

@csrf_exempt
def get_all_categories(request):
    if request.method == "GET":
        categories = Category.objects.all()

        data = []
        for category in categories:
            data.append({
                "id": category.id,
                "name": category.name,
                "prefix": category.prefix
            })

        return JsonResponse(data, safe=False)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def delete_category(request, category_id):
    if request.method == "DELETE":
        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({"error": "Category not found"}, status=404)

        category.delete()
        return JsonResponse({"message": "Category deleted"})

    return JsonResponse({"error": "Invalid request method"}, status=405)
@csrf_exempt
def update_category(request, category_id):
    if request.method == "PUT":
        import json
        data = json.loads(request.body)

        try:
            category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            return JsonResponse({"error": "Category not found"}, status=404)

        # Update fields
        category.name = data.get("name", category.name)

        # Important: handle prefix carefully
        if "prefix" in data:
            category.prefix = data.get("prefix").upper()

        category.save()

        return JsonResponse({
            "message": "Category updated successfully",
            "id": category.id,
            "name": category.name,
            "prefix": category.prefix
        })

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
def create_material(request):
    if request.method == "POST":
        data = json.loads(request.body)

        material = Material.objects.create(
            name=data.get("name"),
            description=data.get("description"),
            price_per_meter=data.get("price_per_meter"),
            colour=data.get("colour"),
            total_stock=data.get("total_stock", 0),
            available_stock=data.get("available_stock", 0)
        )

        return JsonResponse({
            "message": "Material created",
            "id": material.id,
            "code": material.code 
        })


def get_all_materials(request):
    if request.method == "GET":
        materials = Material.objects.all()

        data = []
        for m in materials:
            data.append({
                "id": m.id,
                "name": m.name,
                "code": m.code,
                "colour": m.colour,
                "price_per_meter": float(m.price_per_meter),
                "total_stock": float(m.total_stock),
                "available_stock": float(m.available_stock),
                "image_url": m.image.url if m.image else None
            })

        return JsonResponse(data, safe=False)

def get_material(request, material_id):
    try:
        m = Material.objects.get(id=material_id)
    except Material.DoesNotExist:
        return JsonResponse({"error": "Material not found"}, status=404)

    return JsonResponse({
        "id": m.id,
        "name": m.name,
        "code": m.code,
        "description": m.description,
        "price_per_meter": float(m.price_per_meter),
        "colour": m.colour,
        "total_stock": float(m.total_stock),
        "available_stock": float(m.available_stock),
        "image_url": m.image.url if m.image else None
    })

@csrf_exempt
def update_material(request, material_id):
    if request.method == "PUT":
        data = json.loads(request.body)

        try:
            m = Material.objects.get(id=material_id)
        except Material.DoesNotExist:
            return JsonResponse({"error": "Material not found"}, status=404)

        m.name = data.get("name", m.name)
        m.description = data.get("description", m.description)
        m.price_per_meter = data.get("price_per_meter", m.price_per_meter)
        m.colour = data.get("colour", m.colour)
        m.total_stock = data.get("total_stock", m.total_stock)
        m.available_stock = data.get("available_stock", m.available_stock)

        m.save()

        return JsonResponse({"message": "Material updated"})

@csrf_exempt
def delete_material(request, material_id):
    if request.method == "DELETE":
        try:
            m = Material.objects.get(id=material_id)
        except Material.DoesNotExist:
            return JsonResponse({"error": "Material not found"}, status=404)

        m.delete()
        return JsonResponse({"message": "Material deleted"})

@csrf_exempt
def create_material_purchase(request):
    if request.method == "POST":
        data = json.loads(request.body)

        try:
            material = Material.objects.get(id=data.get("material_id"))
        except Material.DoesNotExist:
            return JsonResponse({"error": "Material not found"}, status=404)

        purchase = MaterialPurchase.objects.create(
            material=material,
            quantity=data.get("quantity"),
            cost_per_unit=data.get("cost_per_unit")
        )
        
        Payment.objects.create(
            amount=purchase.total_cost,
            payment_method='CASH',
            payment_type='EXPENSE',
            expense_category='purchase',
            notes=f"Material purchase: {material.name} x {purchase.quantity}"
        )

        return JsonResponse({
            "message": "Purchase recorded",
            "purchase_id": purchase.id,
            "new_available_stock": float(material.available_stock)
        })

def get_all_purchases(request):
    if request.method == "GET":
        purchases = MaterialPurchase.objects.select_related('material').all()

        data = []
        for p in purchases:
            data.append({
                "id": p.id,
                "material": p.material.name,
                "quantity": float(p.quantity),
                "cost_per_unit": float(p.cost_per_unit),
                "total_cost": float(p.total_cost),
                "purchase_date": p.purchase_date
            })

        return JsonResponse(data, safe=False)

def get_purchase(request, purchase_id):
    try:
        p = MaterialPurchase.objects.get(id=purchase_id)
    except MaterialPurchase.DoesNotExist:
        return JsonResponse({"error": "Purchase not found"}, status=404)

    return JsonResponse({
        "id": p.id,
        "material": p.material.name,
        "quantity": float(p.quantity),
        "cost_per_unit": float(p.cost_per_unit),
        "total_cost": float(p.total_cost),
        "purchase_date": p.purchase_date
    })


@csrf_exempt
def create_stitching_order(request):
    if request.method == "POST":
        data = json.loads(request.body)

        # 🔹 Get or create customer
        customer, _ = Customer.objects.get_or_create(
            phone=data.get("phone"),
            defaults={
                "name": data.get("name"),
                "email": data.get("email")
            }
        )

        # 🔹 Handle material (optional)
        material = None
        if data.get("material_id"):
            try:
                material = Material.objects.get(id=data.get("material_id"))
            except Material.DoesNotExist:
                return JsonResponse({"error": "Material not found"}, status=404)

            # Check stock
            if material.available_stock < float(data.get("material_used", 0)):
                return JsonResponse({"error": "Not enough material"}, status=400)

        # 🔹 Coupon Logic
        coupon_id = data.get("coupon_id")
        coupon = None
        discount_amount = Decimal("0")
        if coupon_id:
            try:
                coupon = Coupon.objects.get(id=coupon_id)
                is_valid, msg = coupon.is_valid(data.get("total_amount"))
                if is_valid:
                    discount_amount = coupon.calculate_discount(data.get("total_amount"))
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass

        # 🔹 Create order
        order = StitchingOrder.objects.create(
            customer=customer,
            material=material,
            outfit_type=data.get("outfit_type"),
            material_used=data.get("material_used", 0),
            measurements_taken=data.get("measurements_taken", False),
            order_date=data.get("order_date"),
            delivery_date=data.get("delivery_date"),
            total_amount=Decimal(str(data.get("total_amount", 0))),
            discount_amount=discount_amount,
                coupon=coupon,
        )
        


        
        # Handle payments array
        payments_data = data.get('payments', [])
        if not payments_data and data.get("advance_payment"):
            payments_data = [{
                "amount": float(data.get("advance_payment")),
                "method": data.get("payment_method", "CASH"),
                "reference": data.get("payment_reference", "")
            }]
        for p in payments_data:
            amt = float(p.get('amount', 0))
            if amt > 0:
                Payment.objects.create(
                    amount=amt,
                    payment_method=p.get('method', 'CASH'),
                    payment_type='INCOME',
                    transaction_reference=p.get('reference', ''),
                    stitching_order=order
                )

        #Reduce stock
        if material:
            material.available_stock -= Decimal(data.get("material_used", 0))
            material.save()

        return JsonResponse({
            "message": "Stitching order created",
            "order_id": order.id
        })
    
def get_all_stitching_orders(request):
    if request.method == "GET":
        orders = StitchingOrder.objects.select_related('customer', 'material').all()

        data = []
        for o in orders:
            data.append({
                "id": o.id,
                "customer": o.customer.name,
                "phone": o.customer.phone,
                "material": o.material.name if o.material else None,
                "outfit_type": o.outfit_type,
                "material_used": float(o.material_used),
                "status": o.status,
            "payments": [{"id": p.id, "amount": float(p.amount), "method": p.payment_method, "reference": p.transaction_reference, "date": p.created_at.isoformat()} for p in o.payments.all()],
                "delivery_date": o.delivery_date,
                "total_amount": float(o.total_amount),
                "discount_amount": float(o.discount_amount),
                "coupon_code": o.coupon.code if o.coupon else None,
                "due_amount": float(o.due_amount)
            })

        return JsonResponse(data, safe=False)
    
def get_stitching_order(request, order_id):
    try:
        o = StitchingOrder.objects.get(id=order_id)
    except StitchingOrder.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

    return JsonResponse({
        "id": o.id,
        "customer": o.customer.name,
        "phone": o.customer.phone,
        "material": o.material.name if o.material else None,
        "outfit_type": o.outfit_type,
        "material_used": float(o.material_used),
        "status": o.status,
            "payments": [{"id": p.id, "amount": float(p.amount), "method": p.payment_method, "reference": p.transaction_reference, "date": p.created_at.isoformat()} for p in o.payments.all()],
        "order_date": o.order_date,
        "delivery_date": o.delivery_date,
        "total_amount": float(o.total_amount),
        "discount_amount": float(o.discount_amount),
        "coupon_code": o.coupon.code if o.coupon else None,
        "advance_payment": float(sum(p.amount for p in o.payments.all() if p.payment_type == "INCOME") - sum(p.amount for p in o.payments.all() if p.payment_type == "REFUND")),
        "due_amount": float(o.due_amount)
    })

@csrf_exempt
def update_stitching_status(request, order_id):
    if request.method == "PUT":
        data = json.loads(request.body)

        try:
            order = StitchingOrder.objects.get(id=order_id)
        except StitchingOrder.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        order.status = data.get("status", order.status)
        order.save()

        return JsonResponse({
            "message": "Status updated",
            "status": order.status
        })

@csrf_exempt
def delete_stitching_order(request, order_id):
    if request.method == "DELETE":
        try:
            order = StitchingOrder.objects.get(id=order_id)
        except StitchingOrder.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        order.delete()
        return JsonResponse({"message": "Order deleted"})

@csrf_exempt
def collect_stitching_payment(request, order_id):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            order = StitchingOrder.objects.get(id=order_id)
        except StitchingOrder.DoesNotExist:
            return JsonResponse({"error": "Order not found"}, status=404)

        amount = data.get("amount", 0)
        if amount:
            Payment.objects.create(
                amount=Decimal(str(amount)),
                payment_method=data.get("payment_method", "CASH"),
                payment_type="INCOME",
                notes="Additional payment for stitching order",
                stitching_order=order
            )

        return JsonResponse({
            "message": "Payment recorded successfully",
            "due_amount": float(order.due_amount),
            "advance_payment": float(order.advance_payment)
        })
    
def get_material_by_code(request, code):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid method"}, status=405)

    try:
        material = Material.objects.get(code=code)
    except Material.DoesNotExist:
        return JsonResponse({"error": "Material not found"}, status=404)

    return JsonResponse({
        "id": material.id,
        "code": material.code,
        "name": material.name,
        "colour": material.colour,
        "price_per_meter": float(material.price_per_meter),
        "available_stock": float(material.available_stock),
        "total_stock": float(material.total_stock)
    })

# --- ACCESSORIES ---

@csrf_exempt
def create_accessory(request):
    if request.method == "POST":
        if request.content_type == "application/json":
            data = json.loads(request.body)
            image = None
        else:
            data = request.POST
            image = request.FILES.get("image")

        accessory = Accessory.objects.create(
            name=data.get("name"),
            expense_category=data.get("category"),
            description=data.get("description"),
            price=Decimal(str(data.get("price", 0))),
            stock=int(data.get("stock", 0)),
            image=image
        )
        return JsonResponse({
            "message": "Accessory created",
            "id": accessory.id,
            "code": accessory.code,
            "image_url": accessory.image.url if accessory.image else None
        })

def get_all_accessories(request):
    if request.method == "GET":
        accessories = Accessory.objects.all().order_by('-id')
        data = []
        for acc in accessories:
            data.append({
                "id": acc.id,
                "code": acc.code,
                "name": acc.name,
                "category": acc.category,
                "description": acc.description,
                "price": float(acc.price),
                "stock": acc.stock,
                "image_url": acc.image.url if acc.image else None
            })
        return JsonResponse(data, safe=False)

@csrf_exempt
def update_accessory(request, accessory_id):
    if request.method in ["POST", "PUT"]:
        if request.content_type == "application/json":
            data = json.loads(request.body)
            image = None
        else:
            data = request.POST
            image = request.FILES.get("image")

        try:
            acc = Accessory.objects.get(id=accessory_id)
        except Accessory.DoesNotExist:
            return JsonResponse({"error": "Accessory not found"}, status=404)
        
        acc.name = data.get("name", acc.name)
        acc.category = data.get("category", acc.category)
        acc.description = data.get("description", acc.description)
        if "price" in data:
            acc.price = Decimal(str(data.get("price")))
        if "stock" in data:
            acc.stock = int(data.get("stock"))
        if image:
            acc.image = image
            
        acc.save()
        return JsonResponse({
            "message": "Accessory updated",
            "image_url": acc.image.url if acc.image else None
        })

@csrf_exempt
def delete_accessory(request, accessory_id):
    if request.method == "DELETE":
        try:
            acc = Accessory.objects.get(id=accessory_id)
        except Accessory.DoesNotExist:
            return JsonResponse({"error": "Accessory not found"}, status=404)
        acc.delete()
        return JsonResponse({"message": "Accessory deleted"})

@csrf_exempt
def create_accessory_sale(request):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            accessory = Accessory.objects.get(id=data.get("accessory_id"))
        except Accessory.DoesNotExist:
            return JsonResponse({"error": "Accessory not found"}, status=404)
        
        # 🔹 Coupon Logic
        coupon_id = data.get("coupon_id")
        coupon = None
        discount_amount = Decimal(str(data.get("discount", 0))) # Manual discount if any
        
        if coupon_id:
            try:
                coupon = Coupon.objects.get(id=coupon_id)
                # Subtotal for accessories is quantity * price
                subtotal = int(data.get("quantity", 1)) * accessory.price
                is_valid, msg = coupon.is_valid(subtotal)
                if is_valid:
                    discount_amount += coupon.calculate_discount(subtotal)
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass

        try:
            qty = int(data.get("quantity", 1))
            total_price = (qty * accessory.price) - discount_amount
            sale = AccessorySale.objects.create(
                accessory=accessory,
                customer_name=data.get("customer_name"),
                customer_phone=data.get("customer_phone"),
                customer_email=data.get("customer_email"),
                customer_address=data.get("customer_address"),
                quantity=qty,
                discount_amount=discount_amount,
                coupon=coupon,
                total_price=total_price
            )
            # Handle payments array
            payments_data = data.get('payments', [])
            for p in payments_data:
                amt = float(p.get('amount', 0))
                if amt > 0:
                    Payment.objects.create(
                        amount=amt,
                        payment_method=p.get('method', 'CASH'),
                        payment_type='INCOME',
                        transaction_reference=p.get('reference', ''),
                        accessory_sale=sale
                    )
            
            # If no payments array passed, assume full cash payment (backward compatibility)
            if not payments_data and sale.total_price > 0:
                Payment.objects.create(
                    amount=sale.total_price,
                    payment_method='CASH',
                    payment_type='INCOME',
                    notes='Full payment',
                    accessory_sale=sale
                )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
        return JsonResponse({
            "message": "Sale recorded",
            "sale_id": sale.id,
            "new_stock": accessory.stock
        })

@csrf_exempt
def update_accessory_sale(request, sale_id):
    if request.method == "PUT":
        data = json.loads(request.body)
        try:
            sale = AccessorySale.objects.get(id=sale_id)
        except AccessorySale.DoesNotExist:
            return JsonResponse({"error": "Sale record not found"}, status=404)
            
        sale.customer_name = data.get("customer_name", sale.customer_name)
        sale.customer_phone = data.get("customer_phone", sale.customer_phone)
        sale.customer_email = data.get("customer_email", sale.customer_email)
        sale.customer_address = data.get("customer_address", sale.customer_address)
        
        if "quantity" in data:
            sale.quantity = int(data.get("quantity"))
        if "discount" in data:
            sale.discount = Decimal(str(data.get("discount")))
        if "total_price" in data:
            sale.total_price = Decimal(str(data.get("total_price")))
            
        try:
            sale.save()
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
        return JsonResponse({"message": "Sale updated successfully"})

@csrf_exempt
def delete_accessory_sale(request, sale_id):
    if request.method == "DELETE":
        try:
            sale = AccessorySale.objects.get(id=sale_id)
            sale.delete()
            return JsonResponse({"message": "Sale record deleted and stock restored"})
        except AccessorySale.DoesNotExist:
            return JsonResponse({"error": "Sale record not found"}, status=404)

def get_all_accessory_sales(request):
    if request.method == "GET":
        sales = AccessorySale.objects.select_related('accessory').all().order_by('-id')
        data = []
        for s in sales:
            data.append({
                "id": s.id,
                "accessory_id": s.accessory.id,
                "accessory_name": s.accessory.name,
                "customer_name": s.customer_name,
                "customer_phone": s.customer_phone,
                "customer_email": s.customer_email,
                "customer_address": s.customer_address,
                "quantity": s.quantity,
                "discount_amount": float(s.discount_amount),
                "total_price": float(s.total_price),
            "payments": [{"id": p.id, "amount": float(p.amount), "method": p.payment_method, "reference": p.transaction_reference, "date": p.created_at.isoformat()} for p in s.payments.all()],
                "date": s.sale_date
            })
        return JsonResponse(data, safe=False)


@csrf_exempt
def get_item_units(request, item_id):
    if request.method == 'GET':
        units = PhysicalUnit.objects.filter(product_id=item_id)
        data = []
        for u in units:
            data.append({
                'id': u.id,
                'unit_id': u.unit_id,
                'size': u.size,
                'status': u.status,
                'notes': u.notes
            })
        return JsonResponse(data, safe=False)

@csrf_exempt
def update_unit_status(request, unit_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            unit = PhysicalUnit.objects.get(id=unit_id)
            unit.status = data.get('status', unit.status)
            unit.size = data.get('size', unit.size)
            unit.notes = data.get('notes', unit.notes)
            unit.save()
            return JsonResponse({'message': 'Status updated'})
        except PhysicalUnit.DoesNotExist:
            return JsonResponse({'error': 'Unit not found'}, status=404)


@csrf_exempt
def get_dashboard_stats(request):
    if request.method == 'GET':
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        # Action Required (Returns due today or tomorrow)
        action_required_rentals = RentalBooking.objects.filter(
            is_returned=False, 
            return_date__lte=tomorrow
        ).select_related('customer').prefetch_related('items__product').order_by('return_date')

        action_data = []
        for r in action_required_rentals:
            item_names = ", ".join([i.product.name for i in r.items.all()])
            action_data.append({
                "id": r.id,
                "customer": r.customer.name,
                "phone": r.customer.phone,
                "item": item_names,
                "due_date": r.return_date,
                "is_overdue": r.return_date < today
            })

        # Upcoming Deliveries (Stitching)
        upcoming_deliveries = StitchingOrder.objects.filter(
            delivery_date__gte=today
        ).exclude(status='delivered').select_related('customer').order_by('delivery_date')[:5]

        deliveries_data = []
        for d in upcoming_deliveries:
            deliveries_data.append({
                "id": d.id,
                "customer": d.customer.name,
                "phone": d.customer.phone,
                "outfit_type": d.outfit_type,
                "delivery_date": d.delivery_date,
                "status": d.status
            })

        # Upcoming Rentals (Pre-Bookings)
        upcoming_rentals = RentalBooking.objects.filter(
            status='PRE_BOOKED',
            rental_date__gte=today
        ).select_related('customer').prefetch_related('items__product').order_by('rental_date')[:5]

        upcoming_rentals_data = []
        for r in upcoming_rentals:
            item_names = ", ".join([i.product.name for i in r.items.all()])
            upcoming_rentals_data.append({
                "id": r.id,
                "customer": r.customer.name,
                "phone": r.customer.phone,
                "item": item_names,
                "rental_date": r.rental_date,
                "status": r.status
            })

        # Revenue History (Last 7 days)
        revenue_history = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            # Simplified revenue: Sum of payments made on that day
            # Since we don't have a dedicated payment table, we check 'order_date' or 'sale_date'
            # Note: This is an approximation based on creation date.
            r_rev = sum(o.advance_paid for o in RentalBooking.objects.filter(rental_date=day))
            a_rev = sum(s.total_price for s in AccessorySale.objects.filter(sale_date=day))
            s_rev = sum(o.advance_payment for o in StitchingOrder.objects.filter(order_date=day))
            
            revenue_history.append({
                "date": day.strftime("%d %b"),
                "amount": float(r_rev + a_rev + s_rev)
            })

        # Basic Stats
        total_rental_items = Product.objects.count()
        active_rentals = RentalBooking.objects.filter(is_returned=False).count()
        overdue_rentals = RentalBooking.objects.filter(is_returned=False, return_date__lt=today).count()
        
        rental_revenue = sum(o.advance_paid for o in RentalBooking.objects.all())
        accessory_revenue = sum(s.total_price for s in AccessorySale.objects.all())
        stitching_revenue = sum(o.advance_payment for o in StitchingOrder.objects.all())
        
        total_revenue = float(rental_revenue + accessory_revenue + stitching_revenue)

        total_accessories = Accessory.objects.count()
        low_stock_accessories = Accessory.objects.filter(stock__lt=5).count()

        pending_stitching = StitchingOrder.objects.filter(status='pending').count()
        ready_stitching = StitchingOrder.objects.filter(status='ready').count()

        return JsonResponse({
            "rentals": {
                "total_items": total_rental_items,
                "active_orders": active_rentals,
                "overdue_orders": overdue_rentals,
                "revenue": float(rental_revenue)
            },
            "accessories": {
                "total_items": total_accessories,
                "low_stock_count": low_stock_accessories,
                "revenue": float(accessory_revenue)
            },
            "stitching": {
                "pending_count": pending_stitching,
                "ready_count": ready_stitching,
                "revenue": float(stitching_revenue)
            },
            "total_revenue": total_revenue,
            "action_required": action_data,
            "upcoming_deliveries": deliveries_data,
            "upcoming_rentals": upcoming_rentals_data,
            "revenue_history": revenue_history
        })

# -- Coupons ------------------------------------------------------------------
from .models import Coupon
from django.utils import timezone

@csrf_exempt
def get_all_coupons(request):
    if request.method == "GET":
        coupons = Coupon.objects.all().order_by("-created_at")
        data = []
        for c in coupons:
            data.append({
                "id": c.id,
                "code": c.code,
                "discount_type": c.discount_type,
                "discount_value": float(c.discount_value),
                "min_purchase_amount": float(c.min_purchase_amount),
                "valid_from": c.valid_from.isoformat(),
                "valid_to": c.valid_to.isoformat(),
                "usage_limit": c.usage_limit,
                "used_count": c.used_count,
                "active": c.active
            })
        return JsonResponse(data, safe=False)

@csrf_exempt
def create_coupon(request):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            coupon = Coupon.objects.create(
                code=data.get("code").upper(),
                discount_type=data.get("discount_type"),
                discount_value=data.get("discount_value"),
                min_purchase_amount=data.get("min_purchase_amount", 0),
                valid_from=data.get("valid_from", timezone.now()),
                valid_to=data.get("valid_to"),
                usage_limit=data.get("usage_limit") if data.get("usage_limit") else None,
                active=data.get("active", True)
            )
            return JsonResponse({"message": "Coupon created", "id": coupon.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def update_coupon(request, coupon_id):
    if request.method == "PUT":
        data = json.loads(request.body)
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            coupon.code = data.get("code", coupon.code).upper()
            coupon.discount_type = data.get("discount_type", coupon.discount_type)
            coupon.discount_value = data.get("discount_value", coupon.discount_value)
            coupon.min_purchase_amount = data.get("min_purchase_amount", coupon.min_purchase_amount)
            coupon.valid_from = data.get("valid_from", coupon.valid_from)
            coupon.valid_to = data.get("valid_to", coupon.valid_to)
            coupon.usage_limit = data.get("usage_limit") if data.get("usage_limit") else None
            coupon.active = data.get("active", coupon.active)
            coupon.save()
            return JsonResponse({"message": "Coupon updated"})
        except Coupon.DoesNotExist:
            return JsonResponse({"error": "Coupon not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def delete_coupon(request, coupon_id):
    if request.method == "DELETE":
        try:
            coupon = Coupon.objects.get(id=coupon_id)
            coupon.delete()
            return JsonResponse({"message": "Coupon deleted"})
        except Coupon.DoesNotExist:
            return JsonResponse({"error": "Coupon not found"}, status=404)

@csrf_exempt
def validate_coupon(request):
    if request.method == "POST":
        data = json.loads(request.body)
        code = data.get("code", "").upper()
        subtotal = data.get("subtotal", 0)
        
        try:
            coupon = Coupon.objects.get(code=code)
            is_valid, message = coupon.is_valid(subtotal)
            if not is_valid:
                return JsonResponse({"valid": False, "message": message})
            
            discount = coupon.calculate_discount(subtotal)
            return JsonResponse({
                "valid": True,
                "coupon_id": coupon.id,
                "discount_amount": float(discount),
                "new_total": float(Decimal(str(subtotal)) - discount)
            })
        except Coupon.DoesNotExist:
            return JsonResponse({"valid": False, "message": "Invalid coupon code"})


@csrf_exempt
def generate_invoice_pdf(request, order_type, order_id):
    try:
        # Fetch order based on type
        if order_type == 'stitching':
            order = StitchingOrder.objects.get(id=order_id)
            cust_name = order.customer.name
            order_code = f"ST-{order.id}"
            item_desc = order.outfit_type
            item_note = order.material.name if order.material else "Custom Stitch"
            category_display = "CUSTOM APPAREL"
            subtotal = order.total_amount
            discount = order.discount_amount
            paid = order.advance_payment
            date_val = order.order_date
            due_date = order.delivery_date
            phone = order.customer.phone
            security_dep = 0
        elif order_type == 'rental':
            order = RentalBooking.objects.get(id=order_id)
            cust_name = order.customer.name
            order_code = f"ORD-{order.id:04d}" if hasattr(order, 'id') else f"ORD-{order.id}"
            first_item = order.items.first()
            item_desc = first_item.product.name if first_item else "Product Sale"
            item_count = order.items.count()
            if item_count > 1:
                item_note = f"Qty: {item_count}"
            elif first_item and first_item.product and first_item.product.code:
                item_note = f"Code: {first_item.product.code} | Qty: 1"
            else:
                item_note = "Qty: 1"
            category_display = "PRODUCT SALE"
            subtotal = order.rental_amount
            discount = order.discount_amount
            paid = order.advance_paid
            date_val = order.rental_date
            due_date = "N/A"
            phone = order.customer.phone
            security_dep = 0
        elif order_type == 'accessory':
            order = AccessorySale.objects.get(id=order_id)
            cust_name = order.customer_name or "Walk-in"
            order_code = f"AC-{order.id}"
            item_desc = order.accessory.name
            item_note = f"Quantity: {order.quantity}"
            category_display = "MERCHANDISE"
            subtotal = order.total_price
            discount = order.discount_amount
            paid = order.total_price # Accessory sales are usually full payment
            date_val = order.sale_date
            due_date = "N/A"
            phone = order.customer_phone or "N/A"
            security_dep = 0
        else:
            return JsonResponse({"error": "Invalid order type"}, status=400)

        # Filename: Invoice_OrderID_CustomerName.pdf
        clean_cust_name = cust_name.replace(' ', '_').replace('/', '_')
        filename = f"Invoice_{order_code}_{clean_cust_name}.pdf"
        
        # Create PDF buffer
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # --- Draw Header ---
        logo_path = os.path.join(settings.BASE_DIR, 'media', 'logo.png')
        if not os.path.exists(logo_path):
            logo_path = "D:/Tron-Projects/Perfect-Fit/frontend/public/logo.png"

        if os.path.exists(logo_path):
            try:
                p.drawImage(logo_path, 20*mm, height - 40*mm, width=30*mm, preserveAspectRatio=True, mask='auto')
            except:
                pass
        
        p.setFont("Helvetica-Bold", 26)
        p.setFillColor(colors.HexColor("#000000"))
        p.drawString(60*mm, height - 28*mm, "Reborn Fitness")
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor("#4b5563"))
        p.drawString(60*mm, height - 33*mm, "Gym Management & Inventory System")
        
        # Brand Accent Line
        p.setStrokeColor(colors.HexColor("#FED505"))
        p.setLineWidth(2.5)
        p.line(20*mm, height - 46*mm, width - 20*mm, height - 46*mm)

        # --- Draw Info Section ---
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(colors.HexColor("#6b7280"))
        p.drawString(20*mm, height - 58*mm, "BILL TO")
        
        p.setFont("Helvetica-Bold", 14)
        p.setFillColor(colors.HexColor("#000000"))
        p.drawString(20*mm, height - 65*mm, cust_name.upper())
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor("#6b7280"))
        p.drawString(20*mm, height - 71*mm, f"Contact: {phone}")

        # Invoice Details Box
        p.drawRightString(width - 20*mm, height - 58*mm, "INVOICE DETAILS")
        p.setFont("Helvetica-Bold", 11)
        p.setFillColor(colors.HexColor("#000000"))
        p.drawRightString(width - 20*mm, height - 65*mm, f"No: {order_code}")
        
        p.setFont("Helvetica", 10)
        p.setFillColor(colors.HexColor("#6b7280"))
        p.drawRightString(width - 20*mm, height - 71*mm, f"Date: {date_val}")
        if order_type != 'rental' and due_date and due_date != 'N/A':
            p.drawRightString(width - 20*mm, height - 77*mm, f"Due: {due_date}")

        # --- Draw Table ---
        data = [
            ["DESCRIPTION", "CATEGORY", "TOTAL"]
        ]
        data.append([
            f"{item_desc.upper()}\n{item_note}",
            category_display,
            f"INR {float(subtotal):,.2f}"
        ])

        table = Table(data, colWidths=[100*mm, 40*mm, 30*mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#000000")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#FED505")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 20),
            ('TOPPADDING', (0, 1), (-1, -1), 20),
            ('GRID', (0, 0), (-1, -1), 0.1, colors.lightgrey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        table.wrapOn(p, width, height)
        table.drawOn(p, 20*mm, height - 125*mm)

        # --- Totals Box ---
        net_sale = float(subtotal) - float(discount)
        balance = net_sale - float(paid)
        
        box_height = 45*mm
        box_y = height - 135*mm - box_height

        p.setFillColor(colors.HexColor("#000000"))
        p.roundRect(width - 85*mm, box_y, 65*mm, box_height, 5, fill=1)
        
        curr_y = box_y + box_height - 10*mm

        p.setFillColor(colors.whitesmoke)
        p.setFont("Helvetica", 9)
        p.drawString(width - 80*mm, curr_y, "SUBTOTAL")
        p.drawRightString(width - 25*mm, curr_y, f"INR {float(subtotal):,.2f}")
        
        curr_y -= 7*mm
        p.drawString(width - 80*mm, curr_y, "DISCOUNT")
        p.drawRightString(width - 25*mm, curr_y, f"- INR {float(discount):,.2f}")
        
        curr_y -= 7*mm
        p.drawString(width - 80*mm, curr_y, "PAID AMOUNT")
        p.drawRightString(width - 25*mm, curr_y, f"INR {float(paid):,.2f}")
        
        p.setStrokeColor(colors.white)
        p.setLineWidth(0.1)
        p.line(width - 80*mm, curr_y - 4*mm, width - 25*mm, curr_y - 4*mm)
        
        curr_y -= 12*mm
        p.setFont("Helvetica-Bold", 12)
        p.drawString(width - 80*mm, curr_y, "BALANCE DUE")
        p.setFillColor(colors.HexColor("#FED505"))
        p.drawRightString(width - 25*mm, curr_y, f"INR {balance:,.2f}")

        # --- Footer ---
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(colors.black)
        p.drawString(20*mm, 40*mm, "TERMS & CONDITIONS")
        p.setFont("Helvetica", 8)
        p.setFillColor(colors.gray)
        p.drawString(20*mm, 35*mm, "1. Goods once sold/delivered are subject to store policies.")
        p.drawString(20*mm, 31*mm, "2. This is a computer generated invoice and requires no signature.")
        p.drawString(20*mm, 27*mm, "3. For support, contact us at Chavakkad, Thrissur.")

        p.setFont("Helvetica-Bold", 13)
        p.setFillColor(colors.HexColor("#000000"))
        p.drawRightString(width - 20*mm, 35*mm, "Reborn Fitness")
        p.setFont("Helvetica", 8)
        p.setFillColor(colors.gray)
        p.drawRightString(width - 20*mm, 30*mm, "Powering Your Fitness Journey")

        p.showPage()
        p.save()
        
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=filename)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

from django.db.models import Sum

@csrf_exempt
def get_profit(request):
    if request.method == "GET":
        income = Payment.objects.filter(payment_type__iexact='income').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        expense = Payment.objects.filter(payment_type__iexact='expense').aggregate(total=Sum('amount'))['total'] or Decimal('0')
        profit = income - expense

        return JsonResponse({
            "income": float(income),
            "expense": float(expense),
            "profit": float(profit)
        })

@csrf_exempt
def add_expense(request):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            Payment.objects.create(
                amount=Decimal(str(data.get("amount", 0))),
                payment_method=data.get("method", "CASH"),
                payment_type='EXPENSE',
                expense_category=data.get("category", "other"),
                notes=data.get("description", "")
            )
            return JsonResponse({"message": "Expense added successfully"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

from django.utils import timezone
from datetime import timedelta
import calendar

@csrf_exempt
def get_financial_dashboard_data(request):


    if request.method == "GET":
        now = timezone.now()
        
        # 1. Chart Data (Last 6 Months)
        range_type = request.GET.get("range", "6m")
        chart_data = []

        if range_type == "1m":
            for i in range(29, -1, -1):
                day = now - timedelta(days=i)
                income = Payment.objects.filter(payment_type__iexact='income', created_at__date=day.date()).aggregate(total=Sum('amount'))['total'] or 0
                expense = Payment.objects.filter(payment_type__iexact='expense', created_at__date=day.date()).aggregate(total=Sum('amount'))['total'] or 0
                chart_data.append({"name": day.strftime("%d %b"), "income": float(income), "expense": float(expense)})
        else:
            num_months = 12 if range_type == "1y" else (3 if range_type == "3m" else 6)
            for i in range(num_months - 1, -1, -1):
                y = now.year
                m = now.month - i
                while m <= 0: m += 12; y -= 1
                month_name = calendar.month_abbr[m]
                income = Payment.objects.filter(payment_type__iexact='income', created_at__year=y, created_at__month=m).aggregate(total=Sum('amount'))['total'] or 0

                expense = Payment.objects.filter(payment_type__iexact='expense', created_at__year=y, created_at__month=m).aggregate(total=Sum('amount'))['total'] or 0
                chart_data.append({
                    "name": month_name if range_type != '1y' else f"{month_name} {str(y)[2:]}", 
                    "income": float(income), 
                    "expense": float(expense)
                })

        # 2. Distribution Data (This Month Expenses by Category)

        category_map = dict(Payment.CATEGORY)
        
        distribution = []
        this_month_expenses = Payment.objects.filter(
            payment_type__iexact='expense',
            created_at__year=now.year,
            created_at__month=now.month
        )
        total_expense_this_month = this_month_expenses.aggregate(total=Sum('amount'))['total'] or 0
        total_expense_val = float(total_expense_this_month)

        categories = this_month_expenses.values('expense_category').annotate(total=Sum('amount'))
        for c in categories:
            val = float(c['total'])
            percent = round((val / total_expense_val) * 100) if total_expense_val > 0 else 0
            distribution.append({
                "name": category_map.get(c['expense_category'], c['expense_category']),
                "percent": percent,
                "amount": val
            })

        distribution = sorted(distribution, key=lambda x: x['amount'], reverse=True)

        # 3. Recent Expenses
        recent_txs = Payment.objects.filter(payment_type__iexact='expense').order_by('-created_at')[:5]
        recent_expenses = []
        for tx in recent_txs:
            recent_expenses.append({
                "date": tx.created_at.strftime("%b %d, %Y"),
                "category": category_map.get(tx.expense_category, tx.expense_category),
                "desc": tx.notes or f"{category_map.get(tx.expense_category, tx.expense_category)} Expense",
                "amount": float(tx.amount),
                "status": "Paid" 
            })

        return JsonResponse({
            "chartData": chart_data,
            "distribution": distribution,
            "recentExpenses": recent_expenses
        })
import csv
from django.http import HttpResponse

@csrf_exempt
def export_monthly_data(request):
    if request.method == 'GET':
        now = timezone.now()
        transactions = Payment.objects.filter(
            created_at__year=now.year,
            created_at__month=now.month
        ).order_by('-created_at')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="financial_data_{now.strftime("%Y_%b")}.csv"'

        writer = csv.writer(response)
        writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Description'])

        category_map = dict(Payment.CATEGORY)
        for t in transactions:
            writer.writerow([
                t.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                t.get_payment_type_display(),
                category_map.get(t.expense_category, t.expense_category),
                str(t.amount),
                t.notes
            ])

        return response

from .models import SystemSettings
from django.conf import settings

@csrf_exempt
def get_system_settings(request):
    if request.method == 'GET':
        s = SystemSettings.get_settings()
        return JsonResponse({
            "is_password_enabled": s.is_password_enabled,
            "has_password": bool(s.password_hash),
            "db_location": str(settings.DB_PATH)
        })


@csrf_exempt
def update_system_settings(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        s = SystemSettings.get_settings()
        
        action = data.get("action")
        
        if action == "toggle_password":
            enabled = data.get("enabled", False)
            if enabled and not s.password_hash:
                # If enabling for the first time, need a password
                password = data.get("password")
                if not password or len(str(password).strip()) == 0:
                    return JsonResponse({"error": "Password required to enable protection"}, status=400)
                s.set_password(password)
            
            s.is_password_enabled = enabled
            s.save()
            return JsonResponse({"message": "Settings updated", "enabled": s.is_password_enabled})
            
        elif action == "change_password":
            old_password = data.get("old_password")
            new_password = data.get("new_password")
            
            if not new_password or len(str(new_password).strip()) == 0:
                return JsonResponse({"error": "New password cannot be empty"}, status=400)
            
            if s.password_hash and not s.check_password(old_password):
                return JsonResponse({"error": "Incorrect old password"}, status=400)
            
            s.set_password(new_password)
            s.save()
            return JsonResponse({"message": "Password changed successfully"})

    return JsonResponse({"error": "Invalid request"}, status=400)

@csrf_exempt
def verify_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        password = data.get("password")
        s = SystemSettings.get_settings()
        
        if not s.is_password_enabled:
            return JsonResponse({"success": True})
            
        if not password:
            return JsonResponse({"success": False, "error": "Password is required"}, status=401)
            
        if s.check_password(password):
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "error": "Incorrect password"}, status=401)
            
    return JsonResponse({"error": "Invalid request"}, status=400)




# -- Alterations ---------------------------------------------------------------
@csrf_exempt
def get_all_alteration_types(request):
    if request.method == "GET":
        types = AlterationType.objects.all().values('id', 'name', 'description', 'is_active')
        return JsonResponse(list(types), safe=False)

@csrf_exempt
def create_alteration_type(request):
    if request.method == "POST":
        data = json.loads(request.body)
        obj = AlterationType.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            is_active=data.get('is_active', True)
        )
        return JsonResponse({"message": "Alteration type created", "id": obj.id})

@csrf_exempt
def get_all_alterations(request):
    if request.method == "GET":
        booking_id = request.GET.get('booking_id')
        qs = Alteration.objects.select_related('alteration_type', 'product', 'booking__customer').all().order_by('-created_at')
        if booking_id:
            qs = qs.filter(booking_id=booking_id)
            
        data = []
        for a in qs:
            data.append({
                "id": a.id,
                "booking_id": a.booking_id,
                "customer_name": a.booking.customer.name,
                "product_name": a.product.name,
                "alteration_type": a.alteration_type.name if a.alteration_type else None,
                "alteration_type_id": a.alteration_type.id if a.alteration_type else None,
                "alteration_area": a.alteration_area,
                "restore_after_return": a.restore_after_return,
                "notes": a.notes,
                "expected_completion_date": a.expected_completion_date.isoformat() if a.expected_completion_date else None,
                "completed_date": a.completed_date.isoformat() if a.completed_date else None,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            })
        return JsonResponse(data, safe=False)

@csrf_exempt
def create_alteration(request):
    if request.method == "POST":
        data = json.loads(request.body)
        try:
            booking = RentalBooking.objects.get(id=data.get('booking_id'))
            product = Product.objects.get(id=data.get('product_id'))
            
            alt_type = None
            if data.get('alteration_type_id'):
                alt_type = AlterationType.objects.get(id=data.get('alteration_type_id'))
            
            exp_date_str = data.get('expected_completion_date')
            exp_date = datetime.strptime(exp_date_str, '%Y-%m-%d').date() if exp_date_str else None
            
            alt = Alteration.objects.create(
                booking=booking,
                product=product,
                alteration_type=alt_type,
                alteration_area=data.get('alteration_area'),
                restore_after_return=data.get('restore_after_return', False),
                notes=data.get('notes', ''),
                expected_completion_date=exp_date,
                status=data.get('status', 'PENDING')
            )
            return JsonResponse({"message": "Alteration created", "id": alt.id})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def update_alteration(request, alteration_id):
    if request.method == "POST" or request.method == "PUT":
        data = json.loads(request.body)
        try:
            alt = Alteration.objects.get(id=alteration_id)
            if 'status' in data:
                alt.status = data['status']
                if alt.status in ['COMPLETED', 'DELIVERED'] and not alt.completed_date:
                    alt.completed_date = datetime.now().date()
            if 'notes' in data:
                alt.notes = data['notes']
            if 'alteration_area' in data:
                alt.alteration_area = data['alteration_area']
            if 'restore_after_return' in data:
                alt.restore_after_return = data['restore_after_return']
            alt.save()
            return JsonResponse({"message": "Alteration updated"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def get_urgent_alerts(request):
    if request.method == "GET":
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        # 1. Alterations Overdue
        overdue_alts = Alteration.objects.select_related('booking__customer', 'product', 'alteration_type').filter(
            status__in=['PENDING', 'IN_PROGRESS'],
            expected_completion_date__lt=today
        )
        
        # 2. Alterations Due Soon (Today or Tomorrow)
        soon_alts = Alteration.objects.select_related('booking__customer', 'product', 'alteration_type').filter(
            status__in=['PENDING', 'IN_PROGRESS'],
            expected_completion_date__in=[today, tomorrow]
        )
        
        # 3. Pickups Tomorrow
        pickups = RentalBooking.objects.select_related('customer').filter(
            status='PRE_BOOKED',
            rental_date=tomorrow
        )
        
        # 4. Returns Tomorrow
        returns = RentalBooking.objects.select_related('customer').filter(
            status='ACTIVE',
            return_date=tomorrow
        )
        
        data = {
            "overdue_alterations": [{
                "id": a.id,
                "booking_id": a.booking.id,
                "customer_name": a.booking.customer.name,
                "product_name": a.product.name,
                "type": a.alteration_type.name if a.alteration_type else a.alteration_area or 'Alteration',
                "expected_date": a.expected_completion_date.isoformat() if a.expected_completion_date else None
            } for a in overdue_alts],
            "soon_alterations": [{
                "id": a.id,
                "booking_id": a.booking.id,
                "customer_name": a.booking.customer.name,
                "product_name": a.product.name,
                "type": a.alteration_type.name if a.alteration_type else a.alteration_area or 'Alteration',
                "expected_date": a.expected_completion_date.isoformat() if a.expected_completion_date else None
            } for a in soon_alts],
            "pickups_tomorrow": [{
                "id": r.id,
                "customer_name": r.customer.name,
                "customer_phone": r.customer.phone
            } for r in pickups],
            "returns_tomorrow": [{
                "id": r.id,
                "customer_name": r.customer.name,
                "customer_phone": r.customer.phone
            } for r in returns]
        }
        return JsonResponse(data)

@csrf_exempt
@transaction.atomic
def pickup_rental_order(request, order_id):
    if request.method == "POST":
        try:
            booking = RentalBooking.objects.select_for_update().get(id=order_id)
            if booking.status != 'PRE_BOOKED':
                return JsonResponse({"error": "Only PRE_BOOKED orders can be picked up."}, status=400)
            
            booking.status = 'ACTIVE'
            booking.collected_at = timezone.now()
            booking.save()

            items = RentalItem.objects.filter(booking=booking)
            for item in items:
                unit = PhysicalUnit.objects.select_for_update().get(id=item.unit.id)
                unit.status = 'rented'
                unit.save()

            return JsonResponse({"message": "Order marked as picked up", "status": booking.status})
        except RentalBooking.DoesNotExist:
            return JsonResponse({"error": "Rental booking not found"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@transaction.atomic
def delete_rental_order(request, order_id):
    if request.method == "DELETE":
        try:
            booking = RentalBooking.objects.select_for_update().get(id=order_id)
            
            # Revert PhysicalUnit status if the booking was holding items
            if booking.status in ['PRE_BOOKED', 'ACTIVE', 'OVERDUE']:
                items = RentalItem.objects.filter(booking=booking)
                for item in items:
                    unit = PhysicalUnit.objects.select_for_update().get(id=item.unit.id)
                    # For PRE_BOOKED, we already confirmed it doesn't set status to rented,
                    # but if it was ACTIVE/OVERDUE it was 'rented'.
                    # Just to be safe, revert to 'available' if it was 'rented' or 'maintenance'
                    unit.status = 'available'
                    unit.save()
                    
            booking.delete()
            return JsonResponse({"message": "Booking deleted successfully."})
        except RentalBooking.DoesNotExist:
            return JsonResponse({"error": "Rental booking not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

# BARCODE ENDPOINTS
@csrf_exempt
def get_unit_by_barcode(request, barcode):
    if request.method == "GET":
        try:
            unit = PhysicalUnit.objects.select_related('product', 'product__category').get(barcode=barcode)
            data = {
                "unit": {
                    "id": unit.id,
                    "unit_id": unit.unit_id,
                    "barcode": unit.barcode,
                    "size": unit.size,
                    "status": unit.status,
                },
                "product": {
                    "id": unit.product.id,
                    "code": unit.product.code,
                    "name": unit.product.name,
                    "category": unit.product.category.name,
                    "rental_price": float(unit.product.rental_price),
                    "is_available": unit.product.is_available,
                }
            }
            return JsonResponse(data)
        except PhysicalUnit.DoesNotExist:
            return JsonResponse({"error": "Barcode not found"}, status=404)

@csrf_exempt
def get_order_by_barcode(request, barcode):
    if request.method == "GET":
        today = date.today()
        from .models import RentalBooking, RentalItem
        orders = RentalBooking.objects.filter(
            status__in=['ACTIVE', 'OVERDUE'],
            items__unit__barcode=barcode
        ).distinct()
        
        if not orders.exists():
            return JsonResponse({"error": "No active rental found for this barcode"}, status=404)
        
        o = orders.first()
        items = []
        for i in o.items.all():
            items.append({
                "product_id": i.product.id,
                "product_name": i.product.name,
                "product_code": i.product.code,
                "unit_id": i.unit.unit_id if i.unit else None,
                "unit_status": i.unit.status if i.unit else None,
            })
        
        first_item = items[0] if items else {}

        data = {
            "id": o.id,
            "order_code": f"RNT-{o.id:04d}",
            "customer_name": o.customer.name,
            "customer_phone": o.customer.phone,
            "items": items,
            "item_name": first_item.get("product_name"),
            "item_code": first_item.get("product_code"),
            "unit_id": first_item.get("unit_id"),
            "unit_status": first_item.get("unit_status"),
            "rental_date": o.rental_date,
            "return_date": o.return_date,
            "rental_amount": float(o.rental_amount),
            "discount_amount": float(o.discount_amount),
            "coupon_code": o.coupon.code if o.coupon else None,
            "advance_paid": float(o.advance_paid),
            "due_amount": float(o.due_amount),
            "security_deposit": float(o.security_deposit),
            "deposit_status": o.deposit_status,
            "refunded_amount": float(o.refunded_amount),
            "deducted_amount": float(o.deducted_amount),
            "damage_notes": o.damage_notes,
            "is_returned": o.is_returned,
            "collected_at": o.collected_at.isoformat() if o.collected_at else None,
            "returned_at": o.returned_at.isoformat() if o.returned_at else None,
            "booking_type": o.booking_type,
            "booking_date": o.booking_date.isoformat() if o.booking_date else None,
            "status": "OVERDUE" if o.status == 'ACTIVE' and not o.is_returned and o.return_date < today else o.status,
            "alterations_count": o.alterations.count(),
            "payments": [{"id": p.id, "amount": float(p.amount), "method": p.payment_method, "reference": p.transaction_reference, "date": p.created_at.isoformat()} for p in o.payments.all()]
        }
        return JsonResponse(data)

@csrf_exempt
def record_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        amount = float(data.get("amount", 0))
        if amount <= 0:
            return JsonResponse({"error": "Invalid amount"}, status=400)
            
        kwargs = {
            'amount': amount,
            'payment_method': data.get('method', 'CASH'),
            'payment_type': data.get('payment_type', 'INCOME'),
            'transaction_reference': data.get('reference', ''),
            'notes': data.get('notes', ''),
            'expense_category': data.get('expense_category', '')
        }
        
        module = data.get('module')
        module_id = data.get('module_id')
        
        try:
            if module == 'RENTAL':
                kwargs['rental_booking'] = RentalBooking.objects.get(id=module_id)
            elif module == 'STITCHING':
                kwargs['stitching_order'] = StitchingOrder.objects.get(id=module_id)
            elif module == 'SALE':
                kwargs['accessory_sale'] = AccessorySale.objects.get(id=module_id)
            
            payment = Payment.objects.create(**kwargs)
            
            return JsonResponse({
                "message": "Payment recorded",
                "payment_id": payment.id
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Invalid request method"}, status=405)
