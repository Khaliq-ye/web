# Jalur file: C:\web\akademik\apps.py

from django.apps import AppConfig


class AkademikConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'akademik'
    verbose_name       = 'Manajemen Akademik'

    def ready(self):
        # Hubungkan signal create_academic_groups ke event post_migrate
        from django.db.models.signals import post_migrate
        from akademik.signals import create_academic_groups

        post_migrate.connect(create_academic_groups, sender=self)