from django import forms
from .models import Persona, ScheduledPost

class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = ['username', 'password', 'biography', 'avatar']

class ScheduledPostForm(forms.ModelForm):
    class Meta:
        model = ScheduledPost
        fields = ['caption', 'image', 'time']
