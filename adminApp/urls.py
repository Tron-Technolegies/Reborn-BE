from django.urls import path
from . import views

urlpatterns = [
# tested
    path('items/', views.get_all_rental_items, name='get_all_rental_items'),
    path('items/create/', views.create_rental_item, name='create_rental_item'),
    path('items/<int:item_id>/', views.get_rental_item, name='get_rental_item'),
    path('items/<int:item_id>/update/', views.update_rental_item, name='update_rental_item'),
    path('items/<int:item_id>/delete/', views.delete_rental_item, name='delete_rental_item'),   
    path('items/code/<str:code>/', views.get_item_by_code, name='get_item_by_code'),
    path('items/<int:item_id>/units/', views.get_item_units, name='get_item_units'),
    path('units/<int:unit_id>/update-status/', views.update_unit_status, name='update_unit_status'),

# tested
    path('orders/', views.get_all_rental_orders, name='get_all_rental_orders'),
    path('orders/create/', views.create_rental_order, name='create_rental_order'),
    path('units/barcode/<str:barcode>/', views.get_unit_by_barcode, name='get_unit_by_barcode'),
    path('orders/barcode/<str:barcode>/', views.get_order_by_barcode, name='get_order_by_barcode'),

    
    path('orders/<int:order_id>/return/', views.return_rental_order, name='return_rental_order'),
    path('orders/<int:order_id>/pickup/', views.pickup_rental_order, name='pickup_rental_order'),
    path('orders/<int:order_id>/delete/', views.delete_rental_order, name='delete_rental_order'),
    
    path('items/check-availability/', views.check_item_availability, name='check_item_availability'),
    path('items/<int:item_id>/history/', views.get_item_history, name='get_item_history'),
    path('reminders/run/', views.check_and_send_reminders, name='check_reminders'),
    path('orders/overdue/', views.get_overdue_items, name='get_overdue_items'),

    path('alteration-types/', views.get_all_alteration_types, name='get_all_alteration_types'),
    path('alteration-types/create/', views.create_alteration_type, name='create_alteration_type'),
    path('alterations/', views.get_all_alterations, name='get_all_alterations'),
    path('alterations/create/', views.create_alteration, name='create_alteration'),
    path('alterations/<int:alteration_id>/update/', views.update_alteration, name='update_alteration'),


# tested
    path('categories/', views.get_all_categories, name='get_all_categories'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    path('categories/<int:category_id>/update/', views.update_category, name='update_category'),

# tested
    path('materials/', views.get_all_materials, name='get_all_materials'),
    path('materials/create/', views.create_material, name='create_material'),
    path('materials/<int:material_id>/', views.get_material, name='get_material'),
    path('materials/<int:material_id>/update/', views.update_material, name='update_material'),
    path('materials/<int:material_id>/delete/', views.delete_material, name='delete_material'),
    path('materials/code/<str:code>/', views.get_material_by_code, name='get_material_by_code'),

# tested
    path('purchases/', views.get_all_purchases, name='get_all_purchases'),
    path('purchases/create/', views.create_material_purchase, name='create_material_purchase'),
    path('purchases/<int:purchase_id>/', views.get_purchase, name='get_purchase'),

# tested
    path('stitching/', views.get_all_stitching_orders, name='get_all_stitching_orders'),
    path('stitching/create/', views.create_stitching_order, name='create_stitching_order'),
    path('stitching/<int:order_id>/', views.get_stitching_order, name='get_stitching_order'),
    path('stitching/<int:order_id>/update-status/', views.update_stitching_status, name='update_stitching_status'),
    path('stitching/<int:order_id>/collect-payment/', views.collect_stitching_payment, name='collect_stitching_payment'),
    path('stitching/<int:order_id>/delete/', views.delete_stitching_order, name='delete_stitching_order'),

    # ACCESSORIES
    path('accessories/', views.get_all_accessories, name='get_all_accessories'),
    path('accessories/create/', views.create_accessory, name='create_accessory'),
    path('accessories/<int:accessory_id>/update/', views.update_accessory, name='update_accessory'),
    path('accessories/<int:accessory_id>/delete/', views.delete_accessory, name='delete_accessory'),
    path('accessories/sales/', views.get_all_accessory_sales, name='get_all_accessory_sales'),
    path('accessories/sales/create/', views.create_accessory_sale, name='create_accessory_sale'),
    path('accessories/sales/<int:sale_id>/update/', views.update_accessory_sale, name='update_accessory_sale'),
    path('accessories/sales/<int:sale_id>/delete/', views.delete_accessory_sale, name='delete_accessory_sale'),
    
    # DASHBOARD
    path('dashboard/stats/', views.get_dashboard_stats, name='get_dashboard_stats'),
    path('dashboard/urgent-alerts/', views.get_urgent_alerts, name='get_urgent_alerts'),

    # COUPONS
    path('coupons/', views.get_all_coupons, name='get_all_coupons'),
    path('coupons/create/', views.create_coupon, name='create_coupon'),
    path('coupons/<int:coupon_id>/update/', views.update_coupon, name='update_coupon'),
    path('coupons/<int:coupon_id>/delete/', views.delete_coupon, name='delete_coupon'),
    path('coupons/validate/', views.validate_coupon, name='validate_coupon'),
    path('invoices/<str:order_type>/<int:order_id>/', views.generate_invoice_pdf, name='generate_invoice_pdf'),
    
    # FINANCIAL LAYER
    path('get-profit/', views.get_profit, name='get_profit'),
    path('add-expense/', views.add_expense, name='add_expense'),
    path('get-dashboard-data/', views.get_financial_dashboard_data, name='get_financial_dashboard_data'),
    path('export-monthly-data/', views.export_monthly_data, name='export_monthly_data'),

    # SYSTEM SETTINGS
    path('settings/', views.get_system_settings, name='get_system_settings'),
    path('settings/update/', views.update_system_settings, name='update_system_settings'),
    path('settings/verify-password/', views.verify_password, name='verify_password'),
    path('payments/record/', views.record_payment, name='record_payment'),
]
