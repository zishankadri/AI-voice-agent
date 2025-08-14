# from django.contrib import admin

# # from django.contrib.auth.admin import UserAdmin
# from .models import UserAccount

# admin.site.register(UserAccount)

# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import UserAccount
# from .forms import UserCreationForm, UserChangeForm
# from unfold.admin import ModelAdmin

# class UserAccountAdmin(BaseUserAdmin, ModelAdmin):
#     form = UserChangeForm
#     add_form = UserCreationForm

#     list_display = ('email', 'is_admin', 'is_superuser')
#     list_filter = ('is_admin', 'is_superuser')
#     fieldsets = (
#         (None, {'fields': ('email', 'password')}),
#         ('Permissions', {'fields': ('is_active', 'is_admin', 'is_superuser', 'is_staff', 'groups', 'user_permissions')}),
#     )
#     add_fieldsets = (

#         (None, {
#             'classes': ('wide',),
#             'fields': ('email', 'password1', 'password2'),
#         }),
#     )
#     search_fields = ('email',)
#     ordering = ('email',)

# admin.site.register(UserAccount, UserAccountAdmin)



from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserAccount
from .forms import UserCreationForm, UserChangeForm
from unfold.admin import ModelAdmin

class UserAccountAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('email', 'restaurant', 'is_admin', 'is_superuser')
    list_filter = ('is_admin', 'is_superuser', 'restaurant')

    fieldsets = (
        (None, {
            'fields': ('email', 'password', 'restaurant')  # Added restaurant here
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_admin', 'is_superuser', 'is_staff',
                'groups', 'user_permissions'
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'restaurant')  # Added restaurant here
        }),
    )

    search_fields = ('email',)
    ordering = ('email',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(email='aivoiceapp@gmail.com')

admin.site.register(UserAccount, UserAccountAdmin)
