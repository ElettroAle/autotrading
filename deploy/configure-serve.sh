#!/usr/bin/env bash
# Runs on the machine, as the deploy user, at every release. Tailscale Serve exposes the dashboard on the path
# /dashboard of the same HTTPS name as the API (ADR 0117). Serve keeps one handler per path, so applying it again
# changes nothing, and an installation created before the dashboard gets it without being provisioned again.
# The deploy user is no operator of tailscaled: the CLI of the machine runs as root in a throwaway container that
# reaches only the local socket of tailscaled, as prepare-installation.sh does for the files of the secrets.
set -euo pipefail
cd /opt/autotrading
postgres_image="$(docker compose config --images | grep '^postgres:')"
docker run --rm --user 0 --network none \
  -v /usr/bin/tailscale:/usr/bin/tailscale:ro -v /run/tailscale:/run/tailscale \
  --entrypoint /usr/bin/tailscale "$postgres_image" \
  --socket=/run/tailscale/tailscaled.sock serve --bg --https=443 --set-path=/dashboard http://127.0.0.1:8080/dashboard
