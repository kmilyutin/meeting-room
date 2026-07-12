from django.db import migrations, models

def normalize_room_statuses(apps, schema_editor):
    Room = apps.get_model('rooms', 'Room')
    Room.objects.filter(status='avaliable').update(status='available')
    Room.objects.filter(status__in=['maintenance', 'closed']).update(status='unavailable')

class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(normalize_room_statuses, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='room',
            name='status',
            field=models.CharField(
                choices=[
                    ('available', 'Свободно'),
                    ('busy', 'Занято'),
                    ('unavailable', 'Недоступно'),
                ],
                default='available',
                max_length=32,
            ),
        ),
    ]