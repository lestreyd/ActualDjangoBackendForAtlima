from django.db import models
from atlima_django.users.models import User
from atlima_django.event.promo_code import PromoCode


class BankNotification(models.Model):
    """Модель для уведомлений от банка"""

    terminal_key = models.CharField(
        max_length=128
    )
    order_id = models.CharField(max_length=128)
    success = models.BooleanField()
    status = models.CharField(max_length=32)
    payment_id = models.IntegerField()
    error_code = models.CharField(max_length=32)
    amount = models.IntegerField()
    card_id = models.IntegerField()
    pan = models.CharField(max_length=16)
    expiration_date = models.CharField(
        max_length=10
    )
    token = models.CharField(max_length=256)

    def __str__(self):
        id = str(self.id)
        return f"bank_notification_{id}"


class TransactionHistory(models.Model):
    """Модель хранения банковских операций"""

    INIT = "init"
    FINISH_AUTHORIZE = "finish_authorize"
    ADD_CARD = "add_card"
    ATTACH_CARD = "attach_card"
    REMOVE_CARD = "remove_card"
    GET_CARD_LIST = "card_list"
    CANCEL = "cancel"

    operations = [
        (INIT, "Initialization"),
        (
            FINISH_AUTHORIZE,
            "Finish Authorization",
        ),
        (ADD_CARD, "Add Card"),
        (ATTACH_CARD, "Attach Card"),
        (REMOVE_CARD, "Remove Card"),
        (GET_CARD_LIST, "Card List"),
        (CANCEL, "Cancel Payment"),
    ]
    # тип операции
    operation = models.CharField(
        choices=operations,
        default=INIT,
        max_length=128,
    )

    BANK_REQUEST = "Bank Request"
    BANK_RESPONSE = "Bank Response"

    information_types = [
        (BANK_REQUEST, "Request"),
        (BANK_RESPONSE, "Response"),
    ]

    # тип информации (response или request)
    information_type = models.CharField(
        choices=information_types,
        default=BANK_REQUEST,
        max_length=128,
    )

    terminal_key = models.CharField(
        max_length=128, null=False, blank=False
    )
    amount = models.CharField(
        max_length=128, null=True, blank=True
    )
    order_id = models.CharField(
        max_length=128, null=True, blank=True
    )
    customer_key = models.CharField(
        max_length=256, null=True, blank=True
    )
    language = models.CharField(
        max_length=10, null=True, blank=True
    )
    recurrent = models.CharField(
        max_length=3, null=True, blank=True
    )

    success = models.BooleanField(
        default=False, null=True, blank=True
    )
    status = models.CharField(
        max_length=128, null=True, blank=True
    )
    payment_id = models.CharField(
        max_length=1024, null=True, blank=True
    )
    error_code = models.CharField(
        max_length=4, null=True, blank=True
    )
    card_data = models.CharField(
        max_length=4096, null=True, blank=True
    )
    card_number = models.CharField(
        max_length=50, null=True, blank=True
    )
    exp = models.CharField(
        max_length=10, null=True, blank=True
    )
    card_holder = models.CharField(
        max_length=512, null=True, blank=True
    )
    cvv = models.CharField(
        max_length=3, null=True, blank=True
    )
    check_type = models.CharField(
        max_length=10, null=True, blank=True
    )
    request_key = models.CharField(
        max_length=512, null=True, blank=True
    )
    card_id = models.CharField(
        max_length=128, null=True, blank=True
    )

    currency = models.CharField(
        max_length=5, null=True, blank=True
    )
    token = models.CharField(
        max_length=256, null=True, blank=True
    )
    ip = models.CharField(
        max_length=20, null=True, blank=True
    )
    description = models.CharField(
        max_length=1024, null=True, blank=True
    )
    data = models.JSONField(null=True, blank=True)
    phone = models.CharField(
        max_length=20, null=True, blank=True
    )
    send_mail = models.BooleanField(
        null=True, blank=True
    )
    info_email = models.CharField(
        max_length=256, null=True, blank=True
    )
    rebill_id = models.CharField(
        max_length=256, null=True, blank=True
    )
    pay_form = models.CharField(
        max_length=1024, null=True, blank=True
    )
    receipt = models.JSONField(
        null=True, blank=True
    )
    redirect_due_date = models.CharField(
        max_length=20, null=True, blank=True
    )
    payment_url = models.CharField(
        max_length=1024, null=True, blank=True
    )
    message = models.CharField(
        max_length=1024, null=True, blank=True
    )
    details = models.CharField(
        max_length=1024, null=True, blank=True
    )

    md = models.CharField(
        max_length=64, null=True, blank=True
    )
    response = models.JSONField(
        null=True, blank=True
    )

    created = models.DateTimeField(
        auto_now_add=True, null=True, blank=True
    )

    def __str__(self):
        id = self.id
        return f"bank_message-{id}"


class Order(models.Model):
    """Таблица с заказами"""

    amount = models.PositiveBigIntegerField()
    status = models.BooleanField(default=False)
    user = models.ForeignKey(
        to=User, on_delete=models.CASCADE
    )
    payment_id = models.CharField(
        max_length=512, null=True, blank=True
    )

    created = models.DateTimeField(
        auto_now_add=True
    )
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        order_id = str(self.id)
        amount = str(self.amount)
        return f"order_id{order_id}_{amount}"


class OrderItem(models.Model):
    """Детализация заказов"""

    order_id = models.ForeignKey(
        to=Order, on_delete=models.CASCADE
    )
    object_type = models.CharField(max_length=128)
    object_id = models.PositiveBigIntegerField()
    amount = models.PositiveBigIntegerField()
    promocode = models.ForeignKey(
        to=PromoCode,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        oid = str(self.id)
        orderid = str(self.order_id)
        return f"item_id{oid}-{orderid}"
