# Jalur file: core/models.py
from django.db import models
from django.contrib.auth.models import User

# ==========================================
# 1. AKTOR: GURU & KEPALA SEKOLAH
# ==========================================

class Guru(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='guru_profile')
    nip = models.CharField(max_length=20, unique=True, verbose_name="NIP")
    nama_lengkap = models.CharField(max_length=255)
    bidang_studi = models.CharField(max_length=100)
    foto = models.ImageField(upload_to='profil_guru/', null=True, blank=True)
    
    @property
    def no_hp(self):
        # Fallback jika ingin diintegrasikan dengan field profile kustom di masa depan
        return ""

    class Meta:
        verbose_name = "Guru"
        verbose_name_plural = "Guru"

    def __str__(self):
        return f"{self.nip} - {self.nama_lengkap}"


class KepalaSekolah(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='kepsek_core_user')
    nip = models.CharField(max_length=30, unique=True, verbose_name="NIP")
    nama_lengkap = models.CharField(max_length=150)
    no_hp = models.CharField(max_length=15, blank=True, null=True)
    foto_kepsek = models.ImageField(upload_to='profil_kepsek/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Aktor Kepala Sekolah"
        verbose_name_plural = "Profil Kepala Sekolah"

    def __str__(self):
        return f"{self.nip} - {self.nama_lengkap}"


# ==========================================
# 2. AKADEMIK: KELAS & STRUKTUR BELAJAR
# ==========================================

class Kelas(models.Model):
    nama_kelas = models.CharField(max_length=50, unique=True)
    wali_kelas = models.ForeignKey(
        Guru, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='kelas_binaan'
    )

    class Meta:
        verbose_name = "Kelas"
        verbose_name_plural = "Kelas"

    def __str__(self):
        return self.nama_kelas

    @property
    def total_siswa(self):
        """Menghitung jumlah siswa di kelas ini secara real-time"""
        return self.daftar_siswa.count()


# ==========================================
# 3. AKTOR: WALI MURID & SISWA
# ==========================================

class WaliMurid(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='wali_core_user')
    nama_lengkap = models.CharField(max_length=255)
    no_hp = models.CharField(max_length=15, blank=True, null=True)
    alamat = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Aktor Wali Murid"
        verbose_name_plural = "Wali"

    def __str__(self):
        return self.nama_lengkap


class Siswa(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='siswa_profile')
    nisn = models.CharField(max_length=20, unique=True, verbose_name="NISN")
    nama_lengkap = models.CharField(max_length=255)
    tempat_lahir = models.CharField(max_length=100, null=True, blank=True)
    tanggal_lahir = models.DateField(null=True, blank=True)
   
    foto = models.ImageField(upload_to='profil_siswa/', null=True, blank=True)
    
    kelas = models.ForeignKey(
        Kelas, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='daftar_siswa'
    )
    wali = models.ForeignKey(
        WaliMurid, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='daftar_anak'
    )

    class Meta:
        verbose_name = "Siswa"
        verbose_name_plural = "Siswa"

    def __str__(self):
        return f"{self.nisn} - {self.nama_lengkap}"

    @property
    def ringkasan_keuangan(self):
        """Membantu pencarian status tunggakan siswa di dashboard wali/siswa"""
        tagihan = self.keuangansiswa_set.all()
        total_tagihan = sum(t.jumlah for t in tagihan)
        total_lunas = sum(t.jumlah for t in tagihan if t.status_lunas)
        return {
            'total': total_tagihan,
            'lunas': total_lunas,
            'tunggakan': total_tagihan - total_lunas
        }


# ==========================================
# 4. OPERASIONAL: STAF & KEUANGAN
# ==========================================

class Staf(models.Model):
    BAGIAN_CHOICES = [
        ('TU', 'Tata Usaha / Administrasi'),
        ('KEU', 'Bendahara Keuangan'),
        ('PERPUS', 'Perpustakaan'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staf_core_user')
    nip = models.CharField(max_length=30, unique=True, verbose_name="NIP/Id Staf")
    nama_lengkap = models.CharField(max_length=255)
    bagian = models.CharField(max_length=20, choices=BAGIAN_CHOICES, default='TU')
    no_hp = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        verbose_name = "Aktor Staf"
        verbose_name_plural = "Staf Akademik"

    def __str__(self):
        return f"{self.nip} - {self.nama_lengkap} ({self.get_bagian_display()})"


class KeuanganSiswa(models.Model):
    siswa = models.ForeignKey(Siswa, on_delete=models.CASCADE, related_name='keuangansiswa_set')
    jenis_tagihan = models.CharField(max_length=100)
    jumlah = models.DecimalField(max_digits=12, decimal_places=0)
    status_lunas = models.BooleanField(default=False)
    tanggal_tagihan = models.DateField()

    class Meta:
        verbose_name = "Keuangan Siswa"
        verbose_name_plural = "Keuangan Siswa"

    def __str__(self):
        status = "Lunas" if self.status_lunas else "Belum Lunas"
        return f"{self.siswa.nama_lengkap} - {self.jenis_tagihan} ({status})"