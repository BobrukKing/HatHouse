from django.db import migrations


def create_initial_store(apps, schema_editor):
    Category = apps.get_model("shop", "Category")
    Product = apps.get_model("shop", "Product")
    StoreSettings = apps.get_model("shop", "StoreSettings")
    StorePage = apps.get_model("shop", "StorePage")

    categories = {}
    for name in (
        "Winter Sale",
        "Берети",
        "Капори та балаклави",
        "Картузи",
        "Літня колекція",
    ):
        categories[name] = Category.objects.create(name=name, slug=name.lower().replace(" ", "-"))

    products = (
        ("Winter Sale", "Santorini з широким полем пудрова", 1200, 890, "images/1.png", "Модель з м’якого вовняного полотна, об’ємною формою та широким полем. Ідеально підходить для холодного сезону і доповнить будь-який образ."),
        ("Берети", "Milan Beige з елегантним підбором", 1100, 820, "images/2.png", "Класичний берето з натуральної вовни та м’якою підкладкою. Підходить для повсякденного носіння та особливих заходів."),
        ("Капори та балаклави", "Velvet Noir капор з утепленням", 1350, 990, "images/3.png", "Комфортний капор для активних зимових прогулянок. М’яке утеплення, гладка текстура та практичний крій зберігають тепло."),
        ("Картузи", "Cypress клубний картуз", 980, 760, "images/4.png", "Картуз з високою посадкою, створений для стильного образу в холодну пору. Тверда форма та натуральний матеріал надають вишуканості."),
        ("Літня колекція", "Aster літній панама", 780, 590, "images/3.png", "Легка панама для сонячних днів із натуральною лляною фактурою. Підходить для відпочинку, міських прогулянок та відпустки."),
    )
    for category, name, old_price, price, cover, description in products:
        Product.objects.create(
            category=categories[category], name=name, old_price=old_price,
            price=price, cover=cover, description=description,
        )

    StoreSettings.objects.create(brand_name="HatHouse", season_text="Осінь / Зима 2026")
    pages = (
        ("contacts", "Контакти", "Телефон: +380 (50) 123-45-67\n\nEmail: hello@hathouse.ua\n\nАдреса: м. Київ, вул. Мистецтв, 14\n\nГрафік роботи: Пн–Сб, 10:00–19:00"),
        ("returns", "Обмін та повернення", "Повернення або обмін товару можливий протягом 14 днів з моменту отримання, якщо виріб не був у використанні та збережено товарний вигляд.\n\nДля оформлення повернення зверніться до служби підтримки з номером замовлення та фото товару.\n\nТовари зі знижкою обмінюються або повертаються відповідно до чинного законодавства України."),
        ("terms", "Угода користувача", "Використовуючи сайт, ви погоджуєтеся з правилами оформлення замовлення, умовами доставки та відповідальністю за достовірність контактної інформації.\n\nМи зберігаємо право оновлювати ціни, доступність та опис товарів без попереднього повідомлення.\n\nВсі зображення та текстові матеріали використовуються виключно для демонстрації асортименту та не є офіційними рекламними матеріалами виробників."),
    )
    for slug, title, content in pages:
        StorePage.objects.create(slug=slug, title=title, content=content)


def remove_initial_store(apps, schema_editor):
    for model_name in ("Product", "Category", "StoreSettings", "StorePage"):
        apps.get_model("shop", model_name).objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("shop", "0001_initial")]

    operations = [migrations.RunPython(create_initial_store, remove_initial_store)]
