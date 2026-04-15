#!/bin/bash
set -euo pipefail

WAIT_FOR_CONFIG_FILE_ATTEMPTS="${WAIT_FOR_CONFIG_FILE_ATTEMPTS:-600}"
WAIT_FOR_PASSWORD_SET_ATTEMPTS="${WAIT_FOR_PASSWORD_SET_ATTEMPTS:-300}"
WAIT_FOR_SERVICE_READY_ATTEMPTS="${WAIT_FOR_SERVICE_READY_ATTEMPTS:-600}"
WAIT_INTERVAL_SECONDS="${WAIT_INTERVAL_SECONDS:-1}"
CONFIG_FILE="/etc/seekdb/seekdb.cnf"
SEEKDB_CONFIG_FILE="/var/lib/oceanbase/etc/seekdb.data_version.bin"
INITIALIZED_FLAG="/var/lib/oceanbase/.initialized"

seekdb_set_cnf() {
  local key="$1"
  local value="$2"
  if [ -f "$CONFIG_FILE" ] && grep -qE "^${key}=" "$CONFIG_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$CONFIG_FILE"
  else
    echo "${key}=${value}" >> "$CONFIG_FILE"
  fi
}

wait_for_file() {
  local path="$1"
  local attempts="$2"
  for i in $(seq 1 "$attempts"); do
    if [ -f "$path" ]; then
      echo "File '$path' found on attempt #$i."
      return 0
    fi
    if [ $((i % 10)) -eq 0 ]; then
      echo "Waiting for file '$path'..."
    fi
    sleep "$WAIT_INTERVAL_SECONDS"
  done
  echo "Timed out waiting for '$path'."
  return 1
}

wait_for_mysql() {
  local password="${1:-}"
  local attempts="${2:-$WAIT_FOR_SERVICE_READY_ATTEMPTS}"
  local mysql_args=(-h127.0.0.1 -P2881 -uroot)

  if [ -n "$password" ]; then
    mysql_args+=("-p${password}")
  fi

  for i in $(seq 1 "$attempts"); do
    if mysql "${mysql_args[@]}" -e "show databases" >/dev/null 2>&1; then
      echo "seekdb MySQL endpoint is ready on attempt #$i."
      return 0
    fi
    if [ $((i % 10)) -eq 0 ]; then
      echo "Waiting for seekdb MySQL endpoint to become ready..."
    fi
    sleep "$WAIT_INTERVAL_SECONDS"
  done

  echo "Timed out waiting for seekdb MySQL endpoint."
  return 1
}

set_root_password() {
  local password="$1"
  local response_file
  response_file="$(mktemp)"

  for i in $(seq 1 "$WAIT_FOR_PASSWORD_SET_ATTEMPTS"); do
    local http_code
    http_code="$(
      curl \
        --silent \
        --show-error \
        --output "$response_file" \
        --write-out "%{http_code}" \
        -X PUT "http://127.0.0.1:2886/api/v1/seekdb/user/root/password" \
        -H "Content-Type: application/json" \
        -d "{\"password\":\"${password}\"}" \
        --unix-socket "/var/lib/oceanbase/run/obshell.sock"
    )"
    local body
    body="$(cat "$response_file")"

    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
      echo "Root password set successfully on attempt #$i."
      rm -f "$response_file"
      return 0
    fi

    if printf "%s" "$body" | grep -q "Server is initializing"; then
      if [ $((i % 10)) -eq 0 ]; then
        echo "seekdb is still initializing while setting root password..."
      fi
      sleep "$WAIT_INTERVAL_SECONDS"
      continue
    fi

    echo "Failed to set root password on attempt #$i. HTTP $http_code: $body"
    sleep "$WAIT_INTERVAL_SECONDS"
  done

  echo "Timed out while setting root password."
  rm -f "$response_file"
  return 1
}

if [ -n "${DATAFILE_SIZE:-}" ]; then
  seekdb_set_cnf datafile_size "$DATAFILE_SIZE"
fi

if [ -n "${DATAFILE_NEXT:-}" ]; then
  seekdb_set_cnf datafile_next "$DATAFILE_NEXT"
fi

if [ -n "${DATAFILE_MAXSIZE:-}" ]; then
  seekdb_set_cnf datafile_maxsize "$DATAFILE_MAXSIZE"
fi

if [ -n "${CPU_COUNT:-}" ]; then
  seekdb_set_cnf cpu_count "$CPU_COUNT"
fi

if [ -n "${MEMORY_LIMIT:-}" ]; then
  seekdb_set_cnf memory_limit "$MEMORY_LIMIT"
fi

if [ -n "${LOG_DISK_SIZE:-}" ]; then
  seekdb_set_cnf log_disk_size "$LOG_DISK_SIZE"
fi

/usr/libexec/seekdb/scripts/seekdb_systemd_start 2>/dev/null

wait_for_file "$SEEKDB_CONFIG_FILE" "$WAIT_FOR_CONFIG_FILE_ATTEMPTS"
obshell agent start --seekdb --base-dir=/var/lib/oceanbase

if [ ! -f "$INITIALIZED_FLAG" ]; then
  wait_for_mysql "" "$WAIT_FOR_SERVICE_READY_ATTEMPTS"

  MYSQL_OPTS=(-h127.0.0.1 -P2881 -uroot)
  if [ -n "${ROOT_PASSWORD:-}" ]; then
    set_root_password "$ROOT_PASSWORD"
    wait_for_mysql "$ROOT_PASSWORD" "$WAIT_FOR_SERVICE_READY_ATTEMPTS"
    MYSQL_OPTS+=("-p${ROOT_PASSWORD}")
  fi

  if [ -n "${SEEKDB_DATABASE:-}" ]; then
    mysql "${MYSQL_OPTS[@]}" -e "CREATE DATABASE IF NOT EXISTS \`${SEEKDB_DATABASE}\`;"
    echo "Database ${SEEKDB_DATABASE} created."
    MYSQL_OPTS+=("-D${SEEKDB_DATABASE}")
  fi

  if [ -n "${INIT_SCRIPTS_PATH:-}" ]; then
    echo "Executing initialization scripts from ${INIT_SCRIPTS_PATH}..."
    for sql_file in "${INIT_SCRIPTS_PATH}"/*.sql; do
      if [ -f "$sql_file" ]; then
        echo "Executing ${sql_file}..."
        mysql "${MYSQL_OPTS[@]}" < "$sql_file"
        echo "Finished executing ${sql_file}."
      fi
    done
    echo "Initialization scripts execution complete."
  fi

  touch "$INITIALIZED_FLAG"
  echo "Initialization complete."
else
  echo "Already initialized. Skipping initialization."
fi

if [ $# -gt 0 ]; then
  MYSQL_OPTS=(-h127.0.0.1 -P2881 -uroot)
  if [ -n "${ROOT_PASSWORD:-}" ]; then
    wait_for_mysql "$ROOT_PASSWORD" "$WAIT_FOR_SERVICE_READY_ATTEMPTS"
    MYSQL_OPTS+=("-p${ROOT_PASSWORD}")
  else
    wait_for_mysql "" "$WAIT_FOR_SERVICE_READY_ATTEMPTS"
  fi

  if [ -n "${SEEKDB_DATABASE:-}" ]; then
    MYSQL_OPTS+=("-D${SEEKDB_DATABASE}")
  fi

  echo "Executing sql: $*"
  mysql "${MYSQL_OPTS[@]}" -e "$*"
  exit $?
fi

echo "Seekdb started"
echo "Start seekdb health check loop"
while pgrep seekdb >/dev/null; do
  sleep 5
done

echo "Seekdb process not found. Exiting."
exit 1
