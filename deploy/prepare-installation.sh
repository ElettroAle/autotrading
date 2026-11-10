#!/usr/bin/env bash
# Runs on the machine, as the deploy user, before the compose starts. It generates the service secrets on the
# machine itself, so no person and no GitHub log ever sees them (ADR 0015), and installs the database bootstrap.
set -euo pipefail
cd /opt/autotrading
install -d -m 700 secrets
# The postgres user of the container (70) must traverse the init directory.
install -d -m 755 postgres-init
# The previous release left the script read-only: replace it instead of writing through it.
rm -f postgres-init/10-application-role.sh
cat > postgres-init/10-application-role.sh
chmod 0555 postgres-init/10-application-role.sh
postgres_image="$(docker compose config --images | grep '^postgres:')"
for secret in postgres_owner_password postgres_app_password; do
  [ -s "secrets/${secret}" ] && continue
  # Readable only by the containers that need it: the API image user (65532) and the postgres group (70).
  docker run --rm --user 0 --network none -v /opt/autotrading/secrets:/secrets --entrypoint sh "$postgres_image" \
    -c "umask 077 && tr -dc A-Za-z0-9 </dev/urandom | head -c 40 > /secrets/${secret} \
        && chown 65532:70 /secrets/${secret} && chmod 0440 /secrets/${secret}"
done

# The token the API presents to the worker (ADR 0021): readable only by the image user both services run as.
if [ ! -s secrets/worker_token ]; then
  docker run --rm --user 0 --network none -v /opt/autotrading/secrets:/secrets --entrypoint sh "$postgres_image" \
    -c "umask 077 && tr -dc A-Za-z0-9 </dev/urandom | head -c 48 > /secrets/worker_token \
        && chown 65532:65532 /secrets/worker_token && chmod 0400 /secrets/worker_token"
fi

# The key pair of the account credentials (ADR 0007, ADR 0018): generated once, never replaced by a release.
# The API receives only the public key; the private one is mounted in the worker alone.
private_key=secrets/credentials_private_key_v1
public_key=secrets/credentials_public_key
if [ ! -e "$private_key" ] && [ ! -e "$public_key" ]; then
  api_image="$(grep '^API_IMAGE=' .env | cut -d= -f2-)"
  docker run --rm --user 0 --network none -v /opt/autotrading/secrets:/secrets \
    --entrypoint /app/.venv/bin/python "$api_image" -c '
import base64, os
from nacl.public import PrivateKey

key = PrivateKey.generate()
for name, raw, mode in (("credentials_private_key_v1", bytes(key), 0o400),
                        ("credentials_public_key", bytes(key.public_key), 0o444)):
    with open(os.open("/secrets/" + name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode), "w") as handle:
        handle.write(base64.b64encode(raw).decode())
'
fi
if [ ! -s "$public_key" ] || [ ! -e "$private_key" ]; then
  echo "coppia di chiavi delle credenziali incompleta: nessuna chiave viene rigenerata sopra quella esistente" >&2
  exit 1
fi
# Only the worker mounts the private key, and it runs as the image user (65532): the key belongs to that user and
# nobody else can read it (ADR 0021). Applied at every release, so an installation created before the worker
# gets the same ownership.
docker run --rm --user 0 --network none -v /opt/autotrading/secrets:/secrets --entrypoint sh "$postgres_image" \
  -c "chown 65532:65532 /secrets/credentials_private_key_v1 && chmod 0400 /secrets/credentials_private_key_v1"
