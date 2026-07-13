from django.db import migrations, models


def make_busy_rooms_available(apps, schema_editor):
    Room = apps.get_model('rooms', 'Room')
    Room.objects.filter(status='busy').update(status='available')


class Migration(migrations.Migration):
    dependencies = [
        ('rooms', '0003_booking_participants_alter_booking_name_and_more'),
    ]

    operations = [
        migrations.RunPython(make_busy_rooms_available, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='room',
            name='status',
            field=models.CharField(
                choices=[('available', 'Свободно'), ('unavailable', 'Недоступно')],
                default='available',
                max_length=32,
            ),
        ),
    ]
