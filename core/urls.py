# Jalur file: C:\web\core\urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Halaman Dashboard Utama Aplikasi Core
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Data Master (Siswa & Guru)
    path('master/siswa/', views.data_siswa, name='data_siswa'),
    path('master/guru/', views.data_guru, name='data_guru'),
    
    # Manajemen Keuangan Siswa (Sinkron dengan reverse views.py kemarin)
    path('keuangan/', views.manajemen_keuangan, name='keuangan_siswa'),
    path('keuangan/toggle/<int:pk>/', views.toggle_lunas, name='toggle_lunas'),
    
    # Manajemen Inventaris Sekolah
    path('inventaris/', views.inventaris, name='inventaris'),
]