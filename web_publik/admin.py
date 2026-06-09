import sys

from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin
from django.db import transaction, connection
from django.utils.html import format_html

# Model web_publik
# Catatan: JadwalPelajaran (web_publik) TIDAK didaftarkan di sini.
# Model itu hanya menyimpan data statis info kurikulum publik (nama mapel,
# alokasi waktu, ruangan per jurusan) untuk halaman /akademik-info/.
# Jadwal mengajar operasional guru ada di akademik.JadwalPelajaran.
from .models import (
    StatistikSekolah,
    Pengumuman,
    Agenda,
    Berita,
    Pendaftaran,
    KepalaSekolah,
    PpdbSetting,
    PpdbGelombang,
    Prestasi,
    Galeri,
    DokumenUnduhan,
    LayananAkademik,
    KontakSekolah,
    Ekstrakurikuler,
    JadwalPelajaran,
)


# ---------------------------------------------------------------------------
# Helper: Singleton — cegah data konfigurasi ganda
# ---------------------------------------------------------------------------
class SingleObjectAdmin(admin.ModelAdmin):
    """Sembunyikan tombol 'Add' jika data konfigurasi tunggal sudah ada."""

    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------
admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'get_groups', 'is_staff', 'is_active')
    list_filter  = ('groups', 'is_staff', 'is_active')

    def get_groups(self, obj):
        return ", ".join([g.name for g in obj.groups.all()])
    get_groups.short_description = 'Roles/Groups'


# ---------------------------------------------------------------------------
# StatistikSekolah
# ---------------------------------------------------------------------------
@admin.register(StatistikSekolah)
class StatistikAdmin(SingleObjectAdmin):
    list_display = ('nama_studi', 'total_siswa', 'total_guru', 'total_kelas', 'total_mapel')


# ---------------------------------------------------------------------------
# Pengumuman
# ---------------------------------------------------------------------------
@admin.register(Pengumuman)
class PengumumanAdmin(admin.ModelAdmin):
    list_display        = ('judul', 'tanggal', 'is_active')
    list_filter         = ('is_active', 'tanggal')
    search_fields       = ('judul', 'isi')
    date_hierarchy      = 'tanggal'
    prepopulated_fields = {'slug': ('judul',)}


# ---------------------------------------------------------------------------
# Agenda
# ---------------------------------------------------------------------------
@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display  = ('nama_kegiatan', 'tanggal', 'waktu', 'lokasi')
    list_filter   = ('tanggal',)
    search_fields = ('nama_kegiatan', 'lokasi')


# ---------------------------------------------------------------------------
# Berita
# ---------------------------------------------------------------------------
@admin.register(Berita)
class BeritaAdmin(admin.ModelAdmin):
    list_display  = ('judul', 'tanggal_post', 'penulis', 'display_image')
    list_filter   = ('tanggal_post', 'penulis')
    search_fields = ('judul', 'keterangan')

    def display_image(self, obj):
        if obj.gambar:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />',
                obj.gambar.url,
            )
        return '—'
    display_image.short_description = 'Preview'


# ---------------------------------------------------------------------------
# Pendaftaran (PPDB)
# ---------------------------------------------------------------------------
@admin.register(Pendaftaran)
class PendaftaranAdmin(admin.ModelAdmin):
    list_display  = ('nama_lengkap', 'nisn', 'colored_status', 'created_at')
    list_filter   = ('status', 'created_at', 'asal_sekolah')
    search_fields = ('nama_lengkap', 'nisn', 'asal_sekolah')
    actions       = ['terima_dan_buat_akun', 'tolak_pendaftaran']

    fieldsets = (
        ('Informasi Pribadi', {
            'fields': ('nama_lengkap', 'nisn', 'asal_sekolah'),
        }),
        ('Kontak', {
            'fields': ('email', 'nomor_hp'),
        }),
        ('Status Verifikasi', {
            'fields': ('status', 'user'),
        }),
    )

    def colored_status(self, obj):
        warna = {'pending': '#f39c12', 'diterima': '#27ae60', 'ditolak': '#e74c3c'}
        return format_html(
            '<span style="color:white;background:{};padding:3px 10px;'
            'border-radius:12px;font-weight:bold;font-size:11px;">{}</span>',
            warna.get(obj.status, '#7f8c8d'),
            obj.get_status_display(),
        )
    colored_status.short_description = 'Status'

    @admin.action(description='✅ Terima & Aktivasi Akun Siswa')
    def terima_dan_buat_akun(self, request, queryset):
        count   = 0
        skipped = 0

        for pendaftar in queryset:
            if pendaftar.status == 'diterima':
                continue
            try:
                with transaction.atomic():
                    user, created = User.objects.get_or_create(
                        username=pendaftar.nisn,
                        defaults={
                            'email': pendaftar.email,
                            'first_name': pendaftar.nama_lengkap,
                            'is_active': True,
                        },
                    )
                    if not created:
                        user.email      = pendaftar.email
                        user.first_name = pendaftar.nama_lengkap
                        user.is_active  = True
                        user.save()
                    else:
                        user.set_password(pendaftar.nisn)
                        user.save()

                    group, _ = Group.objects.get_or_create(name='Siswa')
                    user.groups.add(group)

                    with connection.cursor() as cursor:
                        cursor.execute(
                            'SELECT id FROM core_siswa WHERE user_id = %s', [user.id]
                        )
                        row = cursor.fetchone()

                        if row:
                            cursor.execute(
                                'UPDATE core_siswa SET nisn=%s, nama_lengkap=%s, kelas_id=1 WHERE user_id=%s',
                                [pendaftar.nisn, pendaftar.nama_lengkap, user.id],
                            )
                        else:
                            cursor.execute(
                                'INSERT INTO core_siswa (nisn, nama_lengkap, user_id, kelas_id) VALUES (%s,%s,%s,1)',
                                [pendaftar.nisn, pendaftar.nama_lengkap, user.id],
                            )

                    pendaftar.status = 'diterima'
                    pendaftar.user   = user
                    pendaftar.save()
                    count += 1

            except Exception:
                _, error_msg, _ = sys.exc_info()
                self.message_user(
                    request,
                    f'🚨 Gagal memproses [{pendaftar.nama_lengkap}]. Error: {error_msg}',
                    level='ERROR',
                )
                skipped += 1

        if count:
            self.message_user(request, f'Sukses: {count} siswa berhasil diaktifkan.')
        if skipped:
            self.message_user(request, f'Peringatan: {skipped} data gagal diproses.', level='WARNING')

    @admin.action(description='❌ Tolak Pendaftaran Terpilih')
    def tolak_pendaftaran(self, request, queryset):
        rows = queryset.update(status='ditolak')
        self.message_user(request, f'{rows} pendaftaran telah ditolak.')


# ---------------------------------------------------------------------------
# KepalaSekolah (profil untuk halaman publik /profil/)
# ---------------------------------------------------------------------------
@admin.register(KepalaSekolah)
class KepalaSekolahAdmin(SingleObjectAdmin):
    list_display = ('nama', 'created_at')


# ---------------------------------------------------------------------------
# PpdbSetting
# ---------------------------------------------------------------------------
@admin.register(PpdbSetting)
class PpdbSettingAdmin(SingleObjectAdmin):
    list_display = ('__str__', 'brosur_pdf', 'updated_at')


# ---------------------------------------------------------------------------
# PpdbGelombang
# ---------------------------------------------------------------------------
@admin.register(PpdbGelombang)
class PpdbGelombangAdmin(admin.ModelAdmin):
    list_display  = ('nama', 'tanggal_mulai', 'tanggal_selesai', 'biaya', 'is_aktif')
    list_filter   = ('is_aktif',)
    search_fields = ('nama',)


# ---------------------------------------------------------------------------
# Prestasi
# ---------------------------------------------------------------------------
@admin.register(Prestasi)
class PrestasiAdmin(admin.ModelAdmin):
    list_display  = ('juara', 'nama_lomba', 'nama_siswa', 'tingkat')
    list_filter   = ('tingkat',)
    search_fields = ('nama_lomba', 'nama_siswa')


# ---------------------------------------------------------------------------
# Galeri
# ---------------------------------------------------------------------------
@admin.register(Galeri)
class GaleriAdmin(admin.ModelAdmin):
    list_display  = ('judul', 'kategori', 'tanggal_kegiatan')
    list_filter   = ('kategori', 'tanggal_kegiatan')
    search_fields = ('judul',)


# ---------------------------------------------------------------------------
# DokumenUnduhan
# ---------------------------------------------------------------------------
@admin.register(DokumenUnduhan)
class DokumenUnduhanAdmin(admin.ModelAdmin):
    list_display  = ('nama_dokumen', 'file')
    search_fields = ('nama_dokumen',)

# ============================================================
# TAMBAHKAN IMPORT INI ke baris import model di admin.py
# (tambahkan LayananAkademik, KontakSekolah, Ekstrakurikuler
#  ke dalam blok import from .models import ...)
# ============================================================

# Contoh import lengkap setelah ditambah:
# from .models import (
#     StatistikSekolah, Pengumuman, Agenda, Berita, Pendaftaran,
#     KepalaSekolah, PpdbSetting, PpdbGelombang, Prestasi,
#     Galeri, DokumenUnduhan,
#     LayananAkademik, KontakSekolah, Ekstrakurikuler,   # <-- TAMBAHAN
# )

# ============================================================
# TAMBAHKAN 3 BLOK ADMIN INI KE BAGIAN BAWAH admin.py
# (setelah @admin.register(DokumenUnduhan))
# ============================================================


# ---------------------------------------------------------------------------
# LayananAkademik — Program & Fasilitas (profil.html)
# ---------------------------------------------------------------------------
@admin.register(LayananAkademik)
class LayananAkademikAdmin(admin.ModelAdmin):
    list_display  = ('nama', 'jenis', 'urutan')
    list_filter   = ('jenis',)
    search_fields = ('nama', 'deskripsi')
    list_editable = ('urutan',)
    ordering      = ('jenis', 'urutan')


# ---------------------------------------------------------------------------
# KontakSekolah — Sidebar kontak (profil.html)
# ---------------------------------------------------------------------------
@admin.register(KontakSekolah)
class KontakSekolahAdmin(SingleObjectAdmin):
    """Singleton — hanya boleh 1 baris kontak resmi."""
    list_display = ('telepon', 'email', 'website')


# ---------------------------------------------------------------------------
# Ekstrakurikuler — Halaman akademik.html
# ---------------------------------------------------------------------------
@admin.register(Ekstrakurikuler)
class EkstrakurikulerAdmin(admin.ModelAdmin):
    list_display  = ('nama', 'icon', 'urutan', 'is_aktif')
    list_filter   = ('is_aktif',)
    search_fields = ('nama', 'deskripsi')
    list_editable = ('urutan', 'is_aktif')
    ordering      = ('urutan', 'nama')

@admin.register(JadwalPelajaran)
class JadwalPelajaranAdmin(admin.ModelAdmin):
    list_display  = ('program_keahlian', 'mata_pelajaran', 'alokasi_waktu', 'ruangan')
    list_filter   = ('program_keahlian',)
    search_fields = ('mata_pelajaran', 'ruangan')
    list_editable = ('alokasi_waktu', 'ruangan')