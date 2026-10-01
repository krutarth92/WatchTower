#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Expected one full Git commit SHA." >&2
  exit 2
fi

requested_sha="$1"
app_dir="/opt/watchtower"
compose=(docker compose --env-file .env.deploy -f compose.deploy.yaml)

cd "$app_dir"
test -f .env.deploy
mkdir -p .deploy
exec 9>.deploy/lock
flock -n 9 || {
  echo "Another staging deployment is active." >&2
  exit 3
}

git fetch --prune origin
git cat-file -e "${requested_sha}^{commit}"
git checkout --detach "$requested_sha"

previous_sha=""
if [[ -f .deploy/current ]]; then
  previous_sha="$(<.deploy/current)"
fi

export WATCHTOWER_IMAGE_TAG="$requested_sha"
"${compose[@]}" config --quiet
"${compose[@]}" build api
"${compose[@]}" up -d --wait postgres redis
"${compose[@]}" run --rm migrate

if ! "${compose[@]}" up -d --no-deps --wait api worker; then
  rollback_succeeded=false
  if [[ "$previous_sha" =~ ^[0-9a-f]{40}$ ]] \
    && docker image inspect "watchtower:${previous_sha}" >/dev/null 2>&1; then
    export WATCHTOWER_IMAGE_TAG="$previous_sha"
    if "${compose[@]}" up -d --no-deps --wait api worker; then
      rollback_succeeded=true
    fi
  fi
  if [[ "$rollback_succeeded" != true ]]; then
    "${compose[@]}" stop api worker || true
  fi
  echo "Staging deployment failed; database migrations were not downgraded." >&2
  exit 4
fi

if [[ "$previous_sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "$previous_sha" > .deploy/previous
fi
printf '%s\n' "$requested_sha" > .deploy/current
"${compose[@]}" ps
