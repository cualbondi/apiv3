import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0002_auto_20151019_2213'),
    ]

    operations = [
        migrations.RunSQL(
            [(
                 'ALTER TABLE core_recorrido ALTER COLUMN uuid TYPE uuid USING GREATEST(uuid,\'00000000000000000000000000000000\')::uuid;')],
            [('ALTER TABLE core_recorrido ALTER COLUMN uuid TYPE varchar(36) USING uuid::varchar(36);')],
        ),
        migrations.AlterField(
            model_name='recorrido',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4),
        ),
    ]
