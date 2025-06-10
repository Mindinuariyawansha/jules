from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('menu/', views.menu_list, name='menu_list'),
]
