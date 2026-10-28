from django.db import migrations


def restore_catalog_order(apps, schema_editor):
    Product = apps.get_model("shop", "Product")
    names = (
        "Santorini з широким полем пудрова",
        "Milan Beige з елегантним підбором",
        "Velvet Noir капор з утепленням",
        "Cypress клубний картуз",
        "Aster літній панама",
    )
    for position, name in enumerate(names):
        Product.objects.filter(name=name).update(sort_order=position)


class Migration(migrations.Migration):
    dependencies = [("shop", "0004_alter_product_options_product_sort_order")]

    operations = [migrations.RunPython(restore_catalog_order, migrations.RunPython.noop)]
