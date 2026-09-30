from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('catalog/', include('catalog.urls')),
    
    # --- ADD THIS LINE FOR LOGIN SYSTEM ---
    path('accounts/', include('django.contrib.auth.urls')),
    
    path('', lambda request: redirect('catalog/search/')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)