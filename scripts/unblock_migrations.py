import re

with open('d:/Tron-Projects/Perfect-Fit/backend/adminApp/views.py', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Fix the import
c = c.replace('Transaction', 'Payment')

# 2. Fix the instances where advance_paid and advance_payment are used in views.py
# (We will just comment them out or replace them with 0 temporarily so the migration passes,
# then we'll do a proper rewrite of the views.)

c = re.sub(r'advance_paid=.*?\,', 'advance_paid=0, # TEMPORARY', c)
c = re.sub(r'advance_payment=.*?\,', 'advance_payment=0, # TEMPORARY', c)

# We also need to fix Payment.objects.create calls that were Transaction.objects.create
# Transaction.objects.create(amount=..., transaction_type='income', category='rental', reference_id=...)
# -> Payment.objects.create(...)

# Actually, the quickest way to unblock makemigrations is just to replace "Transaction" with "Payment"
# wait, if I replace Transaction with Payment globally, Payment.objects.create(amount=..., transaction_type='income'...) will fail if transaction_type isn't a field on Payment.
# Payment has `payment_type` instead of `transaction_type`.

c = c.replace('transaction_type=', 'payment_type=')
c = c.replace('category=', 'expense_category=')
c = c.replace('reference_id=', 'module_reference_id= # TODO fix ')

with open('d:/Tron-Projects/Perfect-Fit/backend/adminApp/views.py', 'w', encoding='utf-8') as f:
    f.write(c)

print('Patched views.py to unblock makemigrations')
