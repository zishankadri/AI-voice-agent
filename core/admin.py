from django.contrib import admin
from .models import Order, OrderItem, MenuItem, AdminSetting, Restaurant, Category
from unfold.admin import ModelAdmin

from import_export import resources
from import_export.admin import ImportExportModelAdmin


class OrderItemInline(admin.TabularInline):  # Or admin.StackedInline
    model = OrderItem
    extra = 0  # Number of blank forms
    show_change_link = True  # Adds a link to edit the related item


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ("name_display", "status", "created_at")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(restaurant=request.user.restaurant)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True  # list view
        return obj.restaurant == request.user.restaurant

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.restaurant == request.user.restaurant
    
    def name_display(self, obj):
        return str(obj)
    name_display.short_description = "Name"

@admin.register(Restaurant)
class RestaurantAdmin(ModelAdmin):
    class Meta:
        model = Restaurant
        fields = ('id', 'name', 'phone_number')

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    class Meta:
        model = Category
        fields = ('id', 'name', 'phone_number')
# Menu Items
class MenuItemResource(resources.ModelResource):
    class Meta:
        model = MenuItem
        fields = ('name')

@admin.register(MenuItem)
class MenuItemAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = MenuItemResource
    list_display = ('name', 'price')


@admin.register(AdminSetting)
class AdminSettingAdmin(ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)

