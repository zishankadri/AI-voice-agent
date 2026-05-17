from django.contrib import admin
from .models import (
    Order,
    OrderItem,
    MenuItem,
    AdminSetting,
    Restaurant,
    Category,
    Branch,
)
from unfold.admin import ModelAdmin, mark_safe, TabularInline

from import_export import resources
from import_export.admin import ImportExportModelAdmin


class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0  # Number of blank forms
    show_change_link = True  # Adds a link to edit the related item


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    inlines = [OrderItemInline]
    list_display = ("name_display", "status", "created_at")
    readonly_fields = ["readable_json"]
    exclude = ["conversation"]

    @admin.display(description="Conversation")
    def readable_json(self, obj):
        if obj.conversation:
            emoji_map = {"user": "👤", "agent": "🤖", "system": "⚙️"}
            conversation_html_list = []
            for message in obj.conversation:
                role = message.get("role", "unknown")
                emoji = emoji_map.get(role, "")
                text = message["text"]

                conversation_html_list.append(
                    mark_safe(
                        "".join(
                            (
                                '<div class="border border-neutral-500/25 bg-white rounded-md p-4">',
                                f'<p class="font-mono text-sm">{emoji} {role}:</p>',
                                f"<p>{text}</p>",
                                "</div>",
                            )
                        )
                    )
                )
            return mark_safe(
                (
                    '<div class="flex flex-col gap-4 overflow-auto">'
                    f"{''.join(conversation_html_list)}"
                    "</div>"
                )
            )
        return "No conversation"

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
        fields = ("id", "name", "phone_number")


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    class Meta:
        model = Category
        fields = ("id", "name", "phone_number")


# Menu Items
class MenuItemResource(resources.ModelResource):
    class Meta:
        model = MenuItem
        fields = "name"


@admin.register(MenuItem)
class MenuItemAdmin(ImportExportModelAdmin, ModelAdmin):
    resource_class = MenuItemResource
    list_display = ("name", "price")


@admin.register(AdminSetting)
class AdminSettingAdmin(ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)


@admin.register(Branch)
class BranchAdmin(ModelAdmin):
    pass
    # list_display = ("key", "value")
    # search_fields = ("key",)
