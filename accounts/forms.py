from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import UserAccount
from .utils import generate_ref_code

class UserAccountForm(UserCreationForm):
    # password1 = forms.CharField(label="Password", widget=forms.PasswordInput)

    class Meta:
        model = UserAccount
        fields = ['email', 'password1', 'password2']

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # Add custome css class to all input widgets.
        for field_name, field in self.fields.items():
            current_class = field.widget.attrs.get('class') or ''
            field.widget.attrs['class'] = current_class+" "+'regular-input'

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email_auth_token = generate_ref_code()

        if commit:
            user.save()
        return user


# forms.py
from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import UserAccount

class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = UserAccount
        fields = ('email',)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match.")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # hash password
        if commit:
            user.save()
        return user

class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = UserAccount
        fields = ('email', 'password', 'is_active', 'is_admin', 'is_superuser', 'is_staff', 'groups', 'user_permissions')

    def clean_password(self):
        return self.initial["password"]
