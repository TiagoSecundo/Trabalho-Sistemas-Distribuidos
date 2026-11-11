from django.shortcuts import get_object_or_404, render

from .forms import MonografiaForm
from monografias.models import Monografia

# Create your views here.
def index(request):
    monografias = Monografia.objects.select_related('discente').order_by('-data_publicacao')
    context = {
        'monografias': monografias,
    }
    return render(request, 'monografias.html', context)


def adicionar(request):
    form = MonografiaForm()
    if request.method == "POST":
        form = MonografiaForm(request.POST)
        if form.is_valid():
            form.save()
            form = MonografiaForm()
    return render(request, "adicionar_monografia.html", {"form": form})
               

def detalhes(request, pk):
    monografia = get_object_or_404(
        Monografia.objects.select_related("discente", "orientador", "coorientador"),
        pk=pk,
    )
    context = {
        "monografia": monografia,
    }

    return render(request, "detalhes.html", context)
