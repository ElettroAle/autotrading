#!/usr/bin/env bash
# Run by the owner, once per installation, on his own PC with `az` already signed in (isolated profile, AZURE_CONFIG_DIR
# set by him). It is not part of the pipeline: the identity of the deploy must not be able to change Entra applications
# (ADR impostazioni-entra-dell-accesso-mcp-riproducibili). Idempotent: it writes only what is not already as it must be.
#
#   configure-mcp-access.sh <client id dell'API> <client id del client MCP> <nome HTTPS dell'installazione>
set -Eeuo pipefail

readonly CLIENT_REDIRECT="http://localhost/callback"

usage() {
  echo "Uso: $0 <client id dell'API> <client id del client MCP> <nome HTTPS dell'installazione, senza https:// e senza percorso>" >&2
  exit 2
}

# `az ... -o tsv` prints one value per line; on Windows the lines end with a carriage return.
values_of() {
  az ad app show --id "$1" --query "$2" --output tsv | tr -d '\r'
}

add_server_resource_to_the_api() {
  local api_client_id="$1" resource="$2" current uri
  local -a identifiers=()
  current="$(values_of "$api_client_id" identifierUris)"
  if grep -Fxq -- "$resource" <<< "$current"; then
    echo "Applicazione dell'API: l'identificativo ${resource} c'è già, tutto in ordine."
    return 0
  fi
  while IFS= read -r uri; do
    if [ -n "$uri" ]; then identifiers+=("$uri"); fi
  done <<< "$current"
  az ad app update --id "$api_client_id" --identifier-uris "${identifiers[@]}" "$resource" > /dev/null
  echo "Applicazione dell'API: aggiunto l'identificativo ${resource}, conservati gli esistenti."
}

set_the_only_redirect_of_the_client() {
  local client_id="$1" current
  current="$(values_of "$client_id" publicClient.redirectUris)"
  if [ "$current" = "$CLIENT_REDIRECT" ]; then
    echo "Client MCP: l'unico redirect è già ${CLIENT_REDIRECT}, tutto in ordine."
    return 0
  fi
  az ad app update --id "$client_id" --public-client-redirect-uris "$CLIENT_REDIRECT" > /dev/null
  echo "Client MCP: impostato ${CLIENT_REDIRECT} come unico redirect."
}

main() {
  if [ "$#" -ne 3 ] || [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then usage; fi
  case "$3" in */* | *:*) usage ;; esac
  trap 'echo "Errore di az: impostazioni Entra non applicate del tutto, rilanciare dopo aver verificato l'\''accesso." >&2' ERR
  add_server_resource_to_the_api "$1" "https://$3/mcp"
  set_the_only_redirect_of_the_client "$2"
}

main "$@"
