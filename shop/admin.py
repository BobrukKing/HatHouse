from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import Max
from adminsortable2.admin import SortableAdminMixin

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
    StoreSettings,
)


class ProductPhotoInline(admin.TabularInline):
    model = ProductPhoto
    extra = 0
    max_num = 0
    can_delete = False


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        clean_file = super().clean
        if isinstance(data, (list, tuple)):
            return [clean_file(file, initial) for file in data]
        return [clean_file(data, initial)] if data else []


class ProductAdminForm(forms.ModelForm):
    photos_upload = MultipleFileField(
        label="Додати фото до галереї",
        required=False,
        help_text="Можна вибрати одразу 4 або більше фото; порядок вибору буде збережено.",
    )

    class Meta:
        model = Product
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["description"].widget.attrs["rows"] = 10
        self.fields["description"].help_text = "Зберігайте абзаци, списки й відступи звичайним текстом."
        self.fields["category"].queryset = Category.objects.filter(is_bonus=False)
        self.fields["bonus_categories"].queryset = Category.objects.filter(is_bonus=True)

    def clean(self):
        cleaned_data = super().clean()
        uploaded_photos = cleaned_data.get("photos_upload", [])
        existing_photos = self.instance.photos.count() if self.instance.pk else 0
        if existing_photos + len(uploaded_photos) < 4:
            raise ValidationError("Для кожного товару потрібно щонайменше 4 фото.")
        return cleaned_data


class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "slug", "is_bonus")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["maxlength"] = MAX_CATEGORY_NAME_LENGTH

    def clean_name(self):
        name = self.cleaned_data["name"]
        if len(name) > MAX_CATEGORY_NAME_LENGTH and (not self.instance.pk or name != self.instance.name):
            raise ValidationError(CATEGORY_NAME_LIMIT_MESSAGE)
        return name

    def clean(self):
        cleaned_data = super().clean()
        if not self.instance.pk and Category.objects.count() >= MAX_CATEGORIES:
            raise ValidationError(CATEGORY_LIMIT_MESSAGE)
        return cleaned_data


@admin.register(Category)
class CategoryAdmin(SortableAdminMixin, admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ("name", "is_bonus", "sort_order")
    list_filter = ("is_bonus",)
    list_editable = ("is_bonus",)
    prepopulated_fields = {"slug": ("name",)}

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not obj.is_bonus:
            obj.bonus_products.clear()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ("name", "category", "price", "old_price", "available", "sort_order")
    list_filter = ("category", "bonus_categories", "available")
    search_fields = ("name", "description")
    filter_horizontal = ("bonus_categories",)
    inlines = (ProductPhotoInline,)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        photos = form.cleaned_data.get("photos_upload", [])
        if not photos:
            return

        last_position = form.instance.photos.aggregate(max_position=Max("position"))["max_position"]
        next_position = (last_position + 1) if last_position is not None else 0
        for offset, photo in enumerate(photos):
            ProductPhoto.objects.create(
                product=form.instance,
                image=photo,
                position=next_position + offset,
            )


@admin.register(StorePage)
class StorePageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug")


@admin.register(StoreSettings)
class StoreSettingsAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "season_text")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("product", "product_name", "quantity", "unit_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("reference", "full_name", "total", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("reference", "full_name", "email", "phone")
    readonly_fields = ("reference", "created_at")
    inlines = (OrderItemInline,)
