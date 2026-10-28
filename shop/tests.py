import base64
import hashlib
import json
import re
import tempfile
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.datastructures import MultiValueDict

from .admin import CategoryAdmin, CategoryAdminForm, ProductAdmin, ProductAdminForm
from .forms import RegistrationForm
from .models import (
    CATEGORY_LIMIT_MESSAGE,
    CATEGORY_NAME_LIMIT_MESSAGE,
    MAX_CATEGORIES,
    MAX_CATEGORY_NAME_LENGTH,
    Category,
    Order,
    OrderItem,
    Product,
    ProductPhoto,
    StorePage,
)

User = get_user_model()


class StorePagesTests(TestCase):
    def test_catalog_shows_seeded_products_and_categories(self):
        response = self.client.get(reverse("catalog"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Santorini з широким полем пудрова")
        self.assertContains(response, "Winter Sale")

    def test_catalog_supports_new_products_per_page_values(self):
        for per_page in (12, 24, 36):
            with self.subTest(per_page=per_page):
                response = self.client.get(reverse("catalog"), {"per_page": per_page})
                self.assertEqual(response.context["per_page"], per_page)
                self.assertEqual(response.context["page_obj"].paginator.per_page, per_page)

        response = self.client.get(reverse("catalog"), {"per_page": 5})
        self.assertEqual(response.context["per_page"], 12)

    def test_category_limit_and_navigation_rows(self):
        Category.objects.all().update(is_bonus=True)
        for category_number in range(Category.objects.count(), MAX_CATEGORIES):
            Category.objects.create(name=f"Category {category_number}", is_bonus=True)

        form = CategoryAdminForm(data={"name": "New category", "slug": "new-category"})
        self.assertFalse(form.is_valid())
        self.assertIn(CATEGORY_LIMIT_MESSAGE, form.non_field_errors())
        with self.assertRaisesMessage(ValidationError, CATEGORY_LIMIT_MESSAGE):
            Category.objects.create(name="New category")

        response = self.client.get(reverse("catalog"))
        category_rows = re.findall(
            r'<div class="category-nav-row">(.*?)</div>',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertEqual([row.count('class="category-link') for row in category_rows], [8, 8])

    def test_category_admin_changelist_loads_sortable_controls(self):
        admin_user = User.objects.create_superuser(
            username="sortable-admin",
            email="sortable@example.com",
            password="Strong-pass-9051",
        )
        self.client.force_login(admin_user)

        response = self.client.get(reverse("admin:shop_category_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "adminsortable2/css/sortable.")

    def test_bonus_category_is_in_header_and_includes_bonus_products(self):
        main_category = Category.objects.create(name="Main hats")
        bonus_category = Category.objects.create(name="Sale edit", is_bonus=True)
        product = Product.objects.create(
            category=main_category,
            name="Bonus collection hat",
            description="",
            price=100,
        )
        product.bonus_categories.add(bonus_category)

        response = self.client.get(reverse("catalog"), {"category": bonus_category.slug})

        self.assertIn(bonus_category, response.context["categories"])
        self.assertIn(main_category, response.context["categories"])
        self.assertEqual(list(response.context["products"]), [product])
        self.assertContains(response, bonus_category.name)
        self.assertContains(response, f'<span class="product-category">{main_category.name}</span>')
        self.assertNotContains(response, f'<span class="product-category">{bonus_category.name}</span>')

        product_form = ProductAdminForm(instance=product)
        self.assertIn(main_category, product_form.fields["category"].queryset)
        self.assertNotIn(bonus_category, product_form.fields["category"].queryset)
        self.assertIn(bonus_category, product_form.fields["bonus_categories"].queryset)
        self.assertNotIn(main_category, product_form.fields["bonus_categories"].queryset)

        bonus_category.is_bonus = False
        CategoryAdmin(Category, admin.site).save_model(None, bonus_category, None, change=True)
        product.refresh_from_db()
        self.assertFalse(product.bonus_categories.exists())

    def test_seed_collections_and_sale_are_bonus_categories(self):
        self.assertTrue(Category.objects.get(name="Winter Sale").is_bonus)
        self.assertTrue(Category.objects.get(name="Літня колекція").is_bonus)

    def test_category_name_length_limit_and_legacy_name(self):
        too_long_name = "x" * (MAX_CATEGORY_NAME_LENGTH + 1)
        form = CategoryAdminForm(data={"name": too_long_name, "slug": "too-long"})
        self.assertFalse(form.is_valid())
        self.assertIn(CATEGORY_NAME_LIMIT_MESSAGE, form.errors["name"])
        self.assertEqual(form.fields["name"].widget.attrs["maxlength"], MAX_CATEGORY_NAME_LENGTH)
        with self.assertRaisesMessage(ValidationError, CATEGORY_NAME_LIMIT_MESSAGE):
            Category.objects.create(name=too_long_name)

        legacy_category = Category(name=too_long_name, slug="legacy-category")
        Category.objects.bulk_create([legacy_category])
        legacy_category.refresh_from_db()
        legacy_category.save(update_fields=["name"])
        legacy_form = CategoryAdminForm(
            data={"name": legacy_category.name, "slug": legacy_category.slug},
            instance=legacy_category,
        )
        self.assertTrue(legacy_form.is_valid(), legacy_form.errors)

    def test_catalog_search_filters_by_name_and_preserves_query(self):
        category = Category.objects.first()
        for index in range(13):
            Product.objects.create(
                category=category,
                name=f"Searchable hat {index}",
                description="",
                price=100,
            )

        response = self.client.get(reverse("catalog"), {"q": "Searchable hat", "per_page": 12})

        self.assertEqual(response.context["search_query"], "Searchable hat")
        self.assertEqual(response.context["page_obj"].paginator.count, 13)
        self.assertEqual(len(response.context["products"]), 12)
        self.assertContains(response, 'value="Searchable hat"')
        self.assertContains(response, "&q=Searchable%20hat&page=2")

    def test_product_and_static_pages_render(self):
        product = Product.objects.first()
        self.assertEqual(self.client.get(reverse("product_detail", args=[product.pk])).status_code, 200)
        for slug in ("contacts", "returns", "terms"):
            with self.subTest(slug=slug):
                self.assertEqual(self.client.get(reverse("static_page", args=[slug])).status_code, 200)

    def test_discount_percent_is_rounded_and_rendered_in_red_badge(self):
        category = Category.objects.filter(is_bonus=False).first()
        product = Product.objects.create(
            category=category,
            name="Rounded discount",
            description="",
            price=199,
            old_price=200,
        )

        self.assertEqual(product.discount_percent, 1)
        catalog_response = self.client.get(reverse("catalog"))
        detail_response = self.client.get(reverse("product_detail", args=[product.pk]))
        self.assertContains(catalog_response, '<span class="discount-badge" aria-label="Знижка 1 відсотків">-1%</span>')
        self.assertContains(detail_response, '<span class="discount-badge" aria-label="Знижка 1 відсотків">-1%</span>')

        product.old_price = product.price
        self.assertIsNone(product.discount_percent)

    def test_product_admin_uploads_multiple_photos_in_selected_order(self):
        category = Category.objects.filter(is_bonus=False).first()
        uploaded_photos = [
            SimpleUploadedFile(f"photo-{number}.jpg", b"test-image", content_type="image/jpeg")
            for number in range(1, 5)
        ]
        files = MultiValueDict({"photos_upload": uploaded_photos})

        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            form = ProductAdminForm(
                data={
                    "category": category.pk,
                    "name": "Gallery upload test",
                    "description": "First paragraph\n\n  - List item",
                    "price": 100,
                    "sort_order": 0,
                },
                files=files,
            )
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(len(form.cleaned_data["photos_upload"]), 4)
            self.assertIn('multiple', form.fields["photos_upload"].widget.render("photos_upload", None))

            product = form.save(commit=False)
            product.save()
            form.save_m2m()
            ProductAdmin(Product, admin.site).save_related(None, form, [], change=False)

            photos = list(ProductPhoto.objects.filter(product=product).order_by("position"))
            self.assertEqual([photo.position for photo in photos], [0, 1, 2, 3])
            self.assertEqual([photo.image.name.rsplit("/", 1)[-1] for photo in photos], [
                "photo-1.jpg",
                "photo-2.jpg",
                "photo-3.jpg",
                "photo-4.jpg",
            ])

    def test_product_admin_requires_four_photos_and_limits_name_to_60(self):
        category = Category.objects.filter(is_bonus=False).first()
        form = ProductAdminForm(data={
            "category": category.pk,
            "name": "Hat product",
            "description": "Description",
            "price": 100,
            "sort_order": 0,
        })

        self.assertFalse(form.is_valid())
        self.assertIn("Для кожного товару потрібно щонайменше 4 фото.", form.non_field_errors())
        self.assertEqual(Product._meta.get_field("name").max_length, 60)
        self.assertEqual(form.fields["name"].max_length, 60)
        self.assertEqual(Category._meta.ordering[0], "sort_order")
        self.assertIn("sort_order", CategoryAdmin.list_display)

    def test_existing_product_with_three_photos_requires_one_more(self):
        category = Category.objects.filter(is_bonus=False).first()
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            product = Product.objects.create(
                category=category,
                name="Existing gallery",
                description="Description",
                price=100,
            )
            for number in range(1, 4):
                ProductPhoto.objects.create(
                    product=product,
                    image=SimpleUploadedFile(f"existing-{number}.jpg", b"test-image", content_type="image/jpeg"),
                    position=number - 1,
                )

            form_data = {
                "category": category.pk,
                "name": product.name,
                "description": product.description,
                "price": product.price,
                "sort_order": product.sort_order,
            }
            incomplete_form = ProductAdminForm(data=form_data, instance=product)
            self.assertFalse(incomplete_form.is_valid())

            files = MultiValueDict({
                "photos_upload": [
                    SimpleUploadedFile("fourth.jpg", b"test-image", content_type="image/jpeg")
                ],
            })
            complete_form = ProductAdminForm(data=form_data, files=files, instance=product)
            self.assertTrue(complete_form.is_valid(), complete_form.errors)

    def test_product_description_renders_paragraphs_and_preserves_indentation(self):
        product = Product.objects.first()
        product.description = "First paragraph\n\n  - First item\n  - Second item"
        product.save(update_fields=["description"])

        response = self.client.get(reverse("product_detail", args=[product.pk]))

        self.assertContains(response, "<p>First paragraph</p>")
        self.assertContains(response, "<p>  - First item<br>  - Second item</p>")

    def test_cart_controls_and_product_data_render(self):
        product = Product.objects.first()
        catalog_response = self.client.get(reverse("catalog"))
        self.assertContains(catalog_response, 'data-cart-open')
        self.assertContains(catalog_response, 'data-cart-checkout')
        self.assertContains(catalog_response, 'data-cart-remove')
        self.assertContains(catalog_response, 'data-cart-remove-confirm')
        self.assertContains(catalog_response, 'data-menu-toggle')
        self.assertContains(catalog_response, 'id="main-navigation"')
        self.assertContains(catalog_response, 'Всі товари')
        self.assertContains(catalog_response, f'data-product-id="{product.pk}"')
        self.assertContains(catalog_response, f'data-product-price="{product.price}"')

        detail_response = self.client.get(reverse("product_detail", args=[product.pk]))
        self.assertContains(detail_response, f'data-product-image="{product.cover_url}"')

    def test_checkout_uses_current_product_price_and_quantity(self):
        product = Product.objects.first()
        response = self.client.post(reverse("checkout_start"), {
            "cart_items": json.dumps([{"id": product.pk, "quantity": 3, "price": 1}]),
        })
        self.assertRedirects(response, reverse("checkout"))

        checkout_response = self.client.get(reverse("checkout"))
        self.assertEqual(checkout_response.status_code, 200)
        if product.discount_percent is not None:
            self.assertContains(checkout_response, f"3 шт. × <del>{product.old_price} грн</del>")
            self.assertContains(checkout_response, f"<strong>{product.price} грн</strong>")
        else:
            self.assertContains(checkout_response, f"3 шт. × {product.price} грн")
        self.assertContains(checkout_response, f"{product.price * 3} грн")
        self.assertEqual(self.client.session["checkout_cart"], [{"id": product.pk, "quantity": 3}])

    def test_checkout_shows_line_and_order_savings_only_for_discounted_products(self):
        category = Category.objects.filter(is_bonus=False).first()
        discounted_product = Product.objects.create(
            category=category,
            name="Discounted hat",
            description="",
            price=799,
            old_price=1100,
        )
        regular_product = Product.objects.create(
            category=category,
            name="Regular hat",
            description="",
            price=500,
        )
        session = self.client.session
        session["checkout_cart"] = [
            {"id": discounted_product.pk, "quantity": 2},
            {"id": regular_product.pk, "quantity": 1},
        ]
        session.save()

        response = self.client.get(reverse("checkout"))

        self.assertEqual(response.context["total"], 2098)
        self.assertEqual(response.context["total_savings"], 602)
        self.assertEqual(response.context["total_discount_percent"], 22)
        self.assertContains(response, "1100 грн")
        self.assertContains(response, "799 грн")
        self.assertContains(response, "Ваша економія:")
        self.assertContains(response, "602 грн (22%)")
        self.assertNotContains(response, "500 грн</del>")

    def test_checkout_rejects_unavailable_products(self):
        product = Product.objects.first()
        product.available = False
        product.save(update_fields=["available"])

        response = self.client.post(reverse("checkout_start"), {
            "cart_items": json.dumps([{"id": product.pk, "quantity": 1}]),
        })

        self.assertRedirects(response, reverse("catalog"))
        self.assertNotIn("checkout_cart", self.client.session)

    @override_settings(
        LIQPAY_PUBLIC_KEY="public-test-key",
        LIQPAY_PRIVATE_KEY="private-test-key",
        LIQPAY_SANDBOX=True,
    )
    def test_checkout_creates_order_and_signed_liqpay_request(self):
        product = Product.objects.first()
        session = self.client.session
        session["checkout_cart"] = [{"id": product.pk, "quantity": 2}]
        session.save()

        response = self.client.post(reverse("checkout"), {
            "full_name": "Ірина Покупець",
            "email": "buyer@example.com",
            "phone": "+380 50 123 4567",
            "delivery_address": "Нова пошта, відділення 1, Київ",
        })

        self.assertEqual(response.status_code, 200)
        order = Order.objects.get()
        order_item = OrderItem.objects.get(order=order)
        self.assertEqual(order.total, product.price * 2)
        self.assertEqual(order_item.quantity, 2)
        self.assertEqual(order_item.unit_price, product.price)

        payload = json.loads(base64.b64decode(response.context["payment_data"]))
        self.assertEqual(payload["order_id"], str(order.reference))
        self.assertEqual(payload["amount"], f"{product.price * 2:.2f}")
        self.assertEqual(payload["currency"], "UAH")
        self.assertEqual(payload["sandbox"], 1)
        expected_signature = base64.b64encode(
            hashlib.sha1(
                ("private-test-key" + response.context["payment_data"] + "private-test-key").encode()
            ).digest()
        ).decode()
        self.assertEqual(response.context["payment_signature"], expected_signature)

    @override_settings(LIQPAY_PRIVATE_KEY="private-test-key", LIQPAY_SANDBOX=True)
    def test_liqpay_callback_checks_signature_before_marking_order_paid(self):
        order = Order.objects.create(
            full_name="Ірина Покупець",
            email="buyer@example.com",
            phone="+380501234567",
            delivery_address="Відділення 1, Київ",
            total=890,
        )
        payment_data = base64.b64encode(json.dumps({
            "order_id": str(order.reference),
            "amount": "890.00",
            "currency": "UAH",
            "status": "sandbox",
        }).encode()).decode()
        signature = base64.b64encode(
            hashlib.sha1(("private-test-key" + payment_data + "private-test-key").encode()).digest()
        ).decode()

        invalid_response = self.client.post(reverse("liqpay_callback"), {
            "data": payment_data,
            "signature": "invalid-signature",
        })
        order.refresh_from_db()
        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(order.status, Order.Status.PENDING)

        valid_response = self.client.post(reverse("liqpay_callback"), {
            "data": payment_data,
            "signature": signature,
        })
        order.refresh_from_db()
        self.assertEqual(valid_response.status_code, 200)
        self.assertEqual(order.status, Order.Status.PAID)

    def test_registration_requires_email_and_username(self):
        form = RegistrationForm({
            "username": "shopper",
            "email": "shopper@example.com",
            "password1": "Strong-pass-9051",
            "password2": "Strong-pass-9051",
        })
        self.assertTrue(form.is_valid(), form.errors)

        invalid_form = RegistrationForm({
            "username": "shopper",
            "email": "not-an-email",
            "password1": "Strong-pass-9051",
            "password2": "Strong-pass-9051",
        })
        self.assertFalse(invalid_form.is_valid())
        self.assertIn("email", invalid_form.errors)

    def test_login_accepts_email_and_redirects_logged_user(self):
        User.objects.create_user(
            username="shopper",
            email="shopper@example.com",
            password="Strong-pass-9051",
        )

        response = self.client.post(reverse("login"), {
            "username": "shopper@example.com",
            "password": "Strong-pass-9051",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["user"].is_authenticated)

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="test-client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="test-client-secret",
        GOOGLE_OAUTH_REDIRECT_URI="http://127.0.0.1:8000/google-callback/",
    )
    @patch("shop.views.requests.post")
    @patch("shop.views.requests.get")
    def test_google_callback_creates_user_and_logs_in(self, mock_get, mock_post):
        self.client.get(reverse("google_login"))
        expected_state = self.client.session["google_oauth_state"]

        mock_post.return_value.json.return_value = {
            "access_token": "test-access-token",
            "id_token": "fake-id-token",
        }
        mock_get.return_value.json.return_value = {
            "email": "google.user@example.com",
            "given_name": "Google",
            "family_name": "User",
        }

        response = self.client.get(reverse("google_callback"), {"code": "test-code", "state": expected_state})

        self.assertRedirects(response, reverse("catalog"))
        user = User.objects.get(email="google.user@example.com")
        self.assertTrue(user.is_active)
        self.assertTrue(self.client.session.get("_auth_user_id") == str(user.pk))

    def test_registered_user_cannot_open_admin(self):
        response = self.client.post(reverse("register"), {
            "username": "shopper",
            "email": "shopper@example.com",
            "password1": "Strong-pass-9051",
            "password2": "Strong-pass-9051",
        })
        self.assertRedirects(response, reverse("catalog"))
        user = User.objects.get(username="shopper")
        self.assertFalse(user.is_staff)
        response = self.client.get("/admin/shop/product/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        self.assertEqual(Category.objects.count(), 5)
        self.assertEqual(StorePage.objects.count(), 3)
