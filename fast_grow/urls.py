from django.urls import path

from . import views

urlpatterns = [
    path('complex', views.complex_create, name='complex_create'),
    path('complex/<int:complex_id>', views.complex_detail, name='complex_detail'),
]