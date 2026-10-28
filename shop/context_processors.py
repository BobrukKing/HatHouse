from .models import Category, StoreSettings


def store_settings(request):
    settings = StoreSettings.objects.first()
    return {"store_settings": settings, "categories": Category.objects.all()}
