from django.contrib import admin
from .models import Order, OrderItem, MenuItem

# admin.site = UnfoldAdminSite()

# admin.site.register(Order, UnfoldAdmin)
# admin.site.register(OrderItem, UnfoldAdmin)
# admin.site.register(MenuItem, UnfoldAdmin)

from django.contrib import admin
from unfold.admin import ModelAdmin


# @admin.register(Order)
# class CustomAdminClass(ModelAdmin):
#     pass

# @admin.register(OrderItem)
# class CustomAdminClass(ModelAdmin):
#     pass

# @admin.register(MenuItem)
# class CustomAdminClass(ModelAdmin):
#     pass


class OrderItemInline(admin.TabularInline):  # Or admin.StackedInline
    model = OrderItem
    extra = 0  # Number of blank forms
    show_change_link = True  # Adds a link to edit the related item

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    inlines = [OrderItemInline]

# Menu Items
from import_export import resources
from import_export.admin import ImportExportModelAdmin

class MenuItemResource(resources.ModelResource):
    class Meta:
        model = MenuItem
        fields = ('id', 'name', 'price')

@admin.register(MenuItem)
class MenuItemAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = MenuItemResource
    list_display = ('name', 'price')



# admin.py
from unfold.admin import ModelAdmin
from .models import AdminSetting

@admin.register(AdminSetting)
class AdminSettingAdmin(ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)
