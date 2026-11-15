#!/usr/bin/env bash
# Runs on the machine, as the deploy user, at every release (ADR 0162). `start`, before the pull, samples the memory of
# every container and the memory available to the machine every 2 seconds; `report`, after the services are up, stops
# the sampling and prints, in Markdown for the summary of the job, the peak and the rest of every container, the minimum
# memory available during the release and the disk. The memory limits of the services are tuned on these numbers
# (Bug 252). The measure never fails the release: every step that cannot measure says so and goes on.
set -uo pipefail
directory="${MEASUREMENT_DIRECTORY:-/opt/autotrading}"
samples="${directory}/resource-samples.txt"
pid_file="${directory}/resource-sampler.pid"

sample() {
  # A release that never reaches its report (a cancelled job) must not leave the sampler running for ever.
  while [ "$SECONDS" -lt 3600 ]; do
    docker stats --no-stream --format 'container {{.Name}} {{.MemUsage}}' 2>/dev/null
    awk '$1 == "MemAvailable:" { print "available", $2 }' /proc/meminfo
    sleep 2
  done >> "$samples"
}

stop_sampler() {
  [ -s "$pid_file" ] || return 0
  # The sampler leads its own process group: stopping the group stops the docker stats and sleep it is waiting on.
  kill -- "-$(cat "$pid_file")" 2>/dev/null || kill "$(cat "$pid_file")" 2>/dev/null
  rm -f "$pid_file"
}

start() {
  stop_sampler
  : > "$samples"
  # Detached from the SSH session, which ends right after this command.
  setsid nohup bash "$0" sample < /dev/null > /dev/null 2>&1 &
  echo "$!" > "$pid_file"
}

container_table() {
  local rest rest_measured=1
  rest="$(docker stats --no-stream --format 'rest {{.Name}} {{.MemUsage}}' 2>/dev/null)" || rest_measured=0
  echo "| Container | Picco (MiB) | Riposo (MiB) |"
  echo "|---|---:|---:|"
  { cat "$samples" 2>/dev/null; printf '%s\n' "$rest"; } | awk -v rest_measured="$rest_measured" '
    function mebibytes(usage,   unit) {
      unit = usage
      sub(/^[0-9.]+/, "", unit)
      if (unit == "B") return usage / 1048576
      if (unit == "KiB" || unit == "kB") return usage / 1024
      if (unit == "GiB" || unit == "GB") return usage * 1024
      if (unit == "TiB" || unit == "TB") return usage * 1048576
      return usage + 0
    }
    # docker stats shows a restarting container, whose stats it cannot read, as dashes: not a service (ADR 0165).
    $2 == "--" { next }
    $1 == "container" { value = mebibytes($3); seen[$2] = 1; if (!($2 in peak) || value > peak[$2]) peak[$2] = value }
    $1 == "rest" { seen[$2] = 1; rest[$2] = mebibytes($3) }
    END {
      for (name in seen) {
        peak_text = (name in peak) ? sprintf("%.0f", peak[name]) : "nessun campione"
        rest_text = (name in rest) ? sprintf("%.0f", rest[name]) : (rest_measured ? "non in esecuzione" : "non misurato")
        printf "| %s | %s | %s |\n", name, peak_text, rest_text
      }
    }' | sort
}

minimum_available() {
  awk '$1 == "available" && (minimum == "" || $2 < minimum) { minimum = $2 }
    END {
      if (minimum == "") { print "Memoria disponibile minima durante il rilascio: nessun campione"; exit }
      printf "Memoria disponibile minima durante il rilascio: %.0f MiB\n", minimum / 1024
    }' "$samples" 2>/dev/null || echo "Memoria disponibile minima durante il rilascio: nessun campione"
}

disk() {
  echo '```text'
  df -h / 2>&1
  echo
  docker system df 2>&1
  echo '```'
}

report() {
  stop_sampler
  echo "### Memoria e disco del rilascio (ADR 0162)"
  echo
  container_table
  echo
  minimum_available
  echo
  disk
  return 0
}

case "${1:-}" in
  start) start ;;
  sample) sample ;;
  report) report ;;
  *) echo "uso: measure-resources.sh start|report" >&2; exit 2 ;;
esac
