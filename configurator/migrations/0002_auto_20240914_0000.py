from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configurator", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="bomconfiguration",
            name="bauform",
            field=models.CharField(
                choices=[("I", "I-Form"), ("U", "U-Form")], default="I", max_length=1
            ),
        ),
        migrations.AddField(
            model_name="bomconfiguration",
            name="dfm_category",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name="sondenverschlusskappe",
            name="sonden_durchmesser",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="stumpfschweissendkappe",
            name="hvb_durchmesser",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="stumpfschweissendkappe",
            name="is_short_version",
            field=models.BooleanField(default=False),
        ),
    ]

