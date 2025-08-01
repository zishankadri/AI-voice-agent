from django.contrib import admin
from .models import Order, OrderItem, MenuItem

# admin.site = UnfoldAdminSite()

# admin.site.register(Order, UnfoldAdmin)
# admin.site.register(OrderItem, UnfoldAdmin)
# admin.site.register(MenuItem, UnfoldAdmin)

from django.contrib import admin
from unfold.admin import ModelAdmin


@admin.register(Order)
class CustomAdminClass(ModelAdmin):
    pass

@admin.register(OrderItem)
class CustomAdminClass(ModelAdmin):
    pass

@admin.register(MenuItem)
class CustomAdminClass(ModelAdmin):
    pass