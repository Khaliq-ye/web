from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils.text import slugify
from django.apps import apps  # Untuk panggilan lintas aplikasi (core & akademik)

# --- 1. ABSTRAK MODEL ---
class TimeStampedModel(models.Model):
    """ Model abstrak untuk mencatat jejak waktu di setiap tabel """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# --- 2. CORE MODELS WEB PUBLIK (OTOMATIS SINKRON) ---

class StatistikSekolah(models.Model):
    nama_studi = models.CharField(max_length=50, default="Statistik Utama Sekolah", editable=False)

    class Meta:
        verbose_name = "Statistik Sekolah"
        verbose_name_plural = "Statistik Sekolah"

    @property
    def total_siswa(self):
        """ Mengambil data total baris dari model Siswa di aplikasi core """
        try:
            from core.models import Siswa
            return Siswa.objects.count()
        except Exception:
            return 0

    @property
    def total_guru(self):
        """ Mengambil data total baris dari model Guru di aplikasi core """
        try:
            from core.models import Guru
            return Guru.objects.count()
        except Exception:
            return 0

    @property
    def total_kelas(self):
        """ Menghitung jumlah kelas unik dari Jadwal Pelajaran (akademik) atau Siswa (core) """
        nama_model_jadwal = ['Jadwal', 'JadwalPelajaran', 'JadwalKelas', 'JadwalPelajaranModel']
        
        for nama_model in nama_model_jadwal:
            try:
                ModelJadwal = apps.get_model('akademik', nama_model)
                fields = [f.name for f in ModelJadwal._meta.get_fields()]
                
                if 'kelas' in fields:
                    daftar_kelas = ModelJadwal.objects.exclude(kelas=None).exclude(kelas="").values_list('kelas', flat=True)
                    kelas_bersih = {k.strip() for k in daftar_kelas if k.strip()}
                    if kelas_bersih:
                        return len(kelas_bersih)
                
                elif 'kelas_id' in fields or any('kelas' in f for f in fields):
                    field_kelas = [f for f in fields if 'kelas' in f][0]
                    total = ModelJadwal.objects.exclude(**{f"{field_kelas}__isnull": True}).values(field_kelas).distinct().count()
                    if total > 0:
                        return total
            except (LookupError, ValueError):
                continue
        
        try:
            from core.models import Siswa
            daftar_kelas_siswa = Siswa.objects.exclude(kelas=None).exclude(kelas="").values_list('kelas', flat=True)
            kelas_siswa_bersih = {k.strip() for k in daftar_kelas_siswa if k.strip()}
            total_fallback = len(kelas_siswa_bersih)
            return total_fallback if total_fallback > 0 else (1 if self.total_siswa > 0 else 0)
        except Exception:
            return 0

    @property
    def total_mapel(self):
        """ Mengambil data total baris dari master Mata Pelajaran di aplikasi akademik """
        nama_model_mapel = ['Mapel', 'MataPelajaran', 'Mata_Pelajaran', 'mapel']
        
        for nama_model in nama_model_mapel:
            try:
                ModelMapel = apps.get_model('akademik', nama_model)
                return ModelMapel.objects.count()
            except (LookupError, ValueError):
                continue

        try:
            from core.models import Guru
            daftar_bidang = Guru.objects.exclude(bidang_studi=None).exclude(bidang_studi="").values_list('bidang_studi', flat=True)
            bidang_bersih = {b.strip() for b in daftar_bidang if b.strip()}
            total_mapel_guru = len(bidang_bersih)
            return total_mapel_guru if total_mapel_guru > 0 else self.total_guru
        except Exception:
            return 0

    def __str__(self):
        return f"Statistik Otomatis (Siswa: {self.total_siswa} | Guru: {self.total_guru})"


class Pengumuman(TimeStampedModel):
    judul = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, null=True) 
    isi = models.TextField()
    tanggal = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Pengumuman"
        ordering = ['-tanggal']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.judul)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.judul


class Agenda(TimeStampedModel):
    nama_kegiatan = models.CharField(max_length=255)
    tanggal = models.DateField()
    waktu = models.CharField(max_length=100, help_text="Contoh: 08:00 - Selesai")
    lokasi = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "Agenda Sekolah"

    def __str__(self):
        return self.nama_kegiatan


class Berita(TimeStampedModel):
    judul = models.CharField(max_length=255)
    gambar = models.ImageField(upload_to='berita/%Y/%m/%d/') 
    keterangan = models.TextField()
    tanggal_post = models.DateField()
    penulis = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Berita Sekolah"

    def __str__(self):
        return self.judul


class Pendaftaran(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Menunggu Verifikasi'),
        ('diterima', 'Diterima'),
        ('ditolak', 'Ditolak'),
    ]

    nisn_validator = RegexValidator(r'^\d{10}$', 'NISN harus berupa 10 digit angka.')

    nama_lengkap = models.CharField(max_length=100)
    nisn = models.CharField(max_length=10, unique=True, validators=[nisn_validator])
    asal_sekolah = models.CharField(max_length=100)
    email = models.EmailField()
    nomor_hp = models.CharField(max_length=15, validators=[RegexValidator(r'^\+?1?\d{9,15}$', 'Format nomor HP tidak valid.')])
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='pendaftaran_profile'
    )

    class Meta:
        verbose_name_plural = "Pendaftaran Siswa Baru"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.nama_lengkap} ({self.nisn})"


# --- 3. MODEL TAMBAHAN BARU (SINKRONISASI TEMPLATE & VIEWS) ---

class KepalaSekolah(TimeStampedModel):
    nama = models.CharField(max_length=150)
    sambutan = models.TextField()
    foto = models.ImageField(upload_to='kepsek/', blank=True, null=True)
    ttd = models.ImageField(upload_to='kepsek/ttd/', blank=True, null=True)

    class Meta:
        verbose_name = "Kepala Sekolah"
        verbose_name_plural = "Kepala Sekolah (Profil)"

    def __str__(self):
        return self.nama


class PpdbSetting(TimeStampedModel):
    brosur_pdf = models.FileField(upload_to='ppdb/brosur/', blank=True, null=True)
    informasi_tambahan = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Pengaturan PPDB"
        verbose_name_plural = "Pengaturan PPDB"

    def __str__(self):
        return "Konfigurasi Brosur & Dokumen PPDB"


class PpdbGelombang(TimeStampedModel):
    nama = models.CharField(max_length=100, help_text="Contoh: Gelombang I (Reguler)")
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    biaya = models.IntegerField(default=0, help_text="Tulis nominal saja tanpa titik/koma. Contoh: 250000")
    is_aktif = models.BooleanField(default=True)
    deskripsi = models.TextField(blank=True, null=True, help_text="Rincian alur atau berkas tambahan gelombang ini")

    class Meta:
        verbose_name = "Gelombang PPDB"
        verbose_name_plural = "Gelombang Seleksi PPDB"

    def __str__(self):
        return f"{self.nama} ({'Aktif' if self.is_aktif else 'Tutup'})"


class Prestasi(TimeStampedModel):
    juara = models.CharField(max_length=100, help_text="Contoh: Juara 1 Emas")
    nama_lomba = models.CharField(max_length=200, help_text="Contoh: Lomba Karya Tulis Ilmiah Nasional")
    nama_siswa = models.CharField(max_length=150, help_text="Contoh: Ahmad Dhani / Tim Teknik Komputer")
    tingkat = models.CharField(max_length=100, help_text="Contoh: Tingkat Provinsi / Nasional")

    class Meta:
        verbose_name = "Prestasi Sekolah"
        verbose_name_plural = "Prestasi Akademik & Non-Akademik"

    def __str__(self):
        return f"{self.juara} - {self.nama_lomba}"


class Galeri(TimeStampedModel):
    """ Model Galeri Tunggal - Menghindari Duplikasi Kebingungan Engine Django """
    KATEGORI_CHOICES = [
        ('fasilitas', 'Fasilitas & Lab'),
        ('kegiatan', 'Kegiatan Belajar'),
        ('ekstra', 'Ekstrakurikuler'),
    ]
    judul = models.CharField(max_length=200)
    gambar = models.ImageField(upload_to='galeri/%Y/%m/%d/')
    kategori = models.CharField(max_length=20, choices=KATEGORI_CHOICES, default='kegiatan')
    tanggal_kegiatan = models.DateField(help_text="Tanggal dokumentasi acara/fasilitas diambil")

    class Meta:
        verbose_name = "Galeri Sekolah"
        verbose_name_plural = "Galeri Foto Kegiatan"
        ordering = ['-tanggal_kegiatan']

    def __str__(self):
        return f"[{self.get_kategori_display()}] - {self.judul}"


class JadwalPelajaran(models.Model):
    CHOICES_PRODI = [
        ('TKJ', 'Teknik Komputer Jaringan'),
        ('RPL', 'Rekayasa Perangkat Lunak'),
    ]
    program_keahlian = models.CharField(max_length=3, choices=CHOICES_PRODI)
    mata_pelajaran = models.CharField(max_length=255)
    alokasi_waktu = models.CharField(max_length=100, help_text="Contoh: 6 Jam / Minggu")
    ruangan = models.CharField(max_length=100, help_text="Contoh: Lab Coding Alfa")

    class Meta:
        verbose_name = "Jadwal Pelajaran"
        verbose_name_plural = "Jadwal Pelajaran Publik"

    def __str__(self):
        return f"{self.program_keahlian} - {self.mata_pelajaran}"


class DokumenUnduhan(models.Model):
    nama_dokumen = models.CharField(max_length=255)
    file = models.FileField(upload_to='dokumen_akademik/')

    class Meta:
        verbose_name = "Dokumen Unduhan"
        verbose_name_plural = "Dokumen Unduhan"

    def __str__(self):
        return self.nama_dokumen
    
# ============================================================
# TAMBAHKAN 3 CLASS INI KE BAGIAN BAWAH models.py
# (setelah class DokumenUnduhan)
# ============================================================


class LayananAkademik(models.Model):
    """
    Program unggulan / jurusan dan fasilitas sekolah.
    Ditampilkan di halaman /profil/ pada bagian 'Layanan Akademik & Sarana'.
    """
    JENIS_CHOICES = [
        ('program', 'Program Unggulan / Jurusan'),
        ('fasilitas', 'Fasilitas Utama'),
    ]
    jenis = models.CharField(
        max_length=10,
        choices=JENIS_CHOICES,
        default='program',
        help_text="Pilih apakah ini Program Keahlian atau Fasilitas.",
    )
    nama = models.CharField(
        max_length=200,
        help_text="Contoh: Teknik Komputer & Jaringan (TKJ) / Laboratorium Komputer Modern",
    )
    deskripsi = models.TextField(
        help_text="Penjelasan singkat mengenai program atau fasilitas ini.",
    )
    urutan = models.PositiveIntegerField(
        default=0,
        help_text="Urutan tampil (angka lebih kecil = tampil lebih dulu).",
    )

    class Meta:
        verbose_name = "Layanan Akademik & Sarana"
        verbose_name_plural = "Layanan Akademik & Sarana"
        ordering = ['jenis', 'urutan']

    def __str__(self):
        return f"[{self.get_jenis_display()}] {self.nama}"


class KontakSekolah(models.Model):
    """
    Informasi kontak resmi sekolah.
    Ditampilkan di sidebar halaman /profil/ pada widget 'Kontak Utama'.
    Dirancang sebagai data tunggal (singleton) — tambah satu baris saja.
    """
    telepon  = models.CharField(max_length=50,  help_text="Contoh: (0376) 23456")
    email    = models.EmailField(help_text="Contoh: info@siakadpro.sch.id")
    alamat   = models.TextField(help_text="Alamat lengkap sekolah. Contoh: Jl. Pendidikan No. 123, Lombok Timur, NTB")
    website  = models.URLField(blank=True, null=True, help_text="URL website resmi (opsional)")
    wa       = models.CharField(
        max_length=20, blank=True, null=True,
        help_text="Nomor WhatsApp (opsional). Contoh: 62817xxxxxxx",
    )

    class Meta:
        verbose_name = "Kontak Sekolah"
        verbose_name_plural = "Kontak Sekolah"

    def __str__(self):
        return f"Kontak: {self.telepon} | {self.email}"


class Ekstrakurikuler(models.Model):
    """
    Daftar kegiatan ekstrakurikuler / pengembangan diri.
    Ditampilkan di halaman /akademik-info/ pada bagian 'Pengembangan Diri & Ekstrakurikuler'.
    """
    ICON_CHOICES = [
        ('fa-code',              'Pemrograman / IT'),
        ('fa-camera',           'Fotografi / Multimedia'),
        ('fa-futbol',           'Olahraga (Bola)'),
        ('fa-basketball',       'Olahraga (Basket)'),
        ('fa-music',            'Seni & Musik'),
        ('fa-leaf',             'Alam / Pramuka'),
        ('fa-microphone-lines', 'Debat / Public Speaking'),
        ('fa-palette',          'Seni Rupa / Desain'),
        ('fa-book-open',        'Literasi / Perpustakaan'),
        ('fa-shield-halved',    'PMR / Kesehatan'),
        ('fa-robot',            'Robotika / IoT'),
        ('fa-chess',            'Catur / Strategi'),
    ]
    nama     = models.CharField(max_length=150, help_text="Contoh: IT Club & Robotics")
    deskripsi = models.TextField(help_text="Deskripsi singkat kegiatan ekstrakurikuler.")
    icon     = models.CharField(
        max_length=50,
        choices=ICON_CHOICES,
        default='fa-star',
        help_text="Pilih ikon Font Awesome yang mewakili ekskul ini.",
    )
    urutan   = models.PositiveIntegerField(
        default=0,
        help_text="Urutan tampil di halaman. Angka lebih kecil tampil lebih dulu.",
    )
    is_aktif = models.BooleanField(default=True, help_text="Centang jika ekskul ini aktif dan ingin ditampilkan.")

    class Meta:
        verbose_name = "Ekstrakurikuler"
        verbose_name_plural = "Daftar Ekstrakurikuler"
        ordering = ['urutan', 'nama']

    def __str__(self):
        return self.nama