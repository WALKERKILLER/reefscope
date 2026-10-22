# 添加 detections JSONField 到 Task 模型

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="task",
            name="detections",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
