from django.shortcuts import render
from .models import MenuItem

def menu_list(request):
    menu_items = MenuItem.objects.all().order_by('category', 'name')
    context = {
        'menu_items': menu_items,
        'categories': MenuItem._meta.get_field('category').choices
    }
    return render(request, 'core/menu.html', context)
