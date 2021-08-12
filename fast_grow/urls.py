"""fast_grow urls"""
from django.urls import path

from . import views

urlpatterns = [
    path('complex', views.complex_create, name='complex_create'),
    path('complex/<int:complex_id>', views.complex_detail, name='complex_detail'),
    path('core', views.core_create, name='core_create'),
    path('core/<int:core_id>', views.core_detail, name='core_detail')
]
