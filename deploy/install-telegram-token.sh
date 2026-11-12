#!/usr/bin/env bash
# Runs on the machine, as the deploy user, with the token of the Telegram bot on stdin (ADR 0071). The token is
# created outside the machine by the owner with BotFather, so it cannot be generated here like the service secrets
# of ADR 0015: it arrives from the secret of the GitHub environment, never on a command line, in a log or in an
# environment variable, and lands as a file readable only by the image user.
set -euo pipefail
cd /opt/autotrading
postgres_image="$(docker compose config --images | grep '^postgres:')"
status=0
# The new token is written beside the old one and renamed over it, so the worker never reads half a token.
# Exit 3 tells that the token changed: the worker reads it only when it starts.
docker run -i --rm --user 0 --network none -v /opt/autotrading/secrets:/secrets --entrypoint sh "$postgres_image" \
  -c 'umask 077
      new=/secrets/.telegram_bot_token.new
      current=/secrets/telegram_bot_token
      cat > "$new"
      if [ ! -s "$new" ]; then rm -f "$new"; exit 0; fi
      if [ -f "$current" ] && [ "$(cat "$new")" = "$(cat "$current")" ]; then rm -f "$new"; exit 0; fi
      chown 65532:65532 "$new" && chmod 0400 "$new" && mv -f "$new" "$current"
      exit 3' || status=$?
case "$status" in
  0) echo "token del bot Telegram invariato" ;;
  # The marker survives a failed release: the next one restarts the worker anyway.
  3) touch .telegram_bot_token_changed && echo "token del bot Telegram aggiornato" ;;
  *) exit "$status" ;;
esac
