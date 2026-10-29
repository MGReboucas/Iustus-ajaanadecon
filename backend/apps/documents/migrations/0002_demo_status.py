from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0001_initial")]
    operations = [migrations.AlterField(
        model_name="documentversion", name="status",
        field=models.CharField(max_length=16, default="UPLOADING", choices=[
            ("DEMO_UNVERIFIED", "Demonstração — não verificado"),
            ("UPLOADING", "Aguardando envio"), ("QUARANTINED", "Aguardando verificação"),
            ("SCANNING", "Em verificação"), ("AVAILABLE", "Disponível"),
            ("REJECTED", "Arquivo recusado"), ("ERROR", "Verificação indisponível")]),
    )]
