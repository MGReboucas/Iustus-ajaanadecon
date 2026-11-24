from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("documents", "0002_demo_status")]
    operations = [migrations.AlterField(
        model_name="documentversion", name="status",
        field=models.CharField(max_length=16, default="UPLOADING", choices=[
            ("REMOVED", "Removido do rascunho"),
            ("DEMO_UNVERIFIED", "Demonstração — não verificado"),
            ("UPLOADING", "Aguardando envio"), ("QUARANTINED", "Aguardando verificação"),
            ("SCANNING", "Em verificação"), ("AVAILABLE", "Disponível"),
            ("REJECTED", "Arquivo recusado"), ("ERROR", "Verificação indisponível")]),
    )]
