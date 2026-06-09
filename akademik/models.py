from django.db import models
from django.contrib.auth.models import User
from core.models import Guru, Siswa, Kelas, KepalaSekolah as CoreKepalaSekolah


# =========================================================================
# 1. MODUL MATA PELAJARAN
# =========================================================================
class MataPelajaran(models.Model):
    nama = models.CharField(max_length=100)
    kode = models.CharField(max_length=10, unique=True)

    class Meta:
        verbose_name = "Mata Pelajaran"
        verbose_name_plural = "Mata Pelajaran"

    def __str__(self):
        return f"{self.kode} - {self.nama}"


# =========================================================================
# 2. MODUL JADWAL & AGENDA MENGAJAR
# =========================================================================
class JadwalPelajaran(models.Model):
    HARI_CHOICES = [
        ('Senin',  'Senin'),
        ('Selasa', 'Selasa'),
        ('Rabu',   'Rabu'),
        ('Kamis',  'Kamis'),
        ('Jumat',  'Jumat'),
        ('Sabtu',  'Sabtu'),
    ]

    mata_pelajaran = models.ForeignKey(
        MataPelajaran, on_delete=models.CASCADE, related_name='jadwal_pelajaran'
    )
    guru = models.ForeignKey(
        Guru, on_delete=models.CASCADE, related_name='jadwal_guru'
    )
    kelas = models.ForeignKey(
        Kelas,
        on_delete=models.CASCADE,
        related_name='jadwal_kelas',
        verbose_name='Kelas',
    )
    hari        = models.CharField(max_length=20, choices=HARI_CHOICES)
    jam_mulai   = models.TimeField()
    jam_selesai = models.TimeField()
    ruangan     = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Jadwal Pelajaran"
        verbose_name_plural = "Jadwal Pelajaran"

    def __str__(self):
        return f"{self.hari} ({self.kelas.nama_kelas}) - {self.mata_pelajaran.nama}"


# =========================================================================
# 3. MODUL JURNAL MENGAJAR
# =========================================================================
class JurnalMengajar(models.Model):
    jadwal = models.ForeignKey(
        JadwalPelajaran, on_delete=models.CASCADE, related_name='jurnal_jadwal'
    )
    tanggal           = models.DateField(auto_now_add=True)
    materi_pembahasan = models.TextField(help_text="Tuliskan ringkasan materi yang diajarkan")
    kendala_kbm       = models.TextField(blank=True, null=True)
    tindak_lanjut     = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Jurnal Mengajar"
        verbose_name_plural = "Jurnal Mengajar"

    def __str__(self):
        return (
            f"{self.tanggal} - {self.jadwal.mata_pelajaran.nama}"
            f" ({self.jadwal.kelas.nama_kelas})"
        )


# =========================================================================
# 4. MODUL MATERI AJAR & SILABUS
# =========================================================================
class MateriAjar(models.Model):
    mata_pelajaran = models.ForeignKey(MataPelajaran, on_delete=models.CASCADE)
    guru           = models.ForeignKey(Guru, on_delete=models.CASCADE)
    judul          = models.CharField(max_length=200)
    deskripsi      = models.TextField(blank=True, null=True)
    file_materi    = models.FileField(upload_to='materi_ajar/', blank=True, null=True)
    link_external  = models.URLField(blank=True, null=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Materi Ajar"
        verbose_name_plural = "Materi Ajar"

    def __str__(self):
        return f"{self.judul} - {self.mata_pelajaran.nama}"


# =========================================================================
# 5. MODUL PRESENSI / ABSENSI SISWA
# =========================================================================
class Presensi(models.Model):
    STATUS_CHOICES = [
        ('Hadir', 'Hadir'),
        ('Izin',  'Izin'),
        ('Sakit', 'Sakit'),
        ('Alpa',  'Alpa'),
    ]

    siswa      = models.ForeignKey(
        Siswa, on_delete=models.CASCADE, related_name='presensi_siswa'
    )
    jadwal     = models.ForeignKey(
        JadwalPelajaran, on_delete=models.CASCADE, null=True, blank=True
    )
    tanggal    = models.DateField()
    status     = models.CharField(max_length=20, choices=STATUS_CHOICES)
    keterangan = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Presensi"
        verbose_name_plural = "Presensi"

    def __str__(self):
        return f"{self.tanggal} - {self.siswa.nama_lengkap} ({self.status})"


# =========================================================================
# 6. MODUL E-LEARNING / TUGAS & KUIS
# =========================================================================
class TugasKuis(models.Model):
    JENIS_CHOICES = [
        ('Tugas', 'Tugas Harian'),
        ('Kuis',  'Kuis Online'),
    ]

    jadwal         = models.ForeignKey(
        JadwalPelajaran, on_delete=models.CASCADE,
        related_name='tugas_kelas', null=True, blank=True
    )
    mata_pelajaran = models.ForeignKey(MataPelajaran, on_delete=models.CASCADE)
    guru           = models.ForeignKey(Guru, on_delete=models.CASCADE)
    judul          = models.CharField(max_length=200)
    jenis          = models.CharField(max_length=10, choices=JENIS_CHOICES)
    deskripsi      = models.TextField(blank=True, null=True)
    batas_waktu    = models.DateTimeField(help_text="Deadline pengumpulan")
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tugas & Kuis"
        verbose_name_plural = "Tugas & Kuis"

    def __str__(self):
        return f"[{self.jenis}] {self.judul} - {self.mata_pelajaran.nama}"


# =========================================================================
# 6b. JAWABAN SISWA — pengumpulan file per tugas
# =========================================================================
class JawabanSiswa(models.Model):
    tugas         = models.ForeignKey(
        TugasKuis, on_delete=models.CASCADE, related_name='jawaban_siswa'
    )
    siswa         = models.ForeignKey(
        Siswa, on_delete=models.CASCADE, related_name='jawaban_tugas'
    )
    file_jawaban  = models.FileField(upload_to='jawaban_siswa/%Y/%m/')
    catatan       = models.TextField(blank=True, null=True)
    dikirim_at    = models.DateTimeField(auto_now_add=True)
    diperbarui_at = models.DateTimeField(auto_now=True)
    nilai         = models.IntegerField(
        null=True, blank=True,
        help_text="Nilai yang diberikan guru (0-100)"
    )
    catatan_guru  = models.TextField(
        blank=True, null=True,
        help_text="Catatan / feedback dari guru"
    )

    class Meta:
        verbose_name        = "Jawaban Siswa"
        verbose_name_plural = "Jawaban Siswa"
        unique_together     = ('tugas', 'siswa')
        ordering            = ['-dikirim_at']

    def __str__(self):
        return f"{self.siswa.nama_lengkap} -> {self.tugas.judul}"

    @property
    def nama_file(self):
        import os
        return os.path.basename(self.file_jawaban.name) if self.file_jawaban else ''

    @property
    def ekstensi(self):
        import os
        _, ext = os.path.splitext(self.file_jawaban.name)
        return ext.lstrip('.').upper() if ext else '-'


# =========================================================================
# 6c. NILAI PERILAKU SISWA PER SESI MENGAJAR
#
#     Setiap guru mengisi nilai perilaku siswa saat mengajar.
#     Kategori: Baik=100, Cukup=70, Kurang=30
#     Nilai perilaku akhir siswa = rata-rata semua penilaian dari semua guru.
#     Kontribusi ke nilai akhir rapor = 15%.
# =========================================================================
class NilaiPerilaku(models.Model):
    KATEGORI_CHOICES = [
        ('Baik',   'Baik'),
        ('Cukup',  'Cukup'),
        ('Kurang', 'Kurang'),
    ]

    SKOR_MAP = {
        'Baik':   100,
        'Cukup':  70,
        'Kurang': 30,
    }

    siswa    = models.ForeignKey(
        Siswa, on_delete=models.CASCADE, related_name='nilai_perilaku'
    )
    guru     = models.ForeignKey(
        Guru, on_delete=models.CASCADE, related_name='penilaian_perilaku'
    )
    jadwal   = models.ForeignKey(
        JadwalPelajaran, on_delete=models.CASCADE,
        related_name='perilaku_jadwal',
        null=True, blank=True
    )
    tanggal  = models.DateField(help_text="Tanggal sesi mengajar")
    kategori = models.CharField(
        max_length=10, choices=KATEGORI_CHOICES,
        help_text="Penilaian perilaku siswa pada sesi ini"
    )
    catatan  = models.CharField(
        max_length=255, blank=True, null=True,
        help_text="Catatan singkat opsional dari guru"
    )

    class Meta:
        verbose_name        = "Nilai Perilaku Siswa"
        verbose_name_plural = "Nilai Perilaku Siswa"
        ordering            = ['-tanggal']
        # Satu guru hanya bisa memberi 1 penilaian per siswa per jadwal per hari
        unique_together     = ('siswa', 'guru', 'jadwal', 'tanggal')

    def __str__(self):
        return (
            f"{self.tanggal} | {self.siswa.nama_lengkap}"
            f" | {self.guru.nama_lengkap} | {self.kategori}"
        )

    @property
    def skor(self):
        """Konversi kategori ke angka: Baik=100, Cukup=70, Kurang=30."""
        return self.SKOR_MAP.get(self.kategori, 0)


# =========================================================================
# 7. MODUL NILAI RAPOR DIGITAL
#
#     Formula nilai akhir (nilai_angka):
#     nilai_angka = (tugas*0.35) + (uts*0.25) + (uas*0.25) + (perilaku*0.15)
#
#     nilai_perilaku diambil dari rata-rata NilaiPerilaku siswa
#     dan disimpan di field nilai_perilaku saat guru input nilai.
# =========================================================================
class NilaiRapor(models.Model):
    siswa          = models.ForeignKey(Siswa, on_delete=models.CASCADE)
    mata_pelajaran = models.ForeignKey(MataPelajaran, on_delete=models.CASCADE)
    nilai_tugas    = models.IntegerField(default=0)
    nilai_uts      = models.IntegerField(default=0)
    nilai_uas      = models.IntegerField(default=0)
    # Nilai perilaku global siswa (rata-rata semua NilaiPerilaku),
    # disalin ke sini saat guru menyimpan nilai agar konsisten di rapor.
    nilai_perilaku = models.IntegerField(
        default=0,
        help_text="Rata-rata nilai perilaku siswa dari semua guru (0-100)"
    )
    nilai_angka    = models.IntegerField(
        default=0,
        help_text=(
            "Nilai Akhir = (tugas*35%) + (uts*25%) + (uas*25%) + (perilaku*15%)"
        )
    )
    keterangan     = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Nilai Rapor"
        verbose_name_plural = "Nilai Rapor"

    def __str__(self):
        return (
            f"{self.siswa.nama_lengkap} - {self.mata_pelajaran.nama}"
            f" ({self.nilai_angka})"
        )

    def hitung_nilai_angka(self):
        """
        Hitung ulang nilai_angka berdasarkan komponen yang tersimpan.
        Panggil metode ini sebelum save() jika ingin sinkron otomatis.
        """
        return int(
            (self.nilai_tugas * 0.35)
            + (self.nilai_uts * 0.25)
            + (self.nilai_uas * 0.25)
            + (self.nilai_perilaku * 0.15)
        )


# =========================================================================
# 8. MODUL PROFIL KEPALA SEKOLAH
# =========================================================================
class KepalaSekolahProfile(models.Model):
    user         = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='kepala_sekolah_profile'
    )
    nama_lengkap = models.CharField(max_length=150)
    nip          = models.CharField(max_length=30, blank=True, null=True)
    bio          = models.TextField(blank=True, null=True)
    foto_kepsek  = models.ImageField(upload_to='profil_kepsek/', blank=True, null=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Kepala Sekolah"
        verbose_name_plural = "Profil Kepala Sekolah"

    def __str__(self):
        return f"Profil: {self.nama_lengkap or self.user.username}"


class SambutanKepsek(models.Model):
    kepala_sekolah = models.OneToOneField(
        CoreKepalaSekolah, on_delete=models.CASCADE,
        related_name='sambutan_profile', verbose_name="Kepala Sekolah"
    )
    sambutan   = models.TextField()
    foto       = models.ImageField(upload_to='kepsek/', blank=True, null=True)
    ttd        = models.ImageField(upload_to='kepsek/ttd/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sambutan Kepala Sekolah"
        verbose_name_plural = "Sambutan Kepala Sekolah"

    def __str__(self):
        return self.kepala_sekolah.nama_lengkap


# =========================================================================
# 9. MODUL PROFIL STAFF TATA USAHA
# =========================================================================
class StaffProfile(models.Model):
    JABATAN_CHOICES = [
        ('Kaur Tata Usaha',    'Kepala Urusan Tata Usaha'),
        ('Staff Administrasi', 'Staff Administrasi Siswa'),
        ('Staff Kepegawaian',  'Staff Administrasi Kepegawaian'),
        ('Operator Dapodik',   'Operator Sistem / Dapodik'),
    ]

    user         = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='staf_profile'
    )
    nama_lengkap = models.CharField(max_length=150)
    nip          = models.CharField(max_length=30, blank=True, null=True)
    jabatan      = models.CharField(
        max_length=50, choices=JABATAN_CHOICES, default='Staff Administrasi'
    )
    no_telepon   = models.CharField(max_length=15, blank=True, null=True)
    foto_staf    = models.ImageField(upload_to='profil_staf/', blank=True, null=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil Staff Tata Usaha"
        verbose_name_plural = "Profil Staff Tata Usaha"

    def __str__(self):
        return f"{self.nama_lengkap} - {self.get_jabatan_display()}"


# =========================================================================
# 10. MODUL ADMINISTRASI / KEUANGAN
# =========================================================================
class AdministrasiSiswa(models.Model):
    STATUS_ADMINISTRASI = [
        ('Lunas',      'Lunas / Terverifikasi'),
        ('Tertunggak', 'Belum Membayar'),
    ]

    siswa             = models.ForeignKey(
        Siswa, on_delete=models.CASCADE, related_name='administrasi'
    )
    jenis_tagihan     = models.CharField(max_length=100, default="SPP Bulanan")
    jumlah_tagihan    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status            = models.CharField(
        max_length=15, choices=STATUS_ADMINISTRASI, default='Tertunggak'
    )
    tanggal_perubahan = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Administrasi Keuangan Siswa"
        verbose_name_plural = "Administrasi Keuangan Siswa"

    def __str__(self):
        return f"{self.siswa.nama_lengkap} - {self.jenis_tagihan} ({self.status})"