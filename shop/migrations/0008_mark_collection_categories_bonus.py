from django.db import migrations
from django.db.models import Q


def mark_bonus_categories(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Category.objects.filter(
        Q(name__icontains="колекці")
        | Q(name__icontains="sale")
        | Q(name__icontains="розпрод")
    ).update(is_bonus=True)


def unmark_bonus_categories(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Category.objects.filter(
        Q(name__icontains="колекці")
        | Q(name__icontains="sale")
        | Q(name__icontains="розпрод")
    ).update(is_bonus=False)


class Migration(migrations.Migration):
    dependencies = [
        ("shop", "0007_category_is_bonus_product_bonus_categories_and_more"),
    ]

    operations = [
        migrations.RunPython(mark_bonus_categories, unmark_bonus_categories),
    ]