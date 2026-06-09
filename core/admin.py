from django.contrib import admin
from .models import Guru, Kelas, Siswa, KeuanganSiswa, KepalaSekolah, Staf, WaliMurid

# =========================================================================
#  --- HELPER CLASS ANTI-DUPLIKASI CORE ---
# =========================================================================
class SingleObjectAdmin(admin.ModelAdmin):
    """ Mencegah tombol 'Add' muncul jika akun Utama Kepala Sekolah sudah dibuat """
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


# =========================================================================
#  --- REGISTRASI MODEL CORE ---
# =========================================================================

@admin.register(KepalaSekolah)
class KepalaSekolahAdmin(SingleObjectAdmin):  # Menggunakan helper anti-duplikasi aktor login
    list_display = ('nip', 'nama_lengkap', 'get_username', 'no_hp')
    search_fields = ('nip', 'nama_lengkap', 'user__username')

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username Login'


@admin.register(Guru)
class GuruAdmin(admin.ModelAdmin):
    list_display = ('nip', 'nama_lengkap', 'bidang_studi', 'get_username')
    search_fields = ('nip', 'nama_lengkap', 'user__username')

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username Login'


@admin.register(Staf)
class StafAdmin(admin.ModelAdmin):
    list_display = ('nip', 'nama_lengkap', 'get_username', 'no_hp')
    search_fields = ('nip', 'nama_lengkap', 'user__username')

    def get_username(self, obj):
        return obj.user.username if obj.user else '-'
    get_username.short_description = 'Username Login'


@admin.register(WaliMurid)
class WaliMuridAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_username', 'get_nama_wali')
    search_fields = ('user__username',)

    def get_username(self, obj):
        return obj.user.username if obj.user else '-'
    get_username.short_description = 'Username Login'

    def get_nama_wali(self, obj):
        if hasattr(obj, 'nama_wali'):
            return obj.nama_wali
        elif hasattr(obj, 'nama_lengkap'):
            return obj.nama_lengkap
        return '-'
    get_nama_wali.short_description = 'Nama Wali'


@admin.register(Siswa)
class SiswaAdmin(admin.ModelAdmin):
    list_display = ('nisn', 'nama_lengkap', 'get_username', 'wali')
    search_fields = ('nisn', 'nama_lengkap', 'user__username', 'wali__nama_wali')

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Username Login'


@admin.register(Kelas)
class KelasAdmin(admin.ModelAdmin):
    list_display = ('nama_kelas', 'wali_kelas')
    search_fields = ('nama_kelas',)


@admin.register(KeuanganSiswa)
class KeuanganAdmin(admin.ModelAdmin):
    list_display = ('siswa', 'jenis_tagihan', 'jumlah', 'status_lunas', 'tanggal_tagihan')
    list_filter = ('status_lunas', 'jenis_tagihan', 'tanggal_tagihan')
    search_fields = ('siswa__nama_lengkap', 'jenis_tagihan')