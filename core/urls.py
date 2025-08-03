from django.urls import path

from django.conf import settings
from django.conf.urls.static import static

from . import views
urlpatterns = [
    path('voice/', views.voice, name='voice'),
    path('process_speech/', views.process_speech, name='process_speech'),
]
