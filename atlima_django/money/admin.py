from .models import PriceConfiguration, PromoCode
from django.contrib import admin
from .models import (PromoCode, 
                     BankNotification, 
                     TransactionHistory,
                     PriceConfiguration,
                     Currency,
                     Order,
                     OrderItem)

# уведомления от банка
class BankNotificationsAdmin(admin.ModelAdmin):
    list_display = ['terminal_key', 'order_id', 'success', 
                    'status', 'payment_id', 'error_code', 
                    'amount', 'card_id', 'pan', 'expiration_date', 
                    'token']
    class Meta:
        model = BankNotification
        fields = '__all__'

admin.site.register(BankNotification, BankNotificationsAdmin)

# просмотр транзакций
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'operation', 'created', 
                    'success', 'order_id', 'card_id', 
                    'customer_key', 'payment_id', 'error_code', 
                    'response']
    class Meta:
        model = TransactionHistory
        fields = '__all__'
        
admin.site.register(TransactionHistory, TransactionAdmin)
        
# список доступных в системе валют
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('id', 'digital_code', 'code', 'title', 'weight_in_list')

admin.site.register(Currency, CurrencyAdmin)

# расширенное администрирование ценовой конфигурации
# может быть Бесплатно, Единая, По графику и По слотам.
# каждая ценовая опция подразумевает свою логику.
class ExtendedPriceConfigurationAdmin(admin.ModelAdmin):
    model = PriceConfiguration
    readonly_fields = ['id',]
    list_display = ('id', 'titles')

admin.site.register(PriceConfiguration, ExtendedPriceConfigurationAdmin)

# предмет заказа - в нашем случае это обычно слоты
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ['order_id', 'object_type', 'object_id', 'amount', 'promocode']
    extra = 0
    min_num = 1
    max_num = 20


# администрирование заказов
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'amount', 'status', 'user', 'created', 'updated']
    inlines = [OrderItemInline]
    class Meta:
        model = Order
        fields = '__all__'

admin.site.register(Order, OrderAdmin)