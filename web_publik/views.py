# Jalur file: C:\web\web_publik\views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Count
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.http import JsonResponse

from .models import (
    StatistikSekolah, Pengumuman, Agenda, Berita, Pendaftaran,
    PpdbSetting, PpdbGelombang, Prestasi, Galeri,
    DokumenUnduhan, KepalaSekolah as PublikKepalaSekolah,
    LayananAkademik, KontakSekolah, Ekstrakurikuler, JadwalPelajaran
)

from akademik.models import SambutanKepsek
from core.models import (
    KepalaSekolah as CoreKepalaSekolah,
    Guru as CoreGuru,
    Siswa as CoreSiswa,
    Staf as CoreStaf,
    WaliMurid as CoreWaliMurid,
    Kelas as CoreKelas          # 🌟 Ditambahkan ke baris impor utama
)

# ==========================================
# 1. PUBLIK VIEWS (HALAMAN INFORMASI)
# ==========================================

def index(request):
    stats_obj = StatistikSekolah.objects.first()
    if not stats_obj:
        stats_obj = StatistikSekolah()

    # 🌟 Diperbarui agar menghitung otomatis & real-time dari database core
    stats_data = {
        'total_siswa'   : CoreSiswa.objects.count() if CoreSiswa.objects.exists() else stats_obj.total_siswa,
        'total_guru'    : CoreGuru.objects.count() if CoreGuru.objects.exists() else stats_obj.total_guru,
        'total_kelas'   : CoreKelas.objects.count() if CoreKelas.objects.exists() else stats_obj.total_kelas,
        'total_mapel'   : stats_obj.total_mapel,
        'total_prestasi': Prestasi.objects.count() if Prestasi.objects.exists() else 0,
    }

    pengumuman_list = Pengumuman.objects.filter(is_active=True).order_by('-tanggal') if Pengumuman.objects.exists() else []
    agenda_list     = Agenda.objects.all().order_by('tanggal')[:4] if Agenda.objects.exists() else []
    berita_list     = Berita.objects.all().order_by('-tanggal_post')[:4] if Berita.objects.exists() else []

    try:
        sambutan_ops = SambutanKepsek.objects.first()
    except Exception:
        sambutan_ops = None

    ppdb_ops      = PpdbSetting.objects.first()
    gelombang_ops = PpdbGelombang.objects.all().order_by('id') if PpdbGelombang.objects.exists() else []
    prestasi_ops  = Prestasi.objects.all().order_by('-id')[:4] if Prestasi.objects.exists() else []

    context = {
        'stats'             : stats_data,
        'pengumuman_running': pengumuman_list,
        'agenda_sekolah'    : agenda_list,
        'berita'            : berita_list,
        'kepala_sekolah'    : sambutan_ops,
        'ppdb_setting'      : ppdb_ops,
        'ppdb_gelombang'    : gelombang_ops,
        'prestasi'          : prestasi_ops,
    }
    return render(request, 'web_publik/index.html', context)


def profil(request):
    try:
        data_kepsek_profil = PublikKepalaSekolah.objects.first()
    except Exception:
        data_kepsek_profil = None

    try:
        statistik = StatistikSekolah.objects.first()
    except Exception:
        statistik = None

    try:
        program_list   = LayananAkademik.objects.filter(jenis='program').order_by('urutan')
        fasilitas_list = LayananAkademik.objects.filter(jenis='fasilitas').order_by('urutan')
    except Exception:
        program_list   = []
        fasilitas_list = []

    try:
        kontak = KontakSekolah.objects.first()
    except Exception:
        kontak = None

    context = {
        'kepsek'        : data_kepsek_profil,
        'statistik'     : statistik,
        'program_list'  : program_list,
        'fasilitas_list': fasilitas_list,
        'kontak'        : kontak,
    }
    return render(request, 'web_publik/profil.html', context)


def akademik_info(request):
    jadwal_tkj   = JadwalPelajaran.objects.filter(program_keahlian='TKJ') if JadwalPelajaran.objects.exists() else []
    jadwal_rpl   = JadwalPelajaran.objects.filter(program_keahlian='RPL') if JadwalPelajaran.objects.exists() else []
    dokumen_list = DokumenUnduhan.objects.all().order_by('-id') if DokumenUnduhan.objects.exists() else []
    agenda_list  = Agenda.objects.all().order_by('tanggal')[:4] if Agenda.objects.exists() else []

    try:
        ekskul_list = Ekstrakurikuler.objects.filter(is_aktif=True).order_by('urutan', 'nama')
    except Exception:
        ekskul_list = []

    context = {
        'jadwal_tkj'    : jadwal_tkj,
        'jadwal_rpl'    : jadwal_rpl,
        'dokumen_list'  : dokumen_list,
        'agenda_sekolah': agenda_list,
        'ekskul_list'   : ekskul_list,
    }
    return render(request, 'web_publik/akademik.html', context)


def galeri(request):
    daftar_galeri       = Galeri.objects.all().order_by('-tanggal_kegiatan') if Galeri.objects.exists() else []
    stats_kategori      = Galeri.objects.values('kategori').annotate(total=Count('id')) if Galeri.objects.exists() else []
    jumlah_per_kategori = {item['kategori']: item['total'] for item in stats_kategori}
    total_semua         = Galeri.objects.count() if Galeri.objects.exists() else 0

    try:
        kontak = KontakSekolah.objects.first()
    except Exception:
        kontak = None

    context = {
        'daftar_galeri'   : daftar_galeri,
        'jumlah_fasilitas': jumlah_per_kategori.get('fasilitas', 0),
        'jumlah_kegiatan' : jumlah_per_kategori.get('kegiatan', 0),
        'jumlah_ekstra'   : jumlah_per_kategori.get('ekstra', 0),
        'total_semua'     : total_semua,
        'kontak'          : kontak,
    }
    return render(request, 'web_publik/galeri.html', context)


def berita(request):
    konteks = {
        'semua_berita': Berita.objects.all().order_by('-tanggal_post') if Berita.objects.exists() else []
    }
    return render(request, 'web_publik/berita_list.html', konteks)


def detail_berita(request, id):
    item_berita = get_object_or_404(Berita, id=id)
    return render(request, 'web_publik/berita_detail.html', {'item': item_berita})


def detail_berita_json(request, berita_id):
    item      = get_object_or_404(Berita, id=berita_id)
    gambar_url = item.gambar.url if item.gambar else ''
    data = {
        'judul'    : item.judul,
        'isi'      : item.keterangan if hasattr(item, 'keterangan') else item.isi,
        'gambar_url': gambar_url,
    }
    return JsonResponse(data)


def gelombang_detail_json(request, id):
    gelombang   = get_object_or_404(PpdbGelombang, id=id)
    tgl_mulai   = gelombang.tanggal_mulai.strftime('%d %B %Y') if gelombang.tanggal_mulai else '-'
    tgl_selesai = gelombang.tanggal_selesai.strftime('%d %B %Y') if gelombang.tanggal_selesai else '-'
    data = {
        'nama'          : gelombang.nama,
        'tanggal_mulai' : tgl_mulai,
        'tanggal_selesai': tgl_selesai,
        'biaya'         : f"{gelombang.biaya:,}".replace(",", "."),
        'deskripsi'     : getattr(gelombang, 'deskripsi', 'Silahkan lakukan pengisian berkas pendaftaran online.'),
        'url_daftar'    : reverse('web_publik:ppdb_online')
    }
    return JsonResponse(data)


# ==========================================
# 2. SISTEM PPDB ONLINE
# ==========================================

def ppdb_online(request):
    if request.method == 'POST':
        data = {
            'nama': request.POST.get('nama', '').strip(),
            'nisn': request.POST.get('nisn', '').strip(),
            'email': request.POST.get('email', '').strip(),
            'hp'  : request.POST.get('hp', '').strip(),
            'asal': request.POST.get('asal_sekolah', '').strip(),
        }

        if not all(data.values()):
            messages.error(request, "Semua kolom wajib diisi!")
            return render(request, 'web_publik/ppdb_form.html', {'form_data': data})

        if not data['nisn'].isdigit() or len(data['nisn']) != 10:
            messages.error(request, f"NISN harus tepat 10 digit angka. Yang dimasukkan: '{data['nisn']}' ({len(data['nisn'])} karakter)")
            return render(request, 'web_publik/ppdb_form.html', {'form_data': data})

        try:
            with transaction.atomic():
                if Pendaftaran.objects.filter(nisn=data['nisn']).exists() or \
                   User.objects.filter(username=data['nisn']).exists():
                    messages.warning(request, f"NISN {data['nisn']} sudah terdaftar di sistem kami.")
                    return render(request, 'web_publik/ppdb_form.html', {'form_data': data})

                pendaftaran = Pendaftaran.objects.create(
                    nama_lengkap=data['nama'],
                    nisn=data['nisn'],
                    asal_sekolah=data['asal'],
                    email=data['email'],
                    nomor_hp=data['hp'],
                    status='pending'
                )

                user = User.objects.create_user(
                    username=data['nisn'],
                    password=data['nisn'],
                    first_name=data['nama']
                )

                try:
                    group = Group.objects.get(name='Siswa')
                    user.groups.add(group)
                except Group.DoesNotExist:
                    pass

                # 🌟 Menggunakan CoreKelas (Import bersih di bagian atas berkas)
                kelas_default = CoreKelas.objects.first()

                pendaftaran.user = user
                pendaftaran.save()

        except IntegrityError as e:
            messages.error(request, f"Data duplikat terdeteksi. Pastikan NISN belum pernah digunakan. ({str(e)})")
            return render(request, 'web_publik/ppdb_form.html', {'form_data': data})
        except Exception as e:
            messages.error(request, f"Gagal mendaftar. Detail error: {str(e)}")
            return render(request, 'web_publik/ppdb_form.html', {'form_data': data})

        messages.success(request, f"Pendaftaran berhasil, {data['nama']}! Silakan login menggunakan NISN: {data['nisn']}")
        return redirect('web_publik:index')

    return render(request, 'web_publik/ppdb_form.html', {'form_data': {}})


# ==========================================
# 3. AUTHENTICATION & PORTAL LOGIN
# ==========================================

def login_portal(request):
    if request.user.is_authenticated:
        return redirect_by_role(request, request.user)

    if request.method == 'POST':
        u    = request.POST.get('username')
        p    = request.POST.get('password')
        user = authenticate(request, username=u, password=p)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect_by_role(request, user)
            else:
                messages.error(request, "Akun Anda sedang dinonaktifkan oleh administrator.")
        else:
            messages.error(request, "Username atau Password salah!")

    return render(request, 'web_publik/login.html')


def redirect_by_role(request, user):
    groups = list(user.groups.values_list('name', flat=True))

    if 'Staf Keuangan' in groups or 'staf_keuangan' in [g.lower() for g in groups]:
        return redirect(reverse('core:keuangan_siswa'))

    try:
        if CoreKepalaSekolah.objects.filter(user=user).exists():
            return redirect(reverse('akademik:dashboard_kepsek'))
        if CoreGuru.objects.filter(user=user).exists():
            return redirect(reverse('akademik:dashboard_guru'))
        if CoreSiswa.objects.filter(user=user).exists():
            return redirect(reverse('akademik:dashboard_siswa'))
        if CoreWaliMurid.objects.filter(user=user).exists():
            return redirect(reverse('akademik:dashboard_wali'))
        if CoreStaf.objects.filter(user=user).exists():
            return redirect(reverse('akademik:dashboard_staf'))
    except Exception:
        pass

    role_map = {
        'Kepala Sekolah'    : 'akademik:dashboard_kepsek',
        'Guru'              : 'akademik:dashboard_guru',
        'Siswa'             : 'akademik:dashboard_siswa',
        'Wali Murid'        : 'akademik:dashboard_wali',
        'Staff Administrasi': 'akademik:dashboard_staf',
        'Bendahara'         : 'akademik:dashboard_bendahara',
        'Perpustakaan'      : 'akademik:dashboard_perpus',
    }
    for role, url_name in role_map.items():
        if role in groups:
            try:
                return redirect(reverse(url_name))
            except Exception:
                continue

    if user.is_superuser:
        return redirect('/admin/')
    if user.is_staff:
        return redirect(reverse('akademik:dashboard_staf'))

    messages.warning(request, f"Akun '{user.username}' belum dihubungkan ke dashboard manapun.")
    return redirect('web_publik:index')


def logout_user(request):
    logout(request)
    messages.info(request, "Berhasil logout. Sampai jumpa kembali!")
    return redirect('web_publik:index')