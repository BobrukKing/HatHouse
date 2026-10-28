import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

MAX_CATEGORIES = 16
MAX_CATEGORY_NAME_LENGTH = 15
CATEGORY_LIMIT_MESSAGE = "Неможливо додати більше 16 категорій. Змініть або видаліть існуючу категорію."
CATEGORY_NAME_LIMIT_MESSAGE = "Назва категорії не може перевищувати 15 символів."


class Category(models.Model):
    name = models.CharField("Назва", max_length=60, unique=True)
    slug = models.SlugField("URL", max_length=80, unique=True, blank=True)
    is_bonus = models.BooleanField("Бонусна категорія", default=False)
    sort_order = models.PositiveIntegerField("Порядок", default=0, db_index=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "категорія"
        verbose_name_plural = "категорії"

    def save(self, *args, **kwargs):
        if self._state.adding and type(self).objects.count() >= MAX_CATEGORIES:
            raise ValidationError(CATEGORY_LIMIT_MESSAGE)
        existing_name = None
        if not self._state.adding:
            existing_name = type(self).objects.filter(pk=self.pk).values_list("name", flat=True).first()
        if len(self.name) > MAX_CATEGORY_NAME_LENGTH and self.name != existing_name:
            raise ValidationError(CATEGORY_NAME_LIMIT_MESSAGE)
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=True)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", verbose_name="Основна категорія")
    bonus_categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="bonus_products",
        verbose_name="Бонусні категорії",
    )
    name = models.CharField("Назва товару", max_length=60)
    description = models.TextField("Опис")
    price = models.PositiveIntegerField("Ціна, грн")
    old_price = models.PositiveIntegerField("Стара ціна, грн", blank=True, null=True)
    cover = models.CharField("Обкладинка зі статичних зображень", max_length=255, blank=True)
    available = models.BooleanField("В наявності", default=True)
    sort_order = models.IntegerField("Позиція в каталозі", default=0)
    created_at = models.DateTimeField("Додано", auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "-id"]
        verbose_name = "товар"
        verbose_name_plural = "товари"

    def __str__(self):
        return self.name

    @property
    def discount_percent(self):
        if self.old_price is None or self.old_price <= self.price:
            return None
        discount_amount = self.old_price - self.price
        return (2 * discount_amount * 100 + self.old_price) // (2 * self.old_price)

    @property
    def cover_url(self):
        first_photo = self.photos.first()
        if first_photo:
            return first_photo.image.url
        return "/static/" + (self.cover or "images/1.png").split("/")[-1]

    @property
    def gallery_urls(self):
        photos = list(self.photos.all())
        if photos:
            return [photo.image.url for photo in photos]
        cover = self.cover_url
        return [cover, *[f"/static/{number}.png" for number in range(1, 5) if f"/static/{number}.png" != cover]][:4]


class ProductPhoto(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="photos", verbose_name="Товар")
    image = models.ImageField("Фото", upload_to="products/")
    position = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "фото товару"
        verbose_name_plural = "фотографії товару"

    def __str__(self):
        return f"Фото: {self.product}"


class StoreSettings(models.Model):
    brand_name = models.CharField("Назва магазину", max_length=40, default="HatHouse")
    brand_image = models.ImageField("Аватарка", upload_to="branding/", blank=True)
    season_text = models.CharField("Текст сезону", max_length=80, default="Осінь / Зима 2026")

    class Meta:
        verbose_name = "налаштування магазину"
        verbose_name_plural = "налаштування магазину"

    def __str__(self):
        return self.brand_name


class StorePage(models.Model):
    SLUG_CHOICES = [
        ("contacts", "Контакти"),
        ("returns", "Обмін та повернення"),
        ("terms", "Угода користувача"),
    ]
    slug = models.SlugField("Сторінка", max_length=20, choices=SLUG_CHOICES, unique=True)
    title = models.CharField("Заголовок", max_length=100)
    content = models.TextField("Текст (абзаци розділяти порожнім рядком)")

    class Meta:
        verbose_name = "текст сторінки"
        verbose_name_plural = "тексти сторінок"

    def __str__(self):
        return self.title


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Очікує оплати"
        PAID = "paid", "Оплачено"
        FAILED = "failed", "Не оплачено"

    reference = models.UUIDField("Номер замовлення", default=uuid.uuid4, unique=True, editable=False)
    full_name = models.CharField("ПІБ покупця", max_length=180)
    email = models.EmailField("Email")
    phone = models.CharField("Телефон", max_length=30)
    delivery_address = models.TextField("Адреса або відділення пошти")
    total = models.PositiveIntegerField("Сума, грн")
    status = models.CharField("Статус", max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField("Створено", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "замовлення"
        verbose_name_plural = "замовлення"

    def __str__(self):
        return f"Замовлення {self.reference}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="Замовлення")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Товар")
    product_name = models.CharField("Назва товару", max_length=180)
    quantity = models.PositiveSmallIntegerField("Кількість")
    unit_price = models.PositiveIntegerField("Ціна за одиницю, грн")

    class Meta:
        verbose_name = "позиція замовлення"
        verbose_name_plural = "позиції замовлення"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"
