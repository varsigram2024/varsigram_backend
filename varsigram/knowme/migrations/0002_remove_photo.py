from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('knowme', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallmember',
            name='photo',
        ),
    ]
