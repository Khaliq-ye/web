# akademik/admin.py
from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import (
    MataPelajaran,
    JadwalPelajaran,
    JurnalMengajar,
    MateriAjar,
    Presensi,
    TugasKuis,
    NilaiRapor,
    SambutanKepsek,
)


# =========================================================================
# HELPER
# =========================================================================
class SingleSambutanAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)


# =========================================================================
# FORM VALIDASI KONFLIK JADWAL
# =========================================================================
class JadwalPelajaranForm(forms.ModelForm):
    """
    Form kustom untuk JadwalPelajaran.
    Validasi dijalankan saat admin menyimpan jadwal baru maupun mengedit.
    Tiga jenis konflik dicek:
      1. Guru mengajar 2 kelas berbeda di hari & jam yang tumpang tindih
      2. Kelas mendapat 2 pelajaran di hari & jam yang tumpang tindih
      3. Ruangan dipakai 2 kelas di hari & jam yang tumpang tindih
    """
    class Meta:
        model  = JadwalPelajaran
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()

        hari        = cleaned.get('hari')
        jam_mulai   = cleaned.get('jam_mulai')
        jam_selesai = cleaned.get('jam_selesai')
        guru        = cleaned.get('guru')
        kelas       = cleaned.get('kelas')
        ruangan     = cleaned.get('ruangan')

        # Jika field wajib belum terisi, biarkan validasi bawaan Django bekerja
        if not all([hari, jam_mulai, jam_selesai, guru, kelas]):
            return cleaned

        # Validasi logika waktu
        if jam_mulai >= jam_selesai:
            raise ValidationError(
                'Jam mulai harus lebih awal dari jam selesai.'
            )

        # QuerySet dasar — semua jadwal di hari yang sama,
        # kecuali record yang sedang diedit (instance.pk)
        qs_hari = JadwalPelajaran.objects.filter(hari=hari)
        if self.instance.pk:
            qs_hari = qs_hari.exclude(pk=self.instance.pk)

        # Filter waktu tumpang tindih:
        # Tumpang tindih terjadi jika:
        #   jam_mulai_baru  < jam_selesai_lama   DAN
        #   jam_selesai_baru > jam_mulai_lama
        qs_tumpang = qs_hari.filter(
            jam_mulai__lt=jam_selesai,
            jam_selesai__gt=jam_mulai,
        )

        # ── 1. Konflik Guru ──────────────────────────────────────────────
        konflik_guru = qs_tumpang.filter(guru=guru).select_related(
            'kelas', 'mata_pelajaran'
        ).first()
        if konflik_guru:
            raise ValidationError(
                format_html(
                    '<strong>⚠ Konflik Jadwal Guru!</strong><br>'
                    'Guru <strong>{}</strong> sudah terjadwal mengajar '
                    '<strong>{}</strong> di kelas <strong>{}</strong> '
                    'pada hari <strong>{}</strong> pukul '
                    '<strong>{} – {}</strong>. '
                    'Harap pilih jam atau hari yang berbeda.',
                    guru.nama_lengkap,
                    konflik_guru.mata_pelajaran.nama,
                    konflik_guru.kelas.nama_kelas,
                    konflik_guru.hari,
                    konflik_guru.jam_mulai.strftime('%H:%M'),
                    konflik_guru.jam_selesai.strftime('%H:%M'),
                )
            )

        # ── 2. Konflik Kelas ─────────────────────────────────────────────
        konflik_kelas = qs_tumpang.filter(kelas=kelas).select_related(
            'guru', 'mata_pelajaran'
        ).first()
        if konflik_kelas:
            raise ValidationError(
                format_html(
                    '<strong>⚠ Konflik Jadwal Kelas!</strong><br>'
                    'Kelas <strong>{}</strong> sudah memiliki pelajaran '
                    '<strong>{}</strong> (oleh <strong>{}</strong>) '
                    'pada hari <strong>{}</strong> pukul '
                    '<strong>{} – {}</strong>. '
                    'Jadwal tidak boleh tumpang tindih.',
                    kelas.nama_kelas,
                    konflik_kelas.mata_pelajaran.nama,
                    konflik_kelas.guru.nama_lengkap,
                    konflik_kelas.hari,
                    konflik_kelas.jam_mulai.strftime('%H:%M'),
                    konflik_kelas.jam_selesai.strftime('%H:%M'),
                )
            )

        # ── 3. Konflik Ruangan ───────────────────────────────────────────
        if ruangan and ruangan.strip():
            konflik_ruangan = qs_tumpang.filter(
                ruangan__iexact=ruangan.strip()
            ).select_related('guru', 'kelas', 'mata_pelajaran').first()
            if konflik_ruangan:
                raise ValidationError(
                    format_html(
                        '<strong>⚠ Konflik Ruangan!</strong><br>'
                        'Ruangan <strong>{}</strong> sudah digunakan untuk '
                        '<strong>{}</strong> kelas <strong>{}</strong> '
                        '(oleh <strong>{}</strong>) '
                        'pada hari <strong>{}</strong> pukul '
                        '<strong>{} – {}</strong>.',
                        ruangan,
                        konflik_ruangan.mata_pelajaran.nama,
                        konflik_ruangan.kelas.nama_kelas,
                        konflik_ruangan.guru.nama_lengkap,
                        konflik_ruangan.hari,
                        konflik_ruangan.jam_mulai.strftime('%H:%M'),
                        konflik_ruangan.jam_selesai.strftime('%H:%M'),
                    )
                )

        return cleaned


# =========================================================================
# ADMIN REGISTRATIONS
# =========================================================================

@admin.register(SambutanKepsek)
class SambutanKepsekAdmin(SingleSambutanAdmin):
    list_display  = ('get_nama_kepsek', 'created_at', 'updated_at')
    search_fields = ('kepala_sekolah__nama_lengkap',)

    def get_nama_kepsek(self, obj):
        return obj.kepala_sekolah.nama_lengkap
    get_nama_kepsek.short_description = 'Nama Kepala Sekolah'


@admin.register(MataPelajaran)
class MataPelajaranAdmin(admin.ModelAdmin):
    list_display  = ('kode', 'nama')
    search_fields = ('kode', 'nama')
    ordering      = ('kode',)


@admin.register(JadwalPelajaran)
class JadwalAdmin(admin.ModelAdmin):
    form          = JadwalPelajaranForm          # ← pakai form validasi konflik
    list_display  = (
        'hari', 'kelas', 'mata_pelajaran', 'guru',
        'jam_mulai', 'jam_selesai', 'ruangan', 'status_konflik'
    )
    list_filter   = ('hari', 'kelas')
    search_fields = (
        'mata_pelajaran__nama',
        'guru__nama_lengkap',
        'kelas__nama_kelas',
    )
    ordering            = ('hari', 'jam_mulai')
    autocomplete_fields = ('kelas', 'guru', 'mata_pelajaran')

    def status_konflik(self, obj):
        if not obj.jam_mulai or not obj.jam_selesai or not obj.hari:
            return format_html('<span style="color:gray;">{}</span>', '—')

        konflik = JadwalPelajaran.objects.filter(
            hari=obj.hari,
            jam_mulai__lt=obj.jam_selesai,
            jam_selesai__gt=obj.jam_mulai,
        ).exclude(pk=obj.pk)

        ada_konflik_guru    = konflik.filter(guru=obj.guru).exists()
        ada_konflik_kelas   = konflik.filter(kelas=obj.kelas).exists()
        ada_konflik_ruangan = (
            konflik.filter(ruangan__iexact=obj.ruangan).exists()
            if obj.ruangan and obj.ruangan.strip()
            else False
        )

        if ada_konflik_guru or ada_konflik_kelas or ada_konflik_ruangan:
            pesan = []
            if ada_konflik_guru:
                pesan.append('Konflik Guru')
            if ada_konflik_kelas:
                pesan.append('Konflik Kelas')
            if ada_konflik_ruangan:
                pesan.append('Konflik Ruangan')
            label = ' | '.join(pesan)
            return format_html(
                '<span style="color:#dc2626;font-weight:700;" title="{0}">⚠ {1}</span>',
                label,
                label,
            )

        return format_html(
            '<span style="color:#16a34a;font-weight:600;">{}</span>',
            '✅ Aman',
        )

    status_konflik.short_description = 'Status Konflik'


@admin.register(JurnalMengajar)
class JurnalMengajarAdmin(admin.ModelAdmin):
    list_display  = ('tanggal', 'get_kelas', 'get_mapel', 'materi_pembahasan')
    list_filter   = ('tanggal',)
    search_fields = ('jadwal__mata_pelajaran__nama', 'jadwal__guru__nama_lengkap')
    ordering      = ('-tanggal',)

    def get_kelas(self, obj):
        return obj.jadwal.kelas.nama_kelas
    get_kelas.short_description = 'Kelas'

    def get_mapel(self, obj):
        return obj.jadwal.mata_pelajaran.nama
    get_mapel.short_description = 'Mata Pelajaran'


@admin.register(MateriAjar)
class MateriAjarAdmin(admin.ModelAdmin):
    list_display  = ('judul', 'mata_pelajaran', 'guru', 'created_at')
    list_filter   = ('mata_pelajaran',)
    search_fields = ('judul', 'guru__nama_lengkap', 'mata_pelajaran__nama')
    ordering      = ('-created_at',)


@admin.register(Presensi)
class PresensiAdmin(admin.ModelAdmin):
    list_display  = ('tanggal', 'siswa', 'status', 'keterangan')
    list_filter   = ('status', 'tanggal')
    search_fields = ('siswa__nama_lengkap',)
    ordering      = ('-tanggal',)


@admin.register(TugasKuis)
class TugasKuisAdmin(admin.ModelAdmin):
    list_display  = (
        'judul', 'jenis', 'mata_pelajaran',
        'get_kelas', 'guru', 'batas_waktu'
    )
    list_filter   = ('jenis', 'mata_pelajaran')
    search_fields = ('judul', 'guru__nama_lengkap', 'mata_pelajaran__nama')
    ordering      = ('-created_at',)

    def get_kelas(self, obj):
        return obj.jadwal.kelas.nama_kelas if obj.jadwal else '—'
    get_kelas.short_description = 'Kelas'


@admin.register(NilaiRapor)
class NilaiAdmin(admin.ModelAdmin):
    list_display  = (
        'siswa', 'mata_pelajaran',
        'nilai_tugas', 'nilai_uts', 'nilai_uas', 'nilai_angka'
    )
    list_filter   = ('mata_pelajaran',)
    search_fields = ('siswa__nama_lengkap', 'mata_pelajaran__nama')