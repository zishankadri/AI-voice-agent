from django.db import models


class StatusEnum(models.TextChoices):
    PENDING = "PENDING", "Pending"
    UNPAID = "UNPAID", "Unpaid"
    PAID = "PAID", "Paid"
    CONFIRMED = "CONFIRMED", "Confirmed"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    READY = "READY", "Ready"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
    FAILED = "FAILED", "Failed"


class Order(models.Model):
    call_sid = models.CharField(max_length=64, unique=True)
    conversation = models.TextField(default="", blank=True)
    status = models.CharField(
        max_length=32,
        choices=StatusEnum.choices,
        default=StatusEnum.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} - {self.status}"


class MenuItem(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()

    def __str__(self):
        return self.name


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    modifications = models.TextField(default="", blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['order', 'menu_item'], name='unique_item_per_order'
            )
        ]

    def __str__(self):
        return f"{self.quantity} x {self.menu_item.name} (Order #{self.order.id})"


# models.py
class AdminSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()

    def __str__(self):
        return self.key
