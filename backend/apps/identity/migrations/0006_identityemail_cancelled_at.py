from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("identity", "0005_mobilesession")]

    operations = [
        migrations.AddField(
            model_name="identityemail", name="cancelled_at",
            field=models.DateTimeField(null=True),
        ),
    ]
