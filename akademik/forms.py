from django import forms
from core.models import Siswa

class UpdateBiodataSiswaForm(forms.ModelForm):
    class Meta:
        model  = Siswa
        fields = ['tempat_lahir', 'tanggal_lahir']
        widgets = {
            'tempat_lahir': forms.TextInput(attrs={
                'class'      : 'form-control',
                'placeholder': 'Contoh: Lombok Timur',
            }),
            'tanggal_lahir': forms.DateInput(attrs={
                'class': 'form-control',
                'type' : 'date',  # Memunculkan date picker di browser
            }),

        }
        labels = {
            'tempat_lahir'  : 'Tempat Lahir',
            'tanggal_lahir' : 'Tanggal Lahir',
        }

class EditDataSiswaAdminForm(forms.ModelForm):
    class Meta:
        model  = Siswa
        fields = [
            'nisn', 'nama_lengkap',
            'tempat_lahir', 'tanggal_lahir',
        ]
        widgets = {
            'nisn': forms.TextInput(attrs={
                'class'    : 'form-control',
                'maxlength': '20',
            }),
            'nama_lengkap': forms.TextInput(attrs={
                'class': 'form-control',
            }),
            'tempat_lahir': forms.TextInput(attrs={
                'class'      : 'form-control',
                'placeholder': 'Contoh: Lombok Timur',
            }),
            'tanggal_lahir': forms.DateInput(attrs={
                'class': 'form-control',
                'type' : 'date',
            }),
            'kelas': forms.Select(attrs={
                'class': 'form-select',
            }),
            'wali': forms.Select(attrs={
                'class': 'form-select',
            }),
        }
        labels = {
            'nisn'          : 'NISN',
            'nama_lengkap'  : 'Nama Lengkap',
            'tempat_lahir'  : 'Tempat Lahir',
            'tanggal_lahir' : 'Tanggal Lahir',
            'kelas'         : 'Kelas',
            'wali'          : 'Akun Wali Murid',
        }

    def clean_nisn(self):
        """Validasi NISN: harus 10 digit angka dan unik (kecuali milik siswa itu sendiri)"""
        nisn = self.cleaned_data.get('nisn', '').strip()
        if not nisn.isdigit() or len(nisn) != 10:
            raise forms.ValidationError('NISN harus tepat 10 digit angka.')

        qs = Siswa.objects.filter(nisn=nisn)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(f'NISN {nisn} sudah digunakan siswa lain.')

        return nisn