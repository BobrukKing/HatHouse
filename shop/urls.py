from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import EmailAuthenticationForm

urlpatterns = [
    path("", views.catalog, name="catalog"),
    path("checkout/start/", views.checkout_start, name="checkout_start"),
    path("checkout/", views.checkout, name="checkout"),
    path("payments/result/", views.payment_result, name="payment_result"),
    path("payments/liqpay/callback/", views.liqpay_callback, name="liqpay_callback"),
    path("products/<int:product_id>/", views.product_detail, name="product_detail"),
    path("pages/<slug:slug>/", views.static_page, name="static_page"),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html", authentication_form=EmailAuthenticationForm),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/register/", views.register, name="register"),
    path("google-login/", views.google_login, name="google_login"),
    path("google-callback/", views.google_callback, name="google_callback"),
]
