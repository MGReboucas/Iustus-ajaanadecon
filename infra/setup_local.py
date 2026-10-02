"""Cria configuração local e, opcionalmente, PostgreSQL isolado. Nunca altera serviço existente."""
import argparse
import base64
import os
from pathlib import Path
import secrets
import subprocess
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"


def run(args, **kwargs):
    return subprocess.run([str(arg) for arg in args], check=True,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                          **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument("--start-db", action="store_true")
    options = parser.parse_args()
    LOCAL.mkdir(exist_ok=True)
    backend_env = ROOT / "backend" / ".env"
    frontend_env = ROOT / "frontend" / ".env.local"
    if not backend_env.exists() and not frontend_env.exists():
        proxy, password = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        backend_env.write_text(
            "DJANGO_SETTINGS_MODULE=config.settings.local\n"
            f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n"
            f"IDENTITY_ENCRYPTION_KEY={base64.urlsafe_b64encode(os.urandom(32)).decode()}\n"
            f"IUSTUS_PROXY_SECRET={proxy}\n"
            f"DATABASE_URL=postgresql://iustus:{password}@127.0.0.1:55432/iustus\n"
            "IUSTUS_PUBLIC_ORIGIN=http://localhost:3000\nIUSTUS_INITIAL_ADMIN_EMAIL=\n",
            encoding="utf8",
        )
        frontend_env.write_text(
            f"IUSTUS_PROXY_SECRET={proxy}\nDJANGO_API_ORIGIN=http://127.0.0.1:8000\n"
            "IUSTUS_PUBLIC_ORIGIN=http://localhost:3000\n"
            "NEXT_PUBLIC_PAGBANK_SANDBOX=true\n", encoding="utf8",
        )
        print("Configuração local criada; segredos não foram exibidos.")
    elif not backend_env.exists() or not frontend_env.exists():
        raise SystemExit("Configuração parcial encontrada. Ajuste os dois arquivos sem sobrescrever seus valores.")
    if not options.start_db:
        return
    if not options.postgres_bin:
        raise SystemExit("Informe --postgres-bin para usar uma instalação existente.")
    values = dict(line.split("=", 1) for line in backend_env.read_text(encoding="utf8").splitlines() if "=" in line and not line.startswith("#"))
    db = urlsplit(values["DATABASE_URL"])
    if db.hostname != "127.0.0.1" or db.port != 55432 or db.username != "iustus" or db.path != "/iustus":
        raise SystemExit("Este script só gerencia seu cluster isolado em 127.0.0.1:55432/iustus.")
    cluster = LOCAL / "postgres"
    if cluster.is_symlink() or not cluster.resolve().is_relative_to(ROOT):
        raise SystemExit("Destino inválido para o cluster local.")
    suffix = ".exe" if os.name == "nt" else ""
    binary = lambda name: options.postgres_bin / (name + suffix)
    if not (cluster / "PG_VERSION").exists():
        if cluster.exists() and any(cluster.iterdir()):
            raise SystemExit("Diretório PostgreSQL não vazio; nenhuma alteração realizada.")
        password_file = LOCAL / "initdb-password"
        password_file.write_text(db.password, encoding="utf8")
        try:
            run([binary("initdb"), "-D", cluster, "-U", "iustus", "--auth=scram-sha-256", "--encoding=UTF8", "--locale=C", "--pwfile", password_file])
        finally:
            password_file.unlink(missing_ok=True)
    status = subprocess.run([str(binary("pg_ctl")), "-D", str(cluster), "status"], capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    if status.returncode != 0:
        run([binary("pg_ctl"), "-D", cluster, "-l", LOCAL / "postgres.log", "-o", "-h 127.0.0.1 -p 55432", "-w", "start"])
    child_env = {**os.environ, "PGPASSWORD": db.password}
    args = [binary("psql"), "-h", "127.0.0.1", "-p", "55432", "-U", "iustus", "-d", "postgres", "-tAc", "SELECT 1 FROM pg_database WHERE datname='iustus'"]
    result = run(args, env=child_env, capture_output=True, text=True)
    if result.stdout.strip() != "1":
        run([binary("createdb"), "-h", "127.0.0.1", "-p", "55432", "-U", "iustus", "iustus"], env=child_env)
    print("PostgreSQL do projeto pronto em 127.0.0.1:55432; serviço preexistente preservado.")


if __name__ == "__main__":
    main()
