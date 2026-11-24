from django.core.management.base import BaseCommand
from jobs.documents import purge_removed_one


class Command(BaseCommand):
    help = "Limpa objetos de anexos removidos após expirarem as URLs de upload."

    def handle(self, *args, **options):
        count = 0
        while count < 100 and purge_removed_one():
            count += 1
        self.stdout.write(f"Objetos removidos: {count}")
