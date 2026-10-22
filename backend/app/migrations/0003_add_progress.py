from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0002_add_detections"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="progress",
            field=models.IntegerField(default=0),
        ),
    ]
