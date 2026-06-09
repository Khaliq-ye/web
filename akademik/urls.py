# akademik/urls.py
from django.urls import path
from . import views
from . import views_export          # ← import file baru
from core import views as core_views

app_name = 'akademik'

urlpatterns = [
    # =========================================================================
    # 1. DASHBOARD ROLES
    # =========================================================================
    path('dashboard/guru/',      views.dashboard_guru,      name='dashboard_guru'),
    path('dashboard/siswa/',     views.dashboard_siswa,     name='dashboard_siswa'),
    path('dashboard/kepsek/',    views.dashboard_kepsek,    name='dashboard_kepsek'),
    path('dashboard/wali/',      views.dashboard_wali,      name='dashboard_wali'),
    path('dashboard/staf/',      views.dashboard_staf,      name='dashboard_staf'),
    path('dashboard/bendahara/', views.dashboard_bendahara, name='dashboard_bendahara'),
    path('dashboard/perpus/',    views.dashboard_perpus,    name='dashboard_perpus'),
    path('laporkan-bug/',        views.laporkan_bug,        name='laporkan_bug'),

    # =========================================================================
    # 2. PROFILE API ACTIONS
    # =========================================================================
    path('dashboard/guru/update-foto/',   views.update_foto_guru,   name='update_foto_guru'),
    path('dashboard/kepsek/update-foto/', views.update_foto_kepsek, name='update_foto_kepsek'),

    # =========================================================================
    # 3. DATA REMOVALS
    # =========================================================================
    path('materi/hapus/<int:materi_id>/', views.hapus_materi, name='hapus_materi'),
    path('jurnal/hapus/<int:jurnal_id>/', views.hapus_jurnal, name='hapus_jurnal'),

    # =========================================================================
    # 4. ACADEMIC FEATURES (KBM Guru)
    # =========================================================================
    path('jadwal/',    views.jadwal_pelajaran, name='jadwal_pelajaran'),
    path('jurnal/',    views.jurnal_mengajar,  name='jurnal_mengajar'),
    path('materi/',    views.materi_ajar,      name='materi_ajar'),
    path('presensi/',  views.presensi,         name='presensi'),
    path('nilai/',     views.input_nilai,      name='input_nilai'),
    path('raport/',    views.e_rapor,          name='e_rapor'),
    path('elearning/', views.e_learning,       name='e_learning'),

    # =========================================================================
    # 5. SISWA — ENDPOINT TERPISAH
    # =========================================================================
    path('siswa/kirim-jawaban/', views.kirim_jawaban_siswa, name='kirim_jawaban_siswa'),
    path('api/tugas-detail/<int:tugas_id>/', views.detail_tugas_siswa, name='detail_tugas_siswa'),

    # =========================================================================
    # 6. STANDALONE PAGES SISWA
    # =========================================================================
    path('siswa/jadwal/',       views.jadwal_siswa,       name='jadwal_siswa'),
    path('siswa/presensi/',     views.presensi_siswa,     name='presensi_siswa'),
    path('siswa/e-learning/',   views.elearning_siswa,    name='elearning_siswa'),
    path('siswa/hasil-studi/',  views.hasil_studi_siswa,  name='hasil_studi_siswa'),
    path('siswa/lihat-materi/', views.lihat_materi_siswa, name='lihat_materi_siswa'),
    path('siswa/update-foto/',  views.update_foto_siswa,  name='update_foto_siswa'),

    # =========================================================================
    # 7. AUTHENTICATION
    # =========================================================================
    path('logout/',              views.logout_view,         name='logout'),
    path('siswa/ubah-password/', views.ubah_password_siswa, name='ubah_password'),

    # =========================================================================
    # 8. API MODAL POP-UP SISWA
    # =========================================================================
    path('api/jadwal/',    views.api_jadwal_siswa,    name='api_jadwal_siswa'),
    path('api/presensi/',  views.api_presensi_siswa,  name='api_presensi_siswa'),
    path('api/nilai/',     views.api_nilai_siswa,     name='api_nilai_siswa'),
    path('api/elearning/', views.api_elearning_siswa, name='api_elearning_siswa'),
    path('api/keuangan/',  views.api_keuangan_siswa,  name='api_keuangan_siswa'),
    path('manajemen-keuangan/', core_views.manajemen_keuangan, name='manajemen_keuangan'),
    path('elearning/jawaban/<int:tugas_id>/', views.lihat_jawaban_guru, name='lihat_jawaban_guru'),

    # =========================================================================
    # 9. EXPORT PDF & EXCEL
    # =========================================================================
    path('export/rapor/<int:siswa_id>/', views_export.export_rapor_pdf, name='export_rapor_pdf'),
    path('lihat/rapor/<int:siswa_id>/', views_export.lihat_rapor_siswa, name='lihat_rapor_siswa'),
    path('export/nilai/<int:siswa_id>/', views_export.export_nilai_excel, name='export_nilai_excel'),
    path('export/semua-siswa/', views_export.export_semua_siswa_excel, name='export_semua_siswa'),
]