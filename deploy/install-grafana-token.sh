#!/usr/bin/env bash
# Runs on the machine, as the deploy user, with the token of Grafana Cloud on stdin (ADR
# telemetria-opentelemetry-verso-grafana-cloud, ADR 0071). The token is created outside the machine by the owner in the
# Grafana Cloud stack, so it cannot be generated here like the service secrets of ADR 0015: it arrives from the secret
# of the GitHub environment, never on a command line, in a log or in an environment variable, and lands as a file
# readable only by the image user.
set -euo pipefail
cd /opt/autotrading
postgres_image="$(docker compose config --images | grep '^postgres:')"
status=0
# The new token is written beside the old one and renamed over it, so a service never reads half a token.
# Exit 3 tells that the token changed: api and worker read it only when they start.
docker run -i --rm --user 0 --network none -v /opt/autotrading/secrets:/secrets --entrypoint sh "$postgres_image" \
  -c 'umask 077
      new=/secrets/.grafana_otlp_token.new
      current=/secrets/grafana_otlp_token
      cat > "$new"
      if [ ! -s "$new" ]; then rm -f "$new"; exit 0; fi
      if [ -f "$current" ] && [ "$(cat "$new")" = "$(cat "$current")" ]; then rm -f "$new"; exit 0; fi
      chown 65532:65532 "$new" && chmod 0400 "$new" && mv -f "$new" "$current"
      exit 3' || status=$?
case "$status" in
  0) echo "token di Grafana Cloud invariato" ;;
  # The marker survives a failed release: the next one recreates api and worker anyway.
  3) touch .grafana_otlp_token_changed && echo "token di Grafana Cloud aggiornato" ;;
  *) exit "$status" ;;
esac
