import os
from datetime import date
from akademik.forms import UpdateBiodataSiswaForm
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Avg
from django.urls import reverse

from core.models import (
    Siswa, Guru, KepalaSekolah as CoreKepalaSekolah,
    WaliMurid, Staf, KeuanganSiswa,
)
from akademik.models import (
    MataPelajaran,
    JadwalPelajaran,
    JurnalMengajar,
    MateriAjar,
    Presensi,
    TugasKuis,
    JawabanSiswa,
    NilaiRapor,
    NilaiPerilaku,
    KepalaSekolahProfile,
    AdministrasiSiswa,
    StaffProfile,
)
from web_publik.models import Pengumuman, Agenda, Berita


# ==============================================================================
# HELPER — hitung nilai perilaku global seorang siswa
# ==============================================================================

def hitung_nilai_perilaku_siswa(siswa):
    """
    Ambil semua NilaiPerilaku milik siswa dari SEMUA guru, konversi ke angka,
    lalu rata-rata.

    Skala:
      Baik   = 100
      Cukup  = 70
      Kurang = 30

    Formula:
      nilai_perilaku = rata-rata(semua skor dari semua penilaian semua guru)
      Kontribusi ke rapor = 15%

    Kembalikan integer 0-100.
    """
    SKOR = {'Baik': 100, 'Cukup': 70, 'Kurang': 30}
    qs = NilaiPerilaku.objects.filter(
        siswa=siswa
    ).values_list('kategori', flat=True)
    if not qs.exists():
        return 0
    total = sum(SKOR.get(k, 0) for k in qs)
    return int(round(total / qs.count()))


def hitung_nilai_akhir(nilai_tugas, nilai_uts, nilai_uas, nilai_perilaku):
    """
    Formula nilai akhir rapor:
      Tugas (35%) + UTS (25%) + UAS (25%) + Perilaku (15%)
    """
    return int(
        (nilai_tugas * 0.35)
        + (nilai_uts * 0.25)
        + (nilai_uas * 0.25)
        + (nilai_perilaku * 0.15)
    )


# ==============================================================================
# 1. DASHBOARD ROLES & PROFILE ACTIONS
# ==============================================================================

@login_required
def dashboard_siswa(request):
    siswa = Siswa.objects.select_related(
        'user', 'wali', 'kelas'
    ).filter(user=request.user).first()

    if request.method == 'POST' and request.POST.get('action') == 'update_biodata':
        if siswa:
            form = UpdateBiodataSiswaForm(request.POST, instance=siswa)
            if form.is_valid():
                form.save()
                messages.success(request, "Biodata berhasil diperbarui!")
            else:
                messages.error(
                    request,
                    "Gagal menyimpan: " + form.errors.as_text()
                )
        else:
            messages.error(
                request,
                "Profil siswa tidak ditemukan. Hubungi admin sekolah."
            )
        return redirect('akademik:dashboard_siswa')

    data = {
        'role': 'Siswa',
        'siswa': siswa,
        'pengumuman': Pengumuman.objects.filter(
            is_active=True
        ).order_by('-created_at')[:5],
        'agenda': Agenda.objects.all().order_by('tanggal')[:5],
        'jadwal_pelajaran': [],
        'absensi': {
            'hadir': 0, 'izin': 0, 'sakit': 0, 'alfa': 0, 'persentase': 0
        },
        # nilai_list = NilaiRapor queryset lengkap (tugas, uts, uas, perilaku, akhir)
        # ditampilkan di panel "Rekap Nilai Rapor" dashboard utama
        'nilai_list': [],
        # tugas_list = daftar tugas aktif dari e-learning
        'tugas_list': [],
        'tagihan_list': [],
        'wali_kelas': None,
        'no_hp_wali': '',
        # jawaban_dinilai = hanya jawaban tugas yang sudah dinilai guru
        # ditampilkan di panel "Nilai & Feedback Tugas dari Guru"
        'jawaban_dinilai': [],
        'rata_nilai_tugas': None,
        # nilai_perilaku_siswa = integer 0-100 (rata-rata semua guru)
        'nilai_perilaku_siswa': 0,
        # riwayat_perilaku = 10 penilaian perilaku terakhir
        'riwayat_perilaku': [],
        # rata-rata nilai akhir rapor (sudah include perilaku 15%)
        'rata_nilai_rapor': None,
        'total_nilai_rapor': 0,
        # statistik perilaku untuk sidebar
        'perilaku_baik_count': 0,
        'perilaku_cukup_count': 0,
        'perilaku_kurang_count': 0,
        'total_penilaian_perilaku': 0,
    }

    if siswa:
        # ── Nilai perilaku global (dari SEMUA guru) ───────────────
        nilai_perilaku = hitung_nilai_perilaku_siswa(siswa)
        data['nilai_perilaku_siswa'] = nilai_perilaku

        # ── Statistik distribusi perilaku ────────────────────────
        qs_perilaku = NilaiPerilaku.objects.filter(siswa=siswa)
        data['perilaku_baik_count'] = qs_perilaku.filter(
            kategori='Baik'
        ).count()
        data['perilaku_cukup_count'] = qs_perilaku.filter(
            kategori='Cukup'
        ).count()
        data['perilaku_kurang_count'] = qs_perilaku.filter(
            kategori='Kurang'
        ).count()
        data['total_penilaian_perilaku'] = qs_perilaku.count()

        # ── Nilai rapor lengkap ───────────────────────────────────
        # Hitung ulang nilai_akhir dengan perilaku global terkini
        nilai_rapor_qs = NilaiRapor.objects.filter(
            siswa=siswa
        ).select_related('mata_pelajaran').order_by('mata_pelajaran__nama')

        # Buat list dengan nilai_akhir yang sudah dikalkulasi ulang
        nilai_list_computed = []
        for n in nilai_rapor_qs:
            akhir = hitung_nilai_akhir(
                n.nilai_tugas, n.nilai_uts, n.nilai_uas, nilai_perilaku
            )
            nilai_list_computed.append({
                'obj': n,
                'mata_pelajaran': n.mata_pelajaran,
                'nilai_tugas': n.nilai_tugas,
                'nilai_uts': n.nilai_uts,
                'nilai_uas': n.nilai_uas,
                'nilai_perilaku': nilai_perilaku,
                'nilai_angka': akhir,
                'keterangan': n.keterangan or '',
            })

        data['nilai_list'] = nilai_list_computed

        # ── Total & rata-rata rapor ───────────────────────────────
        angka_list = [v['nilai_angka'] for v in nilai_list_computed]
        if angka_list:
            data['rata_nilai_rapor'] = round(
                sum(angka_list) / len(angka_list), 1
            )
            data['total_nilai_rapor'] = len(angka_list)

        # ── Tagihan keuangan ──────────────────────────────────────
        data['tagihan_list'] = AdministrasiSiswa.objects.filter(
            siswa=siswa
        ).order_by('-tanggal_perubahan')

        # ── Absensi ───────────────────────────────────────────────
        absensi_data = Presensi.objects.filter(
            siswa=siswa
        ).values('status').annotate(total=Count('status'))
        total_hadir = total_hari = 0
        for item in absensi_data:
            s = item['status'].lower()
            key = 'alfa' if s == 'alpa' else s
            if key in data['absensi']:
                data['absensi'][key] = item['total']
            total_hari += item['total']
            if s == 'hadir':
                total_hadir = item['total']
        if total_hari > 0:
            data['absensi']['persentase'] = int(
                (total_hadir / total_hari) * 100
            )

        if siswa.kelas:
            wali = siswa.kelas.wali_kelas
            data['wali_kelas'] = wali
            if wali and wali.no_hp:
                hp = wali.no_hp.strip()
                data['no_hp_wali'] = (
                    '62' + hp[1:] if hp.startswith('0') else hp
                )
            data['jadwal_pelajaran'] = JadwalPelajaran.objects.filter(
                kelas=siswa.kelas
            ).order_by('hari', 'jam_mulai')
            data['tugas_list'] = TugasKuis.objects.filter(
                jadwal__kelas=siswa.kelas
            ).select_related('mata_pelajaran').prefetch_related(
                'jawaban_siswa'
            ).order_by('-id')[:10]

        # ── Jawaban tugas yang sudah dinilai guru ─────────────────
        # Panel "Nilai & Feedback Tugas dari Guru" HANYA menampilkan ini
        jawaban_dinilai = JawabanSiswa.objects.filter(
            siswa=siswa,
            nilai__isnull=False,
        ).select_related(
            'tugas', 'tugas__mata_pelajaran'
        ).order_by('-diperbarui_at')
        data['jawaban_dinilai'] = jawaban_dinilai

        nilai_list_tugas = [
            j.nilai for j in jawaban_dinilai if j.nilai is not None
        ]
        if nilai_list_tugas:
            data['rata_nilai_tugas'] = round(
                sum(nilai_list_tugas) / len(nilai_list_tugas), 1
            )

        # ── Riwayat perilaku 10 terakhir ─────────────────────────
        data['riwayat_perilaku'] = NilaiPerilaku.objects.filter(
            siswa=siswa
        ).select_related(
            'guru', 'jadwal__mata_pelajaran'
        ).order_by('-tanggal')[:10]

    return render(request, 'akademik/dashboard/siswa.html', data)


def laporkan_bug(request):
    if request.method == 'POST':
        messages.success(request, "Laporan bug telah berhasil dikirim!")
        return redirect('akademik:dashboard_siswa')
    return redirect('akademik:dashboard_siswa')

@login_required
def update_foto_siswa(request):
    if request.method == 'POST' and request.FILES.get('foto_profil'):
        siswa = Siswa.objects.filter(user=request.user).first()
        if not siswa:
            return JsonResponse({'success': False, 'message': 'Data siswa tidak ditemukan.'}, status=404)
        if siswa.foto and hasattr(siswa.foto, 'path'):
            if os.path.exists(siswa.foto.path):
                os.remove(siswa.foto.path)
        siswa.foto = request.FILES['foto_profil']
        siswa.save()
        return JsonResponse({'success': True, 'message': 'Foto profil berhasil diperbarui!', 'url': siswa.foto.url})
    return JsonResponse({'success': False, 'message': 'Request tidak valid.'}, status=400)

@login_required
def dashboard_guru(request):
    guru = Guru.objects.filter(user=request.user).first()
    jadwal_mengajar = []
    total_sesi = 0

    if guru:
        jadwal_mengajar = JadwalPelajaran.objects.filter(
            guru=guru
        ).order_by('hari', 'jam_mulai')
        total_sesi = jadwal_mengajar.count()

    # ── Handle POST: simpan nilai perilaku dari dashboard guru ────
    if (
        request.method == 'POST'
        and request.POST.get('action') == 'simpan_perilaku_guru'
    ):
        if not guru:
            messages.error(request, "Data guru tidak ditemukan.")
            return redirect('akademik:dashboard_guru')

        jadwal_id = request.POST.get('jadwal_id', '').strip()
        tgl_str = request.POST.get('tanggal', str(date.today()))
        try:
            from datetime import datetime
            tgl_simpan = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        except ValueError:
            tgl_simpan = date.today()

        if not jadwal_id:
            messages.error(request, "Pilih jadwal terlebih dahulu.")
            return redirect('akademik:dashboard_guru')

        jadwal_obj = get_object_or_404(
            JadwalPelajaran, id=jadwal_id, guru=guru
        )
        disimpan = 0

        for s in Siswa.objects.filter(kelas=jadwal_obj.kelas):
            kategori_val = request.POST.get(
                'perilaku_' + str(s.pk), ''
            ).strip()
            catatan_val = request.POST.get(
                'catatan_perilaku_' + str(s.pk), ''
            ).strip()
            if kategori_val in ('Baik', 'Cukup', 'Kurang'):
                NilaiPerilaku.objects.update_or_create(
                    siswa=s,
                    guru=guru,
                    jadwal=jadwal_obj,
                    tanggal=tgl_simpan,
                    defaults={
                        'kategori': kategori_val,
                        'catatan': catatan_val or None,
                    },
                )
                disimpan += 1

        messages.success(
            request,
            str(disimpan)
            + " penilaian perilaku berhasil disimpan dari Dashboard Guru.",
        )
        return redirect('akademik:dashboard_guru')

    # ── Data untuk panel nilai perilaku di dashboard guru ─────────
    siswa_perilaku_list = []
    jadwal_terpilih_perilaku = None
    tanggal_terpilih_perilaku = date.today()

    jadwal_id_get = request.GET.get('jadwal_perilaku')
    tgl_param = request.GET.get('tanggal_perilaku', '')
    if tgl_param:
        try:
            from datetime import datetime
            tanggal_terpilih_perilaku = datetime.strptime(
                tgl_param, '%Y-%m-%d'
            ).date()
        except ValueError:
            tanggal_terpilih_perilaku = date.today()

    if guru and jadwal_id_get:
        jadwal_terpilih_perilaku = JadwalPelajaran.objects.filter(
            id=jadwal_id_get, guru=guru
        ).first()
        if jadwal_terpilih_perilaku:
            for s in Siswa.objects.filter(
                kelas=jadwal_terpilih_perilaku.kelas
            ).order_by('nama_lengkap'):
                existing = NilaiPerilaku.objects.filter(
                    siswa=s,
                    guru=guru,
                    jadwal=jadwal_terpilih_perilaku,
                    tanggal=tanggal_terpilih_perilaku,
                ).first()
                siswa_perilaku_list.append({
                    'siswa': s,
                    'kategori': existing.kategori if existing else None,
                    'catatan': existing.catatan if existing else '',
                    # Skor global = rata-rata semua penilaian semua guru
                    'skor_global': hitung_nilai_perilaku_siswa(s),
                })

    context = {
        'role': 'Guru',
        'guru': guru,
        'jadwal_mengajar': jadwal_mengajar,
        'total_sesi': total_sesi,
        'pengumuman': Pengumuman.objects.filter(
            is_active=True
        ).order_by('-created_at')[:3],
        'siswa_perilaku_list': siswa_perilaku_list,
        'jadwal_terpilih_perilaku': jadwal_terpilih_perilaku,
        'tanggal_terpilih_perilaku': tanggal_terpilih_perilaku,
        'PERILAKU_CHOICES': ['Baik', 'Cukup', 'Kurang'],
    }
    return render(request, 'akademik/dashboard/guru.html', context)


@login_required
def update_foto_guru(request):
    if request.method == 'POST' and request.FILES.get('foto_profil'):
        guru = Guru.objects.filter(user=request.user).first()
        if not guru:
            return JsonResponse(
                {'success': False, 'message': 'Data Guru tidak ditemukan.'},
                status=404,
            )
        if guru.foto and hasattr(guru.foto, 'path'):
            if os.path.exists(guru.foto.path):
                os.remove(guru.foto.path)
        guru.foto = request.FILES['foto_profil']
        guru.save()
        return JsonResponse({
            'success': True,
            'message': 'Foto profil berhasil diperbarui!',
            'url': guru.foto.url,
        })
    return JsonResponse(
        {'success': False, 'message': 'Request tidak valid.'}, status=400
    )


@login_required
def update_foto_kepsek(request):
    if request.method == 'POST' and request.FILES.get('foto_kepsek'):
        kepsek_profile, _ = CoreKepalaSekolah.objects.get_or_create(
            user=request.user
        )
        if kepsek_profile.foto_kepsek and hasattr(
            kepsek_profile.foto_kepsek, 'path'
        ):
            if os.path.exists(kepsek_profile.foto_kepsek.path):
                os.remove(kepsek_profile.foto_kepsek.path)
        kepsek_profile.foto_kepsek = request.FILES['foto_kepsek']
        kepsek_profile.save()
        return JsonResponse({
            'success': True,
            'message': (
                'Foto profil resmi Kepala Sekolah berhasil diperbarui!'
            ),
            'url': kepsek_profile.foto_kepsek.url,
        })
    return JsonResponse(
        {'success': False, 'message': 'Request tidak valid.'}, status=400
    )


@login_required
def dashboard_kepsek(request):
    kepsek_profile, _ = CoreKepalaSekolah.objects.get_or_create(
        user=request.user
    )

    if request.method == 'POST' and 'update_profile' in request.POST:
        kepsek_profile.nama_lengkap = request.POST.get('nama_lengkap')
        kepsek_profile.bio = request.POST.get('bio')
        kepsek_profile.nip = request.POST.get('nip')
        foto_baru = request.FILES.get('foto_kepsek')
        if foto_baru:
            kepsek_profile.foto_kepsek = foto_baru
        kepsek_profile.save()
        messages.success(request, "Profil berhasil diperbarui!")
        return redirect('akademik:dashboard_kepsek')

    daftar_siswa = Siswa.objects.all().order_by('nama_lengkap')
    daftar_guru = Guru.objects.all().order_by('nama_lengkap')

    daftar_lunas = KeuanganSiswa.objects.filter(
        status_lunas=True
    ).select_related('siswa').order_by('-id')

    daftar_tertunggak = KeuanganSiswa.objects.filter(
        status_lunas=False
    ).select_related('siswa').order_by('-id')

    jurnal_hari_ini = JurnalMengajar.objects.filter(
        tanggal=date.today()
    ).select_related('jadwal__guru', 'jadwal__mata_pelajaran')

    presensi_hari_ini = Presensi.objects.filter(tanggal=date.today())
    total_absen = presensi_hari_ini.count()
    hadir_count = presensi_hari_ini.filter(status='Hadir').count()
    izin_count = presensi_hari_ini.filter(status='Izin').count()
    sakit_count = presensi_hari_ini.filter(status='Sakit').count()
    alpa_count = presensi_hari_ini.filter(status='Alpa').count()
    persentase_kehadiran = (
        int(round((hadir_count / total_absen) * 100))
        if total_absen > 0 else 0
    )

    context = {
        'role': 'Kepala Sekolah',
        'kepsek_profile': kepsek_profile,
        'total_siswa': daftar_siswa.count(),
        'total_guru': daftar_guru.count(),
        'transaksi_lunas': daftar_lunas.count(),
        'transaksi_tertunggak': daftar_tertunggak.count(),
        'daftar_siswa': daftar_siswa,
        'daftar_guru': daftar_guru,
        'daftar_lunas': daftar_lunas,
        'daftar_tertunggak': daftar_tertunggak,
        'jurnal_hari_ini': jurnal_hari_ini,
        'persentase_kehadiran': persentase_kehadiran,
        'total_absen_hari_ini': total_absen,
        'hadir_count': hadir_count,
        'izin_count': izin_count,
        'sakit_count': sakit_count,
        'alpa_count': alpa_count,
    }
    return render(request, 'akademik/dashboard/kepsek.html', context)


@login_required
def dashboard_wali(request):
    user = request.user
    if not (user.is_superuser or hasattr(user, 'wali_core_user')):
        raise PermissionDenied

    wali = getattr(user, 'wali_core_user', None)
    daftar_anak = []

    if wali:
        daftar_anak = wali.daftar_anak.all()
    elif user.is_superuser:
        daftar_anak = Siswa.objects.all()[:2]

    anak_id = request.GET.get('anak_id')
    if anak_id and daftar_anak.filter(id=anak_id).exists():
        siswa_terkait = daftar_anak.get(id=anak_id)
    else:
        siswa_terkait = daftar_anak.first() if daftar_anak else None

    daftar_nilai = []
    daftar_presensi = []
    semua_presensi = []
    daftar_tagihan = []
    daftar_jadwal = []
    wali_kelas = None
    no_hp_wali_kelas = ''

    total_hadir = 0
    total_alpha = 0
    total_izin = 0
    total_sakit = 0
    total_presensi = 0
    persen_hadir = 0
    rata_nilai = None
    total_mapel = 0
    total_tagihan = 0
    total_tagihan_lunas = 0
    total_tagihan_belum = 0

    def get_predikat(angka):
        if angka >= 90: return 'A'
        elif angka >= 80: return 'B'
        elif angka >= 70: return 'C'
        elif angka >= 60: return 'D'
        else: return 'E'

    if siswa_terkait:
        nilai_perilaku_wali = hitung_nilai_perilaku_siswa(siswa_terkait)

        nilai_rapor_qs = NilaiRapor.objects.filter(
            siswa=siswa_terkait
        ).select_related('mata_pelajaran').order_by('mata_pelajaran__nama')
        total_mapel = nilai_rapor_qs.count()

        angka_list = []
        for n in nilai_rapor_qs:
            akhir = hitung_nilai_akhir(
                n.nilai_tugas, n.nilai_uts, n.nilai_uas, nilai_perilaku_wali
            )
            angka_list.append(akhir)
            daftar_nilai.append({
                'mata_pelajaran': n.mata_pelajaran,
                'nilai_tugas': n.nilai_tugas,
                'nilai_uts': n.nilai_uts,
                'nilai_uas': n.nilai_uas,
                'nilai_angka': akhir,
                'predikat': get_predikat(akhir),
                'keterangan': n.keterangan or '—',
            })

        if angka_list:
            rata_nilai = round(sum(angka_list) / len(angka_list), 1)

        semua_presensi = Presensi.objects.filter(
            siswa=siswa_terkait
        ).select_related('jadwal__mata_pelajaran').order_by('-tanggal')
        daftar_presensi = semua_presensi[:10]

        total_hadir = semua_presensi.filter(status='Hadir').count()
        total_alpha = semua_presensi.filter(
            status__in=['Alpa', 'Alpha']
        ).count()
        total_izin = semua_presensi.filter(status='Izin').count()
        total_sakit = semua_presensi.filter(status='Sakit').count()
        total_presensi = semua_presensi.count()
        if total_presensi > 0:
            persen_hadir = int(
                round((total_hadir / total_presensi) * 100)
            )

        daftar_tagihan = AdministrasiSiswa.objects.filter(
            siswa=siswa_terkait
        ).order_by('-tanggal_perubahan')
        total_tagihan = daftar_tagihan.count()
        total_tagihan_lunas = daftar_tagihan.filter(status='Lunas').count()
        total_tagihan_belum = daftar_tagihan.filter(
            status='Tertunggak'
        ).count()

        if siswa_terkait.kelas:
            daftar_jadwal = JadwalPelajaran.objects.filter(
                kelas=siswa_terkait.kelas
            ).select_related(
                'mata_pelajaran', 'guru'
            ).order_by('hari', 'jam_mulai')

            wali_kelas = siswa_terkait.kelas.wali_kelas
            if wali_kelas and wali_kelas.no_hp:
                hp = wali_kelas.no_hp.strip()
                no_hp_wali_kelas = (
                    '62' + hp[1:] if hp.startswith('0') else hp
                )

    daftar_agenda = Agenda.objects.all().order_by('tanggal')[:10]
    daftar_pengumuman = Pengumuman.objects.filter(
        is_active=True
    ).order_by('-created_at')[:8]

    context = {
        'role': 'Wali Murid',
        'wali': wali,
        'daftar_anak': daftar_anak,
        'siswa_terkait': siswa_terkait,
        'daftar_nilai': daftar_nilai,
        'rata_nilai': rata_nilai,
        'total_mapel': total_mapel,
        'daftar_presensi': daftar_presensi,
        'semua_presensi': semua_presensi,
        'total_hadir': total_hadir,
        'total_alpha': total_alpha,
        'total_izin': total_izin,
        'total_sakit': total_sakit,
        'total_presensi': total_presensi,
        'persen_hadir': persen_hadir,
        'daftar_tagihan': daftar_tagihan,
        'total_tagihan': total_tagihan,
        'total_tagihan_lunas': total_tagihan_lunas,
        'total_tagihan_belum': total_tagihan_belum,
        'daftar_jadwal': daftar_jadwal,
        'daftar_agenda': daftar_agenda,
        'wali_kelas': wali_kelas,
        'no_hp_wali_kelas': no_hp_wali_kelas,
        'daftar_pengumuman': daftar_pengumuman,
    }
    return render(request, 'akademik/dashboard/wali.html', context)


@login_required
def dashboard_staf(request):
    user = request.user

    if not user.is_superuser:
        if user.groups.filter(name='Staf Keuangan').exists():
            return redirect(reverse('core:keuangan_siswa'))

    if not (user.is_superuser or user.is_staff):
        raise PermissionDenied

    from web_publik.models import (
        Agenda, Berita, Pengumuman, Prestasi, Galeri,
        PpdbGelombang, PpdbSetting, KontakSekolah,
        LayananAkademik, DokumenUnduhan, Ekstrakurikuler,
        Pendaftaran,
    )
    from akademik.forms import EditDataSiswaAdminForm

    context = {
        'role': 'Staff Tata Usaha',
        'staf': getattr(user, 'staf_core_user', None),
        'total_siswa': Siswa.objects.count(),
        'total_guru': Guru.objects.count(),
        'total_mapel': MataPelajaran.objects.count(),
        'total_jadwal': JadwalPelajaran.objects.count(),
        'tunggakan_keuangan': (
            str(KeuanganSiswa.objects.filter(
                status_lunas=False
            ).count()) + " Berkas"
        ),
        'total_nilai': NilaiRapor.objects.count(),
        'total_presensi': Presensi.objects.count(),
        'total_wali': WaliMurid.objects.count(),
        'total_pendaftaran': Pendaftaran.objects.count(),
        'total_agenda': Agenda.objects.count(),
        'total_berita': Berita.objects.count(),
        'total_pengumuman': Pengumuman.objects.count(),
        'total_prestasi': Prestasi.objects.count(),
        'total_galeri': Galeri.objects.count(),
        'total_ekskul': Ekstrakurikuler.objects.count(),
        'total_dokumen': DokumenUnduhan.objects.count(),
        'total_layanan': LayananAkademik.objects.count(),
        'total_gelombang': PpdbGelombang.objects.count(),
        'total_ppdbsetting': PpdbSetting.objects.count(),
        'total_kontak': KontakSekolah.objects.count(),
        'daftar_jadwal': JadwalPelajaran.objects.select_related(
            'mata_pelajaran', 'guru', 'kelas'
        ).all()[:200],
        'daftar_mapel': MataPelajaran.objects.all(),
        'daftar_nilai': NilaiRapor.objects.select_related(
            'siswa', 'mata_pelajaran'
        ).all()[:200],
        'daftar_presensi': Presensi.objects.select_related(
            'siswa'
        ).all()[:200],
        'daftar_guru': Guru.objects.all(),
        'daftar_wali': WaliMurid.objects.all(),
        'daftar_siswa': Siswa.objects.select_related(
            'kelas', 'wali'
        ).all()[:200],
        'daftar_pendaftaran': Pendaftaran.objects.all()[:200],
        'daftar_agenda': Agenda.objects.all(),
        'daftar_berita': Berita.objects.select_related(
            'penulis'
        ).all()[:100],
        'daftar_pengumuman': Pengumuman.objects.all()[:100],
        'daftar_prestasi': Prestasi.objects.all(),
        'daftar_galeri': Galeri.objects.all()[:100],
        'daftar_ekskul': Ekstrakurikuler.objects.all(),
        'daftar_dokumen': DokumenUnduhan.objects.all(),
        'daftar_layanan': LayananAkademik.objects.all(),
        'daftar_gelombang': PpdbGelombang.objects.all(),
        'daftar_ppdbsetting': PpdbSetting.objects.all(),
        'daftar_kontak': KontakSekolah.objects.all(),
    }
    return render(request, 'akademik/dashboard/staf.html', context)


@login_required
def keuangan_siswa_view(request):
    user = request.user
    if not (user.is_superuser or user.is_staff):
        raise PermissionDenied

    keuangan_list = KeuanganSiswa.objects.all().select_related('siswa')

    q = request.GET.get('q')
    if q:
        keuangan_list = (
            keuangan_list.filter(siswa__nama_lengkap__icontains=q)
            | keuangan_list.filter(jenis_tagihan__icontains=q)
        )

    status = request.GET.get('status')
    if status == 'true':
        keuangan_list = keuangan_list.filter(status_lunas=True)
    elif status == 'false':
        keuangan_list = keuangan_list.filter(status_lunas=False)

    jenis = request.GET.get('jenis')
    if jenis:
        keuangan_list = keuangan_list.filter(jenis_tagihan__iexact=jenis)

    context = {
        'role': 'Staff Tata Usaha',
        'keuangan_list': keuangan_list,
        'total_tagihan': keuangan_list.count(),
        'total_lunas': keuangan_list.filter(status_lunas=True).count(),
        'total_belum_lunas': keuangan_list.filter(
            status_lunas=False
        ).count(),
    }
    return render(
        request,
        'akademik/dashboard/keuangan_siswa.html',
        context
    )


@login_required
def dashboard_bendahara(request):
    return render(
        request,
        'akademik/dashboard/bendahara.html',
        {'role': 'Bendahara'},
    )


@login_required
def dashboard_perpus(request):
    return render(
        request,
        'akademik/dashboard/perpus.html',
        {'role': 'Perpustakaan'},
    )


# ==============================================================================
# 2. MODUL AKADEMIK & KBM GURU
# ==============================================================================

@login_required
def jadwal_pelajaran(request):
    guru = Guru.objects.filter(user=request.user).first()
    jadwal_list = []
    if guru:
        jadwal_list = JadwalPelajaran.objects.filter(
            guru=guru
        ).order_by('hari', 'jam_mulai')
    return render(
        request,
        'akademik/kbm/jadwal.html',
        {'guru': guru, 'jadwal_list': jadwal_list},
    )


@login_required
def jurnal_mengajar(request):
    guru = Guru.objects.filter(user=request.user).first()
    jadwal_guru = []
    jurnal_list = []

    if guru:
        jadwal_guru = JadwalPelajaran.objects.filter(guru=guru)

        if request.method == 'POST':
            jadwal_id = request.POST.get('jadwal')
            materi = request.POST.get('materi')
            kendala = request.POST.get('kendala')
            tindak_lanjut = request.POST.get('tindak_lanjut')

            if jadwal_id and materi:
                jadwal_obj = get_object_or_404(
                    JadwalPelajaran, id=jadwal_id
                )
                JurnalMengajar.objects.create(
                    jadwal=jadwal_obj,
                    materi_pembahasan=materi,
                    kendala_kbm=kendala or '',
                    tindak_lanjut=tindak_lanjut or '',
                )
                messages.success(request, "Jurnal KBM berhasil disimpan!")
                return redirect('akademik:jurnal_mengajar')

        jurnal_list = JurnalMengajar.objects.filter(
            jadwal__guru=guru
        ).select_related('jadwal__mata_pelajaran').order_by('-tanggal')

    context = {
        'guru': guru,
        'jadwal_guru': jadwal_guru,
        'jurnal_list': jurnal_list,
    }
    return render(request, 'akademik/kbm/jurnal.html', context)


@login_required
def hapus_jurnal(request, jurnal_id):
    guru = Guru.objects.filter(user=request.user).first()
    jurnal = get_object_or_404(
        JurnalMengajar, id=jurnal_id, jadwal__guru=guru
    )
    jurnal.delete()
    messages.success(request, "Riwayat Jurnal KBM berhasil dihapus!")
    return redirect('akademik:jurnal_mengajar')


@login_required
def materi_ajar(request):
    guru = Guru.objects.filter(user=request.user).first()
    materi_list = []
    jadwal_guru = []

    if guru:
        semua_jadwal = JadwalPelajaran.objects.filter(
            guru=guru
        ).select_related('mata_pelajaran')
        mapel_dilihat = set()
        for j in semua_jadwal:
            if j.mata_pelajaran_id not in mapel_dilihat:
                mapel_dilihat.add(j.mata_pelajaran_id)
                jadwal_guru.append(j)

        if request.method == 'POST':
            mapel_id = request.POST.get('mata_pelajaran')
            judul = request.POST.get('judul')
            deskripsi = request.POST.get('deskripsi')
            file_dokumen = request.FILES.get('file_materi')
            link_external = request.POST.get('link_external')

            if mapel_id and judul:
                mapel_obj = get_object_or_404(MataPelajaran, id=mapel_id)
                MateriAjar.objects.create(
                    mata_pelajaran=mapel_obj,
                    guru=guru,
                    judul=judul,
                    deskripsi=deskripsi or '',
                    file_materi=file_dokumen,
                    link_external=link_external or None,
                )
                messages.success(
                    request, "Materi '" + judul + "' berhasil diunggah!"
                )
                return redirect('akademik:materi_ajar')

        materi_list = MateriAjar.objects.filter(
            guru=guru
        ).select_related('mata_pelajaran').order_by('-created_at')

    context = {
        'guru': guru,
        'materi_list': materi_list,
        'jadwal_guru': jadwal_guru,
    }
    return render(request, 'akademik/kbm/materi.html', context)


@login_required
def lihat_materi_siswa(request):
    url = request.GET.get('url', '')
    judul = request.GET.get('judul', '')
    if not url:
        return redirect('akademik:dashboard_siswa')
    return render(
        request,
        'akademik/siswa/lihat_materi.html',
        {'url': url, 'judul': judul},
    )


@login_required
def hapus_materi(request, materi_id):
    guru = Guru.objects.filter(user=request.user).first()
    materi = get_object_or_404(MateriAjar, id=materi_id, guru=guru)
    judul_materi = materi.judul
    if materi.file_materi:
        materi.file_materi.delete(save=False)
    materi.delete()
    messages.success(
        request, "Materi '" + judul_materi + "' berhasil dihapus!"
    )
    return redirect('akademik:materi_ajar')


@login_required
def presensi(request):
    guru = Guru.objects.filter(user=request.user).first()
    if not guru:
        messages.error(request, "Akses ditolak!")
        return redirect('akademik:dashboard_staf')

    jadwal_guru = JadwalPelajaran.objects.filter(
        guru=guru
    ).select_related('mata_pelajaran')
    siswa_status_list = []
    jadwal_terpilih = None

    jadwal_id = request.GET.get('jadwal')
    if jadwal_id:
        jadwal_terpilih = get_object_or_404(
            JadwalPelajaran, id=jadwal_id, guru=guru
        )
        para_siswa = Siswa.objects.filter(
            kelas=jadwal_terpilih.kelas
        ).order_by('nama_lengkap')
        for s in para_siswa:
            presensi_hari_ini = Presensi.objects.filter(
                jadwal=jadwal_terpilih,
                siswa=s,
                tanggal=date.today()
            ).first()
            perilaku_hari_ini = NilaiPerilaku.objects.filter(
                siswa=s,
                guru=guru,
                jadwal=jadwal_terpilih,
                tanggal=date.today()
            ).first()
            siswa_status_list.append({
                'siswa': s,
                'status_terakhir': (
                    presensi_hari_ini.status if presensi_hari_ini else None
                ),
                'keterangan': (
                    presensi_hari_ini.keterangan
                    if presensi_hari_ini else ''
                ),
                'perilaku_terakhir': (
                    perilaku_hari_ini.kategori
                    if perilaku_hari_ini else None
                ),
                'catatan_perilaku': (
                    perilaku_hari_ini.catatan
                    if perilaku_hari_ini else ''
                ),
                # Tampilkan skor global (dari semua guru) untuk referensi
                'skor_global': hitung_nilai_perilaku_siswa(s),
            })

    if request.method == 'POST':
        jadwal_obj = get_object_or_404(
            JadwalPelajaran,
            id=request.POST.get('jadwal_id'),
            guru=guru,
        )
        for s in Siswa.objects.filter(kelas=jadwal_obj.kelas):
            status_absen = request.POST.get('status_' + str(s.pk))
            keterangan_absen = request.POST.get(
                'keterangan_' + str(s.pk), ''
            )
            if status_absen:
                Presensi.objects.update_or_create(
                    jadwal=jadwal_obj,
                    siswa=s,
                    tanggal=date.today(),
                    defaults={
                        'status': status_absen,
                        'keterangan': keterangan_absen or None,
                    },
                )

            perilaku_val = request.POST.get(
                'perilaku_' + str(s.pk), ''
            ).strip()
            catatan_val = request.POST.get(
                'catatan_perilaku_' + str(s.pk), ''
            ).strip()
            if perilaku_val in ('Baik', 'Cukup', 'Kurang'):
                NilaiPerilaku.objects.update_or_create(
                    siswa=s,
                    guru=guru,
                    jadwal=jadwal_obj,
                    tanggal=date.today(),
                    defaults={
                        'kategori': perilaku_val,
                        'catatan': catatan_val or None,
                    },
                )

        messages.success(
            request,
            "Presensi & penilaian perilaku kelas "
            + jadwal_obj.kelas.nama_kelas
            + " selesai!",
        )
        return redirect('akademik:presensi')

    context = {
        'guru': guru,
        'jadwal_guru': jadwal_guru,
        'siswa_status_list': siswa_status_list,
        'jadwal_terpilih': jadwal_terpilih,
        'hari_ini': date.today(),
        'PERILAKU_CHOICES': ['Baik', 'Cukup', 'Kurang'],
    }
    return render(request, 'akademik/penilaian/presensi.html', context)


@login_required
def input_nilai(request):
    guru = Guru.objects.filter(user=request.user).first()
    if not guru:
        messages.error(request, "Akses ditolak!")
        return redirect('akademik:dashboard_staf')

    jadwal_guru = JadwalPelajaran.objects.filter(
        guru=guru
    ).select_related('mata_pelajaran')
    siswa_nilai_list = []
    jadwal_terpilih = None

    jadwal_id = request.GET.get('jadwal')
    if jadwal_id:
        jadwal_terpilih = get_object_or_404(
            JadwalPelajaran, id=jadwal_id, guru=guru
        )
        for s in Siswa.objects.filter(
            kelas=jadwal_terpilih.kelas
        ).order_by('nama_lengkap'):
            nilai_obj = NilaiRapor.objects.filter(
                siswa=s,
                mata_pelajaran=jadwal_terpilih.mata_pelajaran,
            ).first()
            perilaku_skor = hitung_nilai_perilaku_siswa(s)
            siswa_nilai_list.append({
                'siswa': s,
                'tugas': nilai_obj.nilai_tugas if nilai_obj else 0,
                'uts': nilai_obj.nilai_uts if nilai_obj else 0,
                'uas': nilai_obj.nilai_uas if nilai_obj else 0,
                'perilaku': perilaku_skor,
                'nilai_akhir': hitung_nilai_akhir(
                    nilai_obj.nilai_tugas if nilai_obj else 0,
                    nilai_obj.nilai_uts if nilai_obj else 0,
                    nilai_obj.nilai_uas if nilai_obj else 0,
                    perilaku_skor,
                ),
                'keterangan': nilai_obj.keterangan if nilai_obj else '',
            })

    if request.method == 'POST':
        jadwal_obj = get_object_or_404(
            JadwalPelajaran,
            id=request.POST.get('jadwal_id'),
            guru=guru,
        )
        for s in Siswa.objects.filter(kelas=jadwal_obj.kelas):
            tugas_val = int(request.POST.get('tugas_' + str(s.pk), 0))
            uts_val = int(request.POST.get('uts_' + str(s.pk), 0))
            uas_val = int(request.POST.get('uas_' + str(s.pk), 0))
            ket_val = request.POST.get('keterangan_' + str(s.pk), '')
            perilaku_skor = hitung_nilai_perilaku_siswa(s)
            # Formula: Tugas(35%) + UTS(25%) + UAS(25%) + Perilaku(15%)
            nilai_akhir = hitung_nilai_akhir(
                tugas_val, uts_val, uas_val, perilaku_skor
            )
            NilaiRapor.objects.update_or_create(
                siswa=s,
                mata_pelajaran=jadwal_obj.mata_pelajaran,
                defaults={
                    'nilai_tugas': tugas_val,
                    'nilai_uts': uts_val,
                    'nilai_uas': uas_val,
                    'nilai_perilaku': perilaku_skor,
                    'nilai_angka': nilai_akhir,
                    'keterangan': ket_val,
                },
            )
        messages.success(
            request,
            "Evaluasi nilai kelas "
            + jadwal_obj.kelas.nama_kelas
            + " berhasil disimpan!",
        )
        return redirect('akademik:input_nilai')

    context = {
        'guru': guru,
        'jadwal_guru': jadwal_guru,
        'siswa_nilai_list': siswa_nilai_list,
        'jadwal_terpilih': jadwal_terpilih,
    }
    return render(request, 'akademik/penilaian/nilai.html', context)


# ==============================================================================
# 2b. INPUT NILAI PERILAKU MANDIRI
# ==============================================================================

@login_required
def input_perilaku(request):
    """
    Guru bisa memberi / memperbarui nilai perilaku siswa
    untuk jadwal dan tanggal tertentu secara mandiri.
    """
    guru = Guru.objects.filter(user=request.user).first()
    if not guru:
        messages.error(request, "Akses ditolak!")
        return redirect('akademik:dashboard_staf')

    jadwal_guru = JadwalPelajaran.objects.filter(
        guru=guru
    ).select_related('mata_pelajaran', 'kelas')

    siswa_perilaku_list = []
    jadwal_terpilih = None
    tanggal_terpilih = date.today()

    jadwal_id = request.GET.get('jadwal')
    tgl_param = request.GET.get('tanggal', '')
    if tgl_param:
        try:
            from datetime import datetime
            tanggal_terpilih = datetime.strptime(
                tgl_param, '%Y-%m-%d'
            ).date()
        except ValueError:
            tanggal_terpilih = date.today()

    if jadwal_id:
        jadwal_terpilih = get_object_or_404(
            JadwalPelajaran, id=jadwal_id, guru=guru
        )
        for s in Siswa.objects.filter(
            kelas=jadwal_terpilih.kelas
        ).order_by('nama_lengkap'):
            existing = NilaiPerilaku.objects.filter(
                siswa=s,
                guru=guru,
                jadwal=jadwal_terpilih,
                tanggal=tanggal_terpilih,
            ).first()
            siswa_perilaku_list.append({
                'siswa': s,
                'kategori': existing.kategori if existing else None,
                'catatan': existing.catatan if existing else '',
                'skor_global': hitung_nilai_perilaku_siswa(s),
            })

    if request.method == 'POST':
        jadwal_obj = get_object_or_404(
            JadwalPelajaran,
            id=request.POST.get('jadwal_id'),
            guru=guru,
        )
        tgl_str = request.POST.get('tanggal', str(date.today()))
        try:
            from datetime import datetime
            tgl_simpan = datetime.strptime(tgl_str, '%Y-%m-%d').date()
        except ValueError:
            tgl_simpan = date.today()

        disimpan = 0
        for s in Siswa.objects.filter(kelas=jadwal_obj.kelas):
            kategori_val = request.POST.get(
                'perilaku_' + str(s.pk), ''
            ).strip()
            catatan_val = request.POST.get(
                'catatan_perilaku_' + str(s.pk), ''
            ).strip()
            if kategori_val in ('Baik', 'Cukup', 'Kurang'):
                NilaiPerilaku.objects.update_or_create(
                    siswa=s,
                    guru=guru,
                    jadwal=jadwal_obj,
                    tanggal=tgl_simpan,
                    defaults={
                        'kategori': kategori_val,
                        'catatan': catatan_val or None,
                    },
                )
                disimpan += 1

        messages.success(
            request,
            str(disimpan) + " penilaian perilaku berhasil disimpan.",
        )
        return redirect('akademik:input_perilaku')

    context = {
        'guru': guru,
        'jadwal_guru': jadwal_guru,
        'siswa_perilaku_list': siswa_perilaku_list,
        'jadwal_terpilih': jadwal_terpilih,
        'tanggal_terpilih': tanggal_terpilih,
        'PERILAKU_CHOICES': ['Baik', 'Cukup', 'Kurang'],
    }
    return render(request, 'akademik/penilaian/perilaku.html', context)


# ==============================================================================
# 3. E-LEARNING — TUGAS & KUIS
# ==============================================================================

# ✅ GANTI DENGAN INI
@login_required
def e_learning(request):
    from django.utils import timezone

    guru = Guru.objects.filter(user=request.user).first()
    if not guru:
        siswa = Siswa.objects.filter(user=request.user).first()
        if siswa:
            return redirect('akademik:dashboard_siswa')
        return redirect('web_publik:index')

    semua_jadwal = JadwalPelajaran.objects.filter(
        guru=guru
    ).select_related('mata_pelajaran').order_by('hari', 'jam_mulai')

    # ── AUTO-DELETE: hapus semua tugas milik guru ini yang sudah lewat deadline ──
    terhapus = TugasKuis.objects.filter(
        guru=guru,
        batas_waktu__lt=timezone.now()
    )
    jumlah_terhapus = terhapus.count()
    terhapus.delete()
    if jumlah_terhapus > 0:
        messages.info(
            request,
            f"{jumlah_terhapus} tugas/kuis otomatis dihapus karena deadline telah lewat."
        )

    if request.method == 'POST':
        jenis    = request.POST.get('jenis', '').strip()
        mapel_id = request.POST.get('mata_pelajaran', '').strip()
        judul    = request.POST.get('judul', '').strip()
        deskripsi = request.POST.get('deskripsi', '').strip()
        batas    = request.POST.get('batas_waktu', '').strip()

        if jenis and mapel_id and judul and batas:
            mapel_obj = get_object_or_404(MataPelajaran, id=mapel_id)
            jadwal_terkait = semua_jadwal.filter(
                mata_pelajaran=mapel_obj
            ).first()
            TugasKuis.objects.create(
                guru=guru,
                mata_pelajaran=mapel_obj,
                jadwal=jadwal_terkait,
                judul=judul,
                deskripsi=deskripsi or None,
                jenis=jenis,
                batas_waktu=batas,
            )
            label = 'Tugas' if jenis == 'Tugas' else 'Kuis'
            messages.success(
                request,
                label + " '" + judul + "' berhasil diterbitkan!"
            )
            return redirect('akademik:e_learning')
        else:
            messages.error(
                request,
                "Harap lengkapi semua field sebelum menerbitkan."
            )

    tugas_list = TugasKuis.objects.filter(
        guru=guru
    ).select_related('mata_pelajaran', 'jadwal').order_by('-created_at')

    context = {
        'guru': guru,
        'jadwal_guru': list(semua_jadwal),
        'tugas_list': tugas_list,
    }
    return render(request, 'akademik/elearning/tugas.html', context)


# ✅ TAMBAHKAN FUNGSI BARU INI tepat di bawah fungsi e_learning
@login_required
def hapus_tugas(request, tugas_id):
    guru = Guru.objects.filter(user=request.user).first()
    if not guru:
        messages.error(request, "Akses ditolak.")
        return redirect('web_publik:index')

    tugas = get_object_or_404(TugasKuis, id=tugas_id, guru=guru)
    judul = tugas.judul
    tugas.delete()
    messages.success(request, f"Tugas/Kuis '{judul}' berhasil dihapus.")
    return redirect('akademik:e_learning')


@login_required
def kirim_jawaban_siswa(request):
    if request.method != 'POST':
        return redirect('akademik:dashboard_siswa')

    siswa = Siswa.objects.filter(user=request.user).first()
    if not siswa:
        return JsonResponse(
            {'ok': False, 'msg': 'Akses ditolak.'}, status=403
        )

    tugas_id = request.POST.get('tugas_id')
    file_jawaban = request.FILES.get('file_jawaban')
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    )

    if not tugas_id or not file_jawaban:
        if is_ajax:
            return JsonResponse(
                {'ok': False, 'msg': 'File jawaban wajib dipilih.'},
                status=400,
            )
        messages.error(
            request, "Gagal mengirim. Pastikan file sudah dipilih."
        )
        return redirect('akademik:dashboard_siswa')

    tugas_obj = get_object_or_404(TugasKuis, id=tugas_id)
    jawaban, created = JawabanSiswa.objects.update_or_create(
        tugas=tugas_obj,
        siswa=siswa,
        defaults={'file_jawaban': file_jawaban},
    )
    label = "dikirim" if created else "diperbarui"
    if is_ajax:
        return JsonResponse({
            'ok': True,
            'msg': 'Jawaban "' + tugas_obj.judul + '" berhasil ' + label + '!',
        })
    messages.success(
        request,
        'Jawaban "' + tugas_obj.judul + '" berhasil ' + label + '!',
    )
    return redirect('akademik:dashboard_siswa')


@login_required
def lihat_jawaban_guru(request, tugas_id):
    guru = Guru.objects.filter(user=request.user).first()
    if not guru:
        messages.error(request, "Akses ditolak.")
        return redirect('web_publik:index')

    tugas = get_object_or_404(TugasKuis, id=tugas_id, guru=guru)

    if request.method == 'POST':
        jawaban_id = request.POST.get('jawaban_id')
        nilai_input = request.POST.get('nilai', '').strip()
        catatan_guru = request.POST.get('catatan_guru', '').strip()

        if jawaban_id:
            jwb = get_object_or_404(
                JawabanSiswa, id=jawaban_id, tugas=tugas
            )
            try:
                jwb.nilai = int(nilai_input) if nilai_input else None
                jwb.catatan_guru = catatan_guru or None
                jwb.save()
                messages.success(
                    request,
                    "Nilai untuk "
                    + jwb.siswa.nama_lengkap
                    + " berhasil disimpan.",
                )
            except ValueError:
                messages.error(
                    request, "Nilai tidak valid, harus angka 0-100."
                )
        return redirect('akademik:lihat_jawaban_guru', tugas_id=tugas_id)

    jawaban_list = JawabanSiswa.objects.filter(
        tugas=tugas
    ).select_related('siswa', 'siswa__kelas').order_by('-dikirim_at')

    total_siswa = 0
    sudah_dinilai = jawaban_list.exclude(nilai=None).count()
    if tugas.jadwal:
        total_siswa = Siswa.objects.filter(
            kelas=tugas.jadwal.kelas
        ).count()

    sudah_kirim = jawaban_list.count()
    belum_kirim = max(total_siswa - sudah_kirim, 0)
    nilai_terisi = [j.nilai for j in jawaban_list if j.nilai is not None]
    rata_nilai = (
        round(sum(nilai_terisi) / len(nilai_terisi), 1)
        if nilai_terisi else None
    )

    context = {
        'guru': guru,
        'tugas': tugas,
        'jawaban_list': jawaban_list,
        'total_siswa': total_siswa,
        'sudah_kirim': sudah_kirim,
        'belum_kirim': belum_kirim,
        'sudah_dinilai': sudah_dinilai,
        'rata_nilai': rata_nilai,
    }
    return render(request, 'akademik/elearning/lihat_jawaban.html', context)


@login_required
def detail_tugas_siswa(request, tugas_id):
    tugas = get_object_or_404(TugasKuis, id=tugas_id)
    data = {
        'judul': tugas.judul,
        'jenis': tugas.get_jenis_display(),
        'mapel': tugas.mata_pelajaran.nama,
        'kelas': (
            tugas.jadwal.kelas.nama_kelas if tugas.jadwal else '-'
        ),
        'deadline': (
            tugas.batas_waktu.strftime('%d %B %Y, %H:%M') + ' WIB'
        ),
        'deskripsi': tugas.deskripsi or 'Tidak ada deskripsi tambahan.',
    }
    return JsonResponse(data)


# ==============================================================================
# 4. MODUL HALAMAN STANDALONE SISWA
# ==============================================================================

@login_required
def jadwal_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    jadwal_list = []
    if siswa and siswa.kelas:
        jadwal_list = JadwalPelajaran.objects.filter(
            kelas=siswa.kelas
        ).order_by('hari', 'jam_mulai')
    return render(
        request,
        'akademik/siswa/jadwal_siswa.html',
        {'siswa': siswa, 'jadwal_list': jadwal_list, 'role': 'Siswa'},
    )


@login_required
def presensi_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    riwayat_presensi = []
    if siswa:
        riwayat_presensi = Presensi.objects.filter(
            siswa=siswa
        ).select_related('jadwal__mata_pelajaran').order_by('-tanggal')
    return render(
        request,
        'akademik/siswa/presensi_siswa.html',
        {
            'siswa': siswa,
            'riwayat_presensi': riwayat_presensi,
            'role': 'Siswa',
        },
    )


@login_required
def elearning_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    materi_list = []
    if siswa and siswa.kelas:
        mapel_ids = JadwalPelajaran.objects.filter(
            kelas=siswa.kelas
        ).values_list('mata_pelajaran_id', flat=True)
        materi_list = MateriAjar.objects.filter(
            mata_pelajaran_id__in=mapel_ids
        ).select_related('mata_pelajaran', 'guru').order_by('-created_at')
    return render(
        request,
        'akademik/siswa/elearning_siswa.html',
        {'siswa': siswa, 'materi_list': materi_list, 'role': 'Siswa'},
    )


@login_required
def hasil_studi_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    nilai_list = []
    if siswa:
        nilai_list = NilaiRapor.objects.filter(
            siswa=siswa
        ).select_related('mata_pelajaran').order_by('mata_pelajaran__nama')
    return render(
        request,
        'akademik/siswa/hasil_studi_siswa.html',
        {'siswa': siswa, 'nilai_list': nilai_list, 'role': 'Siswa'},
    )


@login_required
def e_rapor(request):
    guru = Guru.objects.filter(user=request.user).first()

    mapel_ids = (
        JadwalPelajaran.objects.filter(
            guru=guru
        ).values_list('mata_pelajaran_id', flat=True).distinct()
        if guru else []
    )

    nilai_rapor_list = (
        NilaiRapor.objects.filter(
            mata_pelajaran_id__in=mapel_ids
        ).select_related('siswa', 'mata_pelajaran').order_by(
            'mata_pelajaran__nama', 'siswa__nama_lengkap'
        )
        if mapel_ids else []
    )

    context = {
        'guru': guru,
        'nilai_rapor_list': nilai_rapor_list,
    }
    return render(request, 'akademik/penilaian/raport.html', context)


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Anda berhasil keluar sistem secara aman.")
    return redirect('web_publik:index')


@login_required
def ubah_password_siswa(request):
    return render(
        request,
        'akademik/siswa/ubah_password.html',
        {'role': 'Siswa'},
    )


# ==============================================================================
# 5. API ENDPOINTS UNTUK TABEL MELAYANG (AJAX MODAL POP-UP)
# ==============================================================================

@login_required
def api_jadwal_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    jadwal_list = []
    if siswa and siswa.kelas:
        jadwal_list = JadwalPelajaran.objects.filter(
            kelas=siswa.kelas
        ).order_by('hari', 'jam_mulai')
    return render(
        request,
        'akademik/siswa/tabel_jadwal.html',
        {'jadwal_list': jadwal_list},
    )


@login_required
def api_presensi_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    riwayat_presensi = []
    if siswa:
        riwayat_presensi = Presensi.objects.filter(
            siswa=siswa
        ).select_related('jadwal__mata_pelajaran').order_by('-tanggal')
    return render(
        request,
        'akademik/siswa/tabel_presensi.html',
        {'riwayat_presensi': riwayat_presensi},
    )


@login_required
def api_nilai_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    nilai_list = []
    if siswa:
        nilai_list = NilaiRapor.objects.filter(
            siswa=siswa
        ).select_related('mata_pelajaran').order_by('mata_pelajaran__nama')
    return render(
        request,
        'akademik/siswa/tabel_nilai.html',
        {'nilai_list': nilai_list},
    )


@login_required
def api_elearning_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    materi_list = []
    tugas_list = []

    if siswa and siswa.kelas:
        mapel_ids = JadwalPelajaran.objects.filter(
            kelas=siswa.kelas
        ).values_list('mata_pelajaran_id', flat=True)
        materi_list = MateriAjar.objects.filter(
            mata_pelajaran_id__in=mapel_ids
        ).select_related('mata_pelajaran', 'guru').order_by('-created_at')
        tugas_list = TugasKuis.objects.filter(
            jadwal__kelas=siswa.kelas
        ).select_related(
            'jadwal__mata_pelajaran', 'jadwal__guru'
        ).order_by('-id')

    context = {
        'siswa': siswa,
        'materi_list': materi_list,
        'tugas_list': tugas_list,
    }
    return render(
        request, 'akademik/siswa/tabel_elearning.html', context
    )

@login_required
def api_keuangan_siswa(request):
    siswa = Siswa.objects.filter(user=request.user).first()
    tagihan_list = []
    if siswa:
        tagihan_list = AdministrasiSiswa.objects.filter(
            siswa=siswa
        ).order_by('-tanggal_perubahan')
    return render(
        request,
        'akademik/siswa/tabel_keuangan.html',
        {'tagihan_list': tagihan_list},
    )
