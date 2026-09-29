"""Prepare private configuration for a new public DEMO deployment, without deploying."""
import argparse
import json
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def domain(value):
    value = value.lower().strip()
    if len(value) > 253 or not re.fullmatch(
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?", value
    ):
        raise argparse.ArgumentTypeError("Use a DNS hostname without https://, port or path")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crm-domain", type=domain, required=True)
    parser.add_argument("--auth-domain", type=domain, required=True)
    args = parser.parse_args()
    if args.crm_domain == args.auth_domain:
        parser.error("Use two different hostnames for CRM and Keycloak")
    private = ROOT / ".deployment"
    envfile = ROOT / ".env.public"
    if envfile.exists() or private.exists():
        parser.error("Private configuration already exists; refusing to overwrite credentials")
    realm = json.loads((ROOT / "docker/keycloak-realm.json").read_text(encoding="utf-8"))
    origin = f"https://{args.crm_domain}"
    for client in realm["clients"]:
        if client["clientId"] == "crm-frontend":
            client["redirectUris"] = [origin + "/*"]
            client["webOrigins"] = [origin]
            client.setdefault("attributes", {})["post.logout.redirect.uris"] = origin + "/*"
    credentials = {}
    for user in realm["users"]:
        password = secrets.token_urlsafe(24)
        credentials[user["username"]] = password
        user["credentials"] = [{"type": "password", "value": password, "temporary": False}]
    database_password = secrets.token_hex(24)
    bootstrap_password = secrets.token_urlsafe(32)
    private.mkdir(mode=0o700)
    files = {
        private / "keycloak-realm.json": json.dumps(realm, ensure_ascii=False, indent=2),
        private / "demo-access.json": json.dumps(
            {"url": origin, "accounts": credentials}, ensure_ascii=False, indent=2
        ),
        envfile: "\n".join([
            f"CRM_DOMAIN={args.crm_domain}", f"AUTH_DOMAIN={args.auth_domain}",
            f"POSTGRES_PASSWORD={database_password}", "KC_ADMIN=bootstrap-admin",
            f"KC_ADMIN_PASSWORD={bootstrap_password}", "SEED_DEMO=true", "MAX_UPLOAD_MB=20", "",
        ]),
    }
    for path, content in files.items():
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        # Keycloak runs as a non-root UID and must read its bind-mounted file.
        # The parent directory remains 0700, preventing host-side traversal.
        path.chmod(0o644 if path.name == "keycloak-realm.json" else 0o600)
    print("Prepared .env.public and .deployment. No server was changed or deployed.")
    print("Keep these files private. Share selected demo accounts with judges separately.")


if __name__ == "__main__":
    main()
