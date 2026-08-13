#!/usr/bin/env bash
# Load supported SSH settings from project .env and run one remote command. Run with Shell required_permissions: ["all"].
set -euo pipefail

if (( $# > 1 )); then
  printf 'FAIL: expected zero or one remote command\n' >&2
  exit 2
fi

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"
[[ -f .env ]] || { printf 'FAIL: .env not found\n' >&2; exit 1; }

die() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

trimmed_value() {
  local value=$1
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  TRIMMED_VALUE=$value
}

contains_control_character() {
  local value=$1 char index
  for ((index = 0; index < ${#value}; index++)); do
    char=${value:index:1}
    case $char in
      $'\a'|$'\b'|$'\t'|$'\n'|$'\v'|$'\f'|$'\r'|$'\e'|$'\177')
        return 0
        ;;
    esac
  done
  return 1
}

parse_value() {
  local value=$1 first last inner
  trimmed_value "$value"
  value=$TRIMMED_VALUE
  [[ -n $value ]] || { PARSED_VALUE=; return; }

  first=${value:0:1}
  last=${value: -1}
  if [[ $first == "'" || $first == '"' ]]; then
    (( ${#value} >= 2 )) || die "unmatched quote on .env line $line_number"
    [[ $last == "$first" ]] || die "unmatched quote on .env line $line_number"
    inner=${value:1:${#value}-2}
    [[ $inner != *"$first"* ]] || die "unsupported quote syntax on .env line $line_number"
  elif [[ $last == "'" || $last == '"' ]]; then
    die "unmatched quote on .env line $line_number"
  else
    [[ $value != *"'"* && $value != *'"'* ]] || die "unmatched quote on .env line $line_number"
    [[ $value != *[[:space:]]* ]] || die "unsupported trailing syntax on .env line $line_number"
    inner=$value
  fi

  contains_control_character "$inner" && die "control character on .env line $line_number"
  PARSED_VALUE=$inner
}

SSH_HOST=
SSH_USERNAME=
SSH_PRIVATE_KEY_PATH=
SSH_PORT=
seen_host=0
seen_username=0
seen_key_path=0
seen_port=0
line_number=0
while IFS= read -r line || [[ -n $line ]]; do
  line_number=$((line_number + 1))
  trimmed_value "$line"
  line=$TRIMMED_VALUE
  [[ -z $line || ${line:0:1} == '#' ]] && continue

  if [[ $line == SSH_* || $line =~ ^export[[:space:]]+SSH_ ]]; then
    [[ $line =~ ^(export[[:space:]]+)?(SSH_[A-Za-z0-9_]+)[[:space:]]*=[[:space:]]*(.*)$ ]] || \
      die "malformed SSH_* assignment on .env line $line_number"
    key=${BASH_REMATCH[2]}
    raw_value=${BASH_REMATCH[3]}
    case $key in
      SSH_HOST)
        (( seen_host == 0 )) || die "duplicate $key on .env line $line_number"
        seen_host=1
        ;;
      SSH_USERNAME)
        (( seen_username == 0 )) || die "duplicate $key on .env line $line_number"
        seen_username=1
        ;;
      SSH_PRIVATE_KEY_PATH)
        (( seen_key_path == 0 )) || die "duplicate $key on .env line $line_number"
        seen_key_path=1
        ;;
      SSH_PORT)
        (( seen_port == 0 )) || die "duplicate $key on .env line $line_number"
        seen_port=1
        ;;
      *) continue ;;
    esac
    parse_value "$raw_value"
    case $key in
      SSH_HOST) SSH_HOST=$PARSED_VALUE ;;
      SSH_USERNAME) SSH_USERNAME=$PARSED_VALUE ;;
      SSH_PRIVATE_KEY_PATH) SSH_PRIVATE_KEY_PATH=$PARSED_VALUE ;;
      SSH_PORT) SSH_PORT=$PARSED_VALUE ;;
    esac
  fi
done < .env

[[ -n $SSH_HOST ]] || die 'SSH_HOST is missing or empty'
[[ $SSH_HOST =~ ^[A-Za-z0-9._:%-]+$ ]] || die 'SSH_HOST contains invalid characters'
[[ -n $SSH_USERNAME ]] || die 'SSH_USERNAME is missing or empty'
[[ $SSH_USERNAME =~ ^[A-Za-z_][A-Za-z0-9_.-]*$ ]] || die 'SSH_USERNAME contains invalid characters'
[[ -n $SSH_PRIVATE_KEY_PATH ]] || die 'SSH_PRIVATE_KEY_PATH is missing or empty'

if [[ -n $SSH_PORT ]]; then
  [[ $SSH_PORT =~ ^[0-9]+$ ]] || die 'SSH_PORT must be an integer from 1 to 65535'
  port_without_zeroes=${SSH_PORT#${SSH_PORT%%[!0]*}}
  [[ -n $port_without_zeroes ]] || die 'SSH_PORT must be an integer from 1 to 65535'
  (( ${#port_without_zeroes} <= 5 )) || die 'SSH_PORT must be an integer from 1 to 65535'
  if (( ${#port_without_zeroes} == 5 )) && (( 10#$port_without_zeroes > 65535 )); then
    die 'SSH_PORT must be an integer from 1 to 65535'
  fi
fi

# Quoted ~/path remains literal data. Match it without tilde expansion.
if [[ $SSH_PRIVATE_KEY_PATH == "~/"* ]]; then
  [[ -n ${HOME:-} ]] || die 'HOME is required to resolve SSH_PRIVATE_KEY_PATH'
  SSH_PRIVATE_KEY_PATH="$HOME/${SSH_PRIVATE_KEY_PATH#"~/"}"
fi

# Relative path → this local repo root
case "$SSH_PRIVATE_KEY_PATH" in
  /*) ;;
  *) SSH_PRIVATE_KEY_PATH="$REPO_ROOT/$SSH_PRIVATE_KEY_PATH" ;;
esac

[[ -f $SSH_PRIVATE_KEY_PATH ]] || die 'private key file not found after resolve'

remote_command='echo ok && hostname'
(( $# == 1 )) && remote_command=$1

ssh_argv=(
  ssh
  -F /dev/null
  -i "$SSH_PRIVATE_KEY_PATH"
  -o IdentitiesOnly=yes
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=10
)
[[ -n $SSH_PORT ]] && ssh_argv+=(-p "$SSH_PORT")
ssh_argv+=("$SSH_USERNAME@$SSH_HOST" "$remote_command")

"${ssh_argv[@]}"
