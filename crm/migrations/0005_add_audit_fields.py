from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0004_update_pending_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="car",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Creado"),
        ),
        migrations.AddField(
            model_name="car",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Actualizado"),
        ),
        migrations.AddField(
            model_name="customer",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Creado"),
        ),
        migrations.AddField(
            model_name="customer",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Actualizado"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, verbose_name="Creado"),
        ),
        migrations.AddField(
            model_name="reservation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Actualizado"),
        ),
    ]
