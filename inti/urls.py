from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "Selamat Datang di Sistem Akademik" # Ini teks permanen di atas
admin.site.site_title = "Admin Akademik"
admin.site.index_title = "Panel Kontrol Utama"

# inti/urls.py
urlpatterns = [
    path('admin/', admin.site.urls),
    path('akademik/', include('akademik.urls')),    
    path('portal/', include('core.urls')),
    path('', include('web_publik.urls')), # Pintu masuk tunggal
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)