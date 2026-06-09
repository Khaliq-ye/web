# Jalur file: C:\web\web_publik\urls.py
from django.urls import path
from . import views

app_name = 'web_publik'

urlpatterns = [
    # --- 1. Beranda & Informasi Publik ---
    path('', views.index, name='index'),
    path('profil/', views.profil, name='profil'),
    path('akademik-info/', views.akademik_info, name='akademik_info'),
    path('galeri/', views.galeri, name='galeri'),
    path('berita/', views.berita, name='berita'),  # Jalur untuk daftar semua berita
    path('berita/<int:id>/', views.detail_berita, name='detail_berita'),
    path('ppdb/gelombang-detail-json/<int:id>/', views.gelombang_detail_json, name='gelombang_detail_json'),
    
    # Path untuk melayani request data Jendela Mengambang (Modal) JavaScript
    path('berita/detail-json/<int:berita_id>/', views.detail_berita_json, name='detail_berita_json'),
    
    # --- 2. Sistem Pendaftaran (PPDB) ---
    path('ppdb-online/', views.ppdb_online, name='ppdb_online'),
    
    # --- 3. Autentikasi & Portal Login ---
    path('login/', views.login_portal, name='login_portal'),
    path('logout/', views.logout_user, name='logout'),
]