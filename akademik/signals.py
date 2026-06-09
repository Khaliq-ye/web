# Jalur file: C:\web\akademik\signals.py

from django.db.models.signals import post_migrate
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def create_academic_groups(sender, **kwargs):
    """
    Otomatis membuat Group dan memberikan hak akses
    saat pertama kali migrate dijalankan.
    Dipanggil oleh post_migrate signal dari AkademikConfig.
    """

    # ── GROUP 1: Staff TU ─────────────────────────────────────────────
    staff_group, _ = Group.objects.get_or_create(name='Staff TU')

    models_tata_usaha = ['matapelajaran', 'jadwalpelajaran', 'administrasisiswa']

    for model_name in models_tata_usaha:
        try:
            content_type = ContentType.objects.get(
                app_label='akademik',
                model=model_name
            )
            permissions = Permission.objects.filter(content_type=content_type)
            for perm in permissions:
                staff_group.permissions.add(perm)
        except ContentType.DoesNotExist:
            continue

    # ── GROUP 2: Guru ─────────────────────────────────────────────────
    guru_group, _ = Group.objects.get_or_create(name='Guru')

    models_guru = ['jurnalmengajar', 'materiajar', 'presensi', 'tugaskuis', 'nilairapor']

    for model_name in models_guru:
        try:
            content_type = ContentType.objects.get(
                app_label='akademik',
                model=model_name
            )
            permissions = Permission.objects.filter(content_type=content_type)
            for perm in permissions:
                guru_group.permissions.add(perm)
        except ContentType.DoesNotExist:
            continue

    # ── GROUP 3: Siswa ────────────────────────────────────────────────
    # Siswa hanya boleh view, tidak boleh add/change/delete
    siswa_group, _ = Group.objects.get_or_create(name='Siswa')

    models_siswa = ['nilairapor', 'presensi', 'tugaskuis', 'materiajar']

    for model_name in models_siswa:
        try:
            content_type = ContentType.objects.get(
                app_label='akademik',
                model=model_name
            )
            # Hanya permission 'view_*' saja
            permissions = Permission.objects.filter(
                content_type=content_type,
                codename__startswith='view_'
            )
            for perm in permissions:
                siswa_group.permissions.add(perm)
        except ContentType.DoesNotExist:
            continue

    # ── GROUP 4: Wali Murid ───────────────────────────────────────────
    wali_group, _ = Group.objects.get_or_create(name='Wali Murid')

    models_wali = ['nilairapor', 'presensi']

    for model_name in models_wali:
        try:
            content_type = ContentType.objects.get(
                app_label='akademik',
                model=model_name
            )
            permissions = Permission.objects.filter(
                content_type=content_type,
                codename__startswith='view_'
            )
            for perm in permissions:
                wali_group.permissions.add(perm)
        except ContentType.DoesNotExist:
            continue

    # ── GROUP 5: Staf Keuangan ────────────────────────────────────────
    keuangan_group, _ = Group.objects.get_or_create(name='Staf Keuangan')

    try:
        ct_keuangan = ContentType.objects.get(
            app_label='core',
            model='keuangansiswa'
        )
        for perm in Permission.objects.filter(content_type=ct_keuangan):
            keuangan_group.permissions.add(perm)
    except ContentType.DoesNotExist:
        pass