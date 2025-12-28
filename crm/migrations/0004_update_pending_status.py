from django.db import migrations


def update_pending_status(apps, schema_editor):
    Reservation = apps.get_model("crm", "Reservation")
    Reservation.objects.filter(status="pending").update(status="booked")


class Migration(migrations.Migration):
    dependencies = [
        ("crm", "0003_remove_pending_status"),
    ]

    operations = [
        migrations.RunPython(update_pending_status, migrations.RunPython.noop),
    ]
