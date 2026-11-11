from django import forms

from .models import Monografia


class MonografiaForm(forms.ModelForm):
    class Meta:
        model = Monografia
        fields = "__all__"
        widgets = {
            "data_publicacao": forms.DateInput(attrs={"type": "date"}),
        }
