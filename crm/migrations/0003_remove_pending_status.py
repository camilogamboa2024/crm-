from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0002_alter_reservation_status"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reservation",
            name="status",
            field=models.CharField(
                choices=[
                    ("booked", "Reservado"),
                    ("in_progress", "En curso"),
                    ("completed", "Completado"),
                    ("cancelled", "Cancelado"),
                ],
                default="booked",
                max_length=12,
                verbose_name="Estado",
            ),
        ),
    ]
