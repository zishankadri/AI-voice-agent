from django.urls import path

from . import views
from . import views

urlpatterns = [
    # Register & Login URLs
    path('register/', views.register_page, name="register"),
    path('login/', views.login_page, name="login"),
    path('logout/', views.logout_page, name="logout"),


    # Verification URLs
    path('verify_email/<str:auth_token>/', views.verify_email_page, name="verify_email"),
    path('verify_phone/<str:auth_token>/', views.verify_phone_page, name="verify_phone"),
    path('error/', views.error, name="error"),
    path('change_password/<str:email>/<str:auth_token>/', views.change_password, name="change_password"),
    path('forgot_password/', views.forgot_password, name="forgot_password"),
    # path('check_email/', views.check_your_email, name="error"),

]
