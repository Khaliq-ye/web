# ============================================================
# PATCH: core/views.py
# Tambahkan view toggle_lunas dan perbaiki manajemen_keuangan
# ============================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from core.models import KeuanganSiswa


def is_staf_keuangan(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    grup_user = [g.name.lower().strip() for g in user.groups.all()]
    return any(g in grup_user for g in ('staf_keuangan', 'staf keuangan', 'staff keuangan'))


@login_required
def dashboard(request):
    return render(request, 'core/dashboard.html')


@login_required
def data_siswa(request):
    return render(request, 'core/siswa.html')


@login_required
def data_guru(request):
    return render(request, 'core/guru.html')


@login_required
def manajemen_keuangan(request):
    if not is_staf_keuangan(request.user):
        raise PermissionDenied

    keuangan_queryset = KeuanganSiswa.objects.select_related('siswa').all()

    search_query  = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    jenis_filter  = request.GET.get('jenis', '')

    if search_query:
        keuangan_queryset = keuangan_queryset.filter(
            siswa__nama_lengkap__icontains=search_query
        ) | keuangan_queryset.filter(
            siswa__nisn__icontains=search_query
        )

    if status_filter:
        keuangan_queryset = keuangan_queryset.filter(
            status_lunas=(status_filter == 'true')
        )

    if jenis_filter:
        keuangan_queryset = keuangan_queryset.filter(jenis_tagihan=jenis_filter)

    total_nominal = keuangan_queryset.aggregate(total=Sum('jumlah'))['total'] or 0

    # Daftar jenis tagihan unik untuk dropdown filter
    jenis_tagihan_list = KeuanganSiswa.objects.values_list(
        'jenis_tagihan', flat=True
    ).distinct().order_by('jenis_tagihan')

    context = {
        'keuangan_list'     : keuangan_queryset,
        'total_tagihan'     : keuangan_queryset.count(),
        'total_lunas'       : keuangan_queryset.filter(status_lunas=True).count(),
        'total_belum_lunas' : keuangan_queryset.filter(status_lunas=False).count(),
        'total_nominal'     : f"Rp {total_nominal:,.0f}".replace(",", "."),
        'jenis_tagihan_list': jenis_tagihan_list,
    }
    return render(request, 'core/keuangan_siswa.html', context)


@login_required
def toggle_lunas(request, pk):
    """Toggle status lunas/belum lunas langsung dari dashboard keuangan."""
    if not is_staf_keuangan(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        tagihan = get_object_or_404(KeuanganSiswa, pk=pk)
        tagihan.status_lunas = not tagihan.status_lunas
        tagihan.save()

    return redirect('core:keuangan_siswa')


@login_required
def inventaris(request):
    return render(request, 'core/inventaris.html')