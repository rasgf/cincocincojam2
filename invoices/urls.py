from django.urls import path
from . import views

app_name = 'invoices'

urlpatterns = [
    # URLs para professores
    path('settings/', views.company_settings, name='company_settings'),
    
    # URLs para emissão de notas fiscais
    path('emit/<int:transaction_id>/', views.emit_invoice, name='emit'),
    path('retry/<int:invoice_id>/', views.retry_invoice, name='retry'),
    path('status/<int:invoice_id>/', views.check_invoice_status, name='check_status'),
    path('cancel/<int:invoice_id>/', views.cancel_invoice, name='cancel'),
    path('delete/<int:invoice_id>/', views.delete_invoice, name='delete'),
    
    # URLs para o modo de teste
    path('test-mode/', views.test_mode, name='test_mode'),
]
