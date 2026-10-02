"""Preparação interativa local, sem exibir segredos nem alterar contas externas."""
import getpass
from pathlib import Path
import secrets

from cryptography.fernet import Fernet


def main():
    root = Path(__file__).resolve().parents[2]
    target = root / ".local" / "deployment.env"
    if target.exists():
        raise SystemExit("deployment.env já existe. Edite os valores pendentes sem regenerar chaves.")
    target.parent.mkdir(exist_ok=True)
    gmail = input("Gmail remetente: ").strip()
    if not gmail.endswith("@gmail.com") or "\n" in gmail or "=" in gmail:
        raise SystemExit("Informe a conta Gmail dedicada ao envio.")
    password = getpass.getpass("Senha de app do Gmail (oculta; não use a senha da conta): ").replace(" ", "")
    if not password or "\n" in password:
        raise SystemExit("Senha de app obrigatória.")
    database = getpass.getpass("DATABASE_URL do Neon (oculta): ").strip()
    if not database.startswith("postgresql://") or "\n" in database:
        raise SystemExit("Informe a conexão PostgreSQL do Neon.")
    values = {
        "DJANGO_SETTINGS_MODULE": "config.settings.production",
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(64),
        "IUSTUS_PROXY_SECRET": secrets.token_urlsafe(48),
        "IDENTITY_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "DATABASE_URL": database,
        "EMAIL_HOST": "smtp.gmail.com", "EMAIL_PORT": "587",
        "EMAIL_HOST_USER": gmail, "EMAIL_HOST_PASSWORD": password,
        "DEFAULT_FROM_EMAIL": f"Iustus <{gmail}>",
        "IUSTUS_PUBLIC_ORIGIN": "https://iustus-defesa-juridica.vercel.app",
        "IUSTUS_INITIAL_ADMIN_EMAIL": "", "DJANGO_ALLOWED_HOSTS": "",
        "REGISTRATION_POLICY_VERSION": "web-evaluation-v1",
    }
    with target.open("x", encoding="utf8") as output:
        output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    print("Segredos salvos em .local/deployment.env (ignorado pelo Git). Nenhuma credencial foi exibida.")


if __name__ == "__main__":
    main()
