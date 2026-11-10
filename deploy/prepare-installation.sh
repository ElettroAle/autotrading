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
