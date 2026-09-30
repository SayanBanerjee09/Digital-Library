from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_page, name='search'),
    path('upload/', views.upload_book, name='upload'),
    
    # --- NEW DASHBOARD URLS ---
    path('dashboard/', views.dashboard, name='dashboard'),
    path('delete/<str:filename>/', views.delete_book, name='delete_book'),
]