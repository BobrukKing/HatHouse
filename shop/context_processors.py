from .models import Category, Order, StoreSettings


def store_settings(request):
    settings = StoreSettings.objects.first()
    return {"store_settings": settings, "categories": Category.objects.all()}


def pending_shipping_orders(request):
    can_view_orders = (
        request.user.is_authenticated
        and request.user.is_staff
        and request.user.has_perm("shop.view_order")
    )
    count = Order.objects.filter(status=Order.Status.PAID).count() if can_view_orders else 0
    return {"pending_shipping_count": count}
