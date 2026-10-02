"""HeartDiseaseProject URL Configuration."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

app_name = 'heartdisease'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/predict/', views.predict, name='predict'),
    path('api/model-status/', views.model_status, name='model_status'),
]
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('heartdisease.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)