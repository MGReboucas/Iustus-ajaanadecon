from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.urls import URLResolver, get_resolver


def routes(patterns, prefix=""):
    for pattern in patterns:
        route = prefix + str(pattern.pattern)
        if isinstance(pattern, URLResolver):
            yield from routes(pattern.url_patterns, route)
        else:
            cls = getattr(pattern.callback, "cls", None) or getattr(pattern.callback, "view_class", None)
            if cls:
                methods = [method.upper() for method in cls.http_method_names
                           if method not in ("head", "options") and callable(getattr(cls, method, None))]
                yield route, ", ".join(methods), cls.__module__ + "." + cls.__name__


def document():
    rows = sorted(routes(get_resolver().url_patterns))
    header = "# Inventario de rotas Django\n\nGerado do roteamento e dos handlers. Nao certifica autorizacao, disponibilidade ou deploy. HEAD/OPTIONS omitidos.\n\n"
    header += "Atualizar: `python backend/manage.py export_api_routes --settings=config.settings.test --output docs/API_ROTAS.md`\n\n"
    header += "Conferir: acrescente `--check` ao comando.\n\n"
    header += "| Metodos | Rota | Implementacao |\n| --- | --- | --- |\n"
    return header + "".join(f"| {methods} | `/{route}` | `{view}` |\n" for route, methods, view in rows)


class Command(BaseCommand):
    help = "Export deterministic API route inventory without accessing the database."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)
        parser.add_argument("--check", action="store_true")

    def handle(self, *args, **options):
        path = Path(options["output"])
        expected = document()
        if options["check"]:
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                raise CommandError("API route inventory is outdated")
            self.stdout.write("API routes verified")
        else:
            path.write_text(expected, encoding="utf-8")
            self.stdout.write("API route inventory written")
