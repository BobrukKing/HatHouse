import base64
import hashlib
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.crypto import constant_time_compare, get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .forms import CheckoutForm, RegistrationForm
from .models import Category, Order, OrderItem, Product, StorePage

User = get_user_model()


def _get_google_user(user_info):
    email = (user_info.get("email") or "").strip().lower()
    if not email:
        raise ValueError("Google не передав email.")

    user = User.objects.filter(email__iexact=email).first()
    if user is not None:
        return user

    base_name = (user_info.get("given_name") or user_info.get("name") or email.split("@")[0] or "google_user").strip()
    base_name = "".join(ch for ch in base_name if ch.isalnum() or ch in "._-") or "google_user"
    username = base_name[:30] or "google_user"
    suffix = 1
    while User.objects.filter(username__iexact=username).exists():
        username = f"{base_name[:24]}{suffix}"
        suffix += 1

    user = User.objects.create_user(
        username=username,
        email=email,
        password=get_random_string(32),
    )
    user.first_name = (user_info.get("given_name") or "").strip()
    user.last_name = (user_info.get("family_name") or "").strip()
    user.save(update_fields=["first_name", "last_name"])
    return user


def google_login(request):
    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    if not client_id:
        messages.info(request, "Google-вхід ще не налаштований. Додайте Google OAuth credentials у .env.")
        return redirect("login")

    state = get_random_string(32)
    request.session["google_oauth_state"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/google-callback/"),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": state,
    }
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")


def google_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    stored_state = request.session.get("google_oauth_state")

    if not code or not state or state != stored_state:
        messages.error(request, "Google OAuth повернув некоректний стан або код. Спробуйте ще раз.")
        return redirect("login")

    request.session.pop("google_oauth_state", None)

    client_id = getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
    redirect_uri = getattr(settings, "GOOGLE_OAUTH_REDIRECT_URI", "http://127.0.0.1:8000/google-callback/")

    if not client_id or not client_secret:
        messages.info(request, "Google-вхід ще не налаштований. Додайте Google OAuth credentials у .env.")
        return redirect("login")

    try:
        token_response = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        access_token = token_data.get("access_token")
        if not access_token:
            raise ValueError("Google не повернув access_token.")

        user_info_response = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            params={"access_token": access_token},
            timeout=30,
        )
        user_info_response.raise_for_status()
        user_info = user_info_response.json()

        user = _get_google_user(user_info)
        user.backend = "django.contrib.auth.backends.ModelBackend"
        login(request, user)
        return redirect("catalog")
    except requests.RequestException:
        messages.error(request, "Не вдалося зв’язатися з Google. Спробуйте пізніше.")
        return redirect("login")
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("login")


def catalog(request):
    categories = Category.objects.all()
    products = Product.objects.select_related("category").prefetch_related("photos")
    selected_category = request.GET.get("category", "all")
    search_query = request.GET.get("q", "").strip()
    category = None
    if selected_category != "all":
        category = categories.filter(slug=selected_category).first()
        if category:
            products = products.filter(Q(category=category) | Q(bonus_categories=category)).distinct()
        else:
            selected_category = "all"
            products = Product.objects.select_related("category").prefetch_related("photos")
    if search_query:
        products = products.filter(name__icontains=search_query)

    try:
        per_page = int(request.GET.get("per_page", "12"))
    except ValueError:
        per_page = 12
    if per_page not in (12, 24, 36):
        per_page = 12

    page = Paginator(products, per_page).get_page(request.GET.get("page"))
    return render(request, "shop/catalog.html", {
        "categories": categories,
        "products": page,
        "page_obj": page,
        "selected_category": selected_category,
        "search_query": search_query,
        "per_page": per_page,
        "catalog_title": "Каталог головних уборів" if selected_category == "all" else f"Каталог: {category.name}",
    })


def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("photos"), id=product_id
    )
    return render(request, "shop/product_detail.html", {"product": product})


def static_page(request, slug):
    page = get_object_or_404(StorePage, slug=slug)
    return render(request, "shop/static_page.html", {
        "page": page,
        "paragraphs": [paragraph for paragraph in page.content.split("\n\n") if paragraph.strip()],
    })


def _resolve_checkout_cart(cart_data):
    if not isinstance(cart_data, list) or not cart_data or len(cart_data) > 50:
        return None

    quantities = {}
    for item in cart_data:
        if not isinstance(item, dict):
            return None
        raw_id = item.get("id")
        quantity = item.get("quantity")
        if isinstance(raw_id, bool) or not str(raw_id).isdigit() or len(str(raw_id)) > 12:
            return None
        if type(quantity) is not int or quantity < 1 or quantity > 99:
            return None
        product_id = int(raw_id)
        quantities[product_id] = quantities.get(product_id, 0) + quantity
        if quantities[product_id] > 99:
            return None

    products = Product.objects.filter(id__in=quantities, available=True)
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(quantities):
        return None

    return [
        {
            "product": products_by_id[product_id],
            "quantity": quantity,
            "subtotal": products_by_id[product_id].price * quantity,
            "old_price": (
                products_by_id[product_id].old_price
                if products_by_id[product_id].discount_percent is not None
                else None
            ),
            "discount_percent": products_by_id[product_id].discount_percent,
            "original_subtotal": (
                products_by_id[product_id].old_price
                if products_by_id[product_id].discount_percent is not None
                else products_by_id[product_id].price
            ) * quantity,
        }
        for product_id, quantity in quantities.items()
    ]


@require_POST
def checkout_start(request):
    try:
        cart_data = json.loads(request.POST.get("cart_items", ""))
    except (TypeError, ValueError):
        cart_data = None

    items = _resolve_checkout_cart(cart_data)
    if items is None:
        messages.error(request, "Кошик порожній або містить недоступний товар. Перевірте його та спробуйте ще раз.")
        return redirect("catalog")

    request.session["checkout_cart"] = [
        {"id": item["product"].id, "quantity": item["quantity"]}
        for item in items
    ]
    return redirect("checkout")


def checkout(request):
    items = _resolve_checkout_cart(request.session.get("checkout_cart"))
    if items is None:
        request.session.pop("checkout_cart", None)
        messages.error(request, "Кошик порожній або товар більше не доступний.")
        return redirect("catalog")

    total = sum(item["subtotal"] for item in items)
    original_total = sum(item["original_subtotal"] for item in items)
    total_savings = original_total - total
    total_discount_percent = (
        (2 * total_savings * 100 + original_total) // (2 * original_total)
        if original_total
        else 0
    )
    payment_enabled = bool(settings.LIQPAY_PUBLIC_KEY and settings.LIQPAY_PRIVATE_KEY)
    form = CheckoutForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid() and not payment_enabled:
            form.add_error(None, "Оплата карткою ще не налаштована. Спробуйте пізніше.")
        elif form.is_valid():
            with transaction.atomic():
                order = Order.objects.create(
                    full_name=form.cleaned_data["full_name"],
                    email=form.cleaned_data["email"],
                    phone=form.cleaned_data["phone"],
                    delivery_address=form.cleaned_data["delivery_address"],
                    total=total,
                )
                OrderItem.objects.bulk_create([
                    OrderItem(
                        order=order,
                        product=item["product"],
                        product_name=item["product"].name,
                        quantity=item["quantity"],
                        unit_price=item["product"].price,
                    )
                    for item in items
                ])

            payment_payload = {
                "public_key": settings.LIQPAY_PUBLIC_KEY,
                "version": 3,
                "action": "pay",
                "amount": f"{total:.2f}",
                "currency": "UAH",
                "description": f"Оплата замовлення {order.reference}",
                "order_id": str(order.reference),
                "result_url": request.build_absolute_uri(
                    f"{reverse('payment_result')}?order={order.reference}"
                ),
                "server_url": request.build_absolute_uri(reverse("liqpay_callback")),
                "language": "uk",
                "paytypes": ["card"],
            }
            if settings.LIQPAY_SANDBOX:
                payment_payload["sandbox"] = 1

            payment_data = base64.b64encode(
                json.dumps(payment_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
            payment_signature = base64.b64encode(
                hashlib.sha1(
                    (settings.LIQPAY_PRIVATE_KEY + payment_data + settings.LIQPAY_PRIVATE_KEY).encode("utf-8")
                ).digest()
            ).decode("ascii")
            request.session.pop("checkout_cart", None)
            return render(request, "shop/liqpay_redirect.html", {
                "payment_data": payment_data,
                "payment_signature": payment_signature,
            })

    return render(request, "shop/checkout.html", {
        "form": form,
        "items": items,
        "total": total,
        "total_savings": total_savings,
        "total_discount_percent": total_discount_percent,
        "payment_enabled": payment_enabled,
    })


def payment_result(request):
    order = get_object_or_404(Order, reference=request.GET.get("order"))
    return render(request, "shop/payment_result.html", {"order": order})


@csrf_exempt
@require_POST
def liqpay_callback(request):
    payment_data = request.POST.get("data", "")
    received_signature = request.POST.get("signature", "")
    private_key = settings.LIQPAY_PRIVATE_KEY
    if not payment_data or len(payment_data) > 20000 or not received_signature or not private_key:
        return HttpResponseBadRequest("Invalid payment notification")

    expected_signature = base64.b64encode(
        hashlib.sha1((private_key + payment_data + private_key).encode("utf-8")).digest()
    ).decode("ascii")
    if not constant_time_compare(received_signature, expected_signature):
        return HttpResponseBadRequest("Invalid payment signature")

    try:
        payment = json.loads(base64.b64decode(payment_data, validate=True))
        if not isinstance(payment, dict):
            return HttpResponseBadRequest("Invalid payment data")
        order = Order.objects.get(reference=payment.get("order_id"))
        amount = Decimal(str(payment.get("amount")))
    except (ValueError, TypeError, InvalidOperation, Order.DoesNotExist, ValidationError):
        return HttpResponseBadRequest("Invalid payment data")

    if payment.get("currency") != "UAH" or amount != Decimal(order.total):
        return HttpResponseBadRequest("Payment amount mismatch")

    if order.status != Order.Status.PAID:
        if payment.get("status") == "success" or (
            payment.get("status") == "sandbox" and settings.LIQPAY_SANDBOX
        ):
            order.status = Order.Status.PAID
            order.save(update_fields=["status"])
        elif payment.get("status") in {"failure", "error", "reversed", "expired"}:
            order.status = Order.Status.FAILED
            order.save(update_fields=["status"])

    return HttpResponse("OK")


def register(request):
    if request.user.is_authenticated:
        return redirect("catalog")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        user.backend = "shop.auth_backends.EmailUsernameModelBackend"
        login(request, user)
        messages.success(request, "Обліковий запис створено.")
        return redirect("catalog")
    return render(request, "registration/register.html", {"form": form})
