#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  refresh-australia-db.sh --repo-dir PATH [--branch NAME]

Required:
  --repo-dir   Local clone path used for the weekly refresh.

Optional:
  --branch     Git branch to track. Defaults to main.

The script updates the clone, builds the load file and database in a temporary
build directory, and then writes the finished database file into
<repo-dir>/db/Australia.db.
EOF
}

repo_dir=""
branch="main"
repo_url="https://github.com/mynativeplant/Australia.git"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo-dir)
      repo_dir="${2:-}"
      shift 2
      ;;
    --branch)
      branch="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$repo_dir" ]]; then
  usage >&2
  exit 2
fi

for tool in git python3 db_load install; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "Missing required tool: $tool" >&2
    exit 1
  fi
done

if [[ -e "$repo_dir" && ! -d "$repo_dir/.git" ]]; then
  echo "Repository path exists but is not a git checkout: $repo_dir" >&2
  exit 1
fi

if [[ ! -d "$repo_dir/.git" ]]; then
  echo "Cloning $repo_url into $repo_dir"
  mkdir -p "$(dirname "$repo_dir")"
  git clone --branch "$branch" --single-branch "$repo_url" "$repo_dir"
else
  echo "Updating existing clone at $repo_dir"
  git -C "$repo_dir" fetch --prune origin "$branch"
  git -C "$repo_dir" checkout -B "$branch" "origin/$branch"
  git -C "$repo_dir" reset --hard "origin/$branch"
fi

build_dir="$(mktemp -d)"
cleanup() {
  rm -rf "$build_dir"
}
trap cleanup EXIT

dbload_txt="$build_dir/plant-family.dbload.txt"
db_file="$build_dir/Australia.db"

echo "Building database load file"
python3 "$repo_dir/scripts/build-db-load-file.py" \
  --root "$repo_dir" \
  --output "$dbload_txt"

echo "Running db_load"
db_load -T -t btree -f "$dbload_txt" "$db_file"

echo "Installing database to $repo_dir/db/Australia.db"
mkdir -p "$repo_dir/db"
install -m 0644 "$db_file" "$repo_dir/db/Australia.db"

echo "Updated database: $repo_dir/db/Australia.db"
