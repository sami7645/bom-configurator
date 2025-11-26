from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configurator", "0002_auto_20240914_0000"),
    ]

    operations = [
        migrations.AddField(
            model_name="entlueftung",
            name="et_hvb",
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]

