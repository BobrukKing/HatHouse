from django.db import migrations, models


def keep_latest_store_settings(apps, schema_editor):
    StoreSettings = apps.get_model("shop", "StoreSettings")
    database = schema_editor.connection.alias
    settings_ids = list(
        StoreSettings.objects.using(database)
        .order_by("-pk")
        .values_list("pk", flat=True)
    )
    if len(settings_ids) > 1:
        StoreSettings.objects.using(database).filter(pk__in=settings_ids[1:]).delete()


class Migration(migrations.Migration):
    dependencies = [("shop", "0010_order_admin_notification_sent_alter_order_status")]

    operations = [
        migrations.RunPython(keep_latest_store_settings, migrations.RunPython.noop),
        migrations.AddField(
            model_name="storesettings",
            name="singleton_key",
            field=models.CharField(
                default="store-settings",
                editable=False,
                max_length=32,
                unique=True,
            ),
        ),
    ]
