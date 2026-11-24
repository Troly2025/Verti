#!/usr/bin/env bash
set -euo pipefail

worker=steep-meadow-46e1
wrangler=./node_modules/.bin/wrangler
fail() { printf '::error::%s\n' "$*" >&2; exit 1; }

[[ "${GITHUB_REPOSITORY:-}" == Troly2025/Verti && "${GITHUB_REF:-}" == refs/heads/main ]] ||
  fail "Release is allowed only on Troly2025/Verti main."
[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || fail "GitHub commit SHA is invalid."
[[ "${CLOUDFLARE_ACCOUNT_ID:-}" == d29afda5c9fd5a4bb66ffdab0e1d5ab1 ]] ||
  fail "Cloudflare account is not the configured production account."
[[ -n "${CLOUDFLARE_API_TOKEN:-}" ]] || fail "Repository Actions secret CLOUDFLARE_API_TOKEN is missing."
tag="github-$GITHUB_SHA"

uuid='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
id="${VERTI_VERSION_ID:-}"
case "${VERTI_OPERATION:-}" in
  stage) [[ -z "$id" ]] || fail "Leave version_id empty when staging." ;;
  promote) [[ "$id" =~ $uuid ]] || fail "Enter the exact reviewed Cloudflare version UUID." ;;
  *) fail "Choose stage or promote." ;;
esac

dir=$(mktemp -d)
trap 'rm -rf -- "$dir"' EXIT
# Do not echo raw Wrangler output in the public repository's Actions logs.
# Version URLs are public if enabled on the Worker, even if omitted from logs.
active_version() {
  "$wrangler" deployments status --name "$worker" --json 2>"$dir/err" |
    node -e '
      const fs = require("node:fs");
      try {
        const {versions} = JSON.parse(fs.readFileSync(0, "utf8"));
        if (versions?.length !== 1 || versions[0].percentage !== 100) process.exit(1);
        const id = versions[0].version_id;
        if (!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/.test(id)) process.exit(1);
        console.log(id);
      } catch { process.exit(1); }'
}
active=$(active_version) || fail "Could not verify the expected single 100% deployment on the existing Worker. Check account, Worker and token scope."
printf 'Prior active version (rollback): `%s`.\n\n' "$active" >>"$GITHUB_STEP_SUMMARY"

if [[ "$VERTI_OPERATION" == stage ]]; then
  if ! WRANGLER_OUTPUT_FILE_PATH="$dir/output.jsonl" "$wrangler" versions upload --name "$worker" --tag "$tag" \
    --message "GitHub main $GITHUB_SHA" >"$dir/upload" 2>&1; then
    fail "Cloudflare did not confirm the upload. Check Deployments before retrying."
  fi
  staged=$(node - "$dir/output.jsonl" <<'JS'
const fs = require('node:fs');
try {
  const rows = fs.readFileSync(process.argv[2], 'utf8').trim().split('\n').map(JSON.parse);
  console.log(rows.findLast(row => row.type === 'version-upload')?.version_id ?? '');
} catch { process.exit(1); }
JS
  ) || fail "Unable to recover the new version UUID. Look up the GitHub commit tag in Deployments before retrying."
  [[ "$staged" =~ $uuid ]] || fail "Cloudflare did not return a valid version UUID. Check Deployments before retrying."
  after=$(active_version) || fail "Version uploaded, but the active deployment could not be verified. Check Deployments before retrying."
  [[ "$after" == "$active" ]] || fail "Active deployment changed during staging. Inspect Deployments before proceeding."
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    printf 'version_id=%s\nprevious_version=%s\n' "$staged" "$active" >>"$GITHUB_OUTPUT"
  fi
  printf 'Staged version: `%s`.\n\n' "$staged" >>"$GITHUB_STEP_SUMMARY"
  printf 'Find tag `%s` in the Worker Deployments. No live traffic was promoted.\n' "$tag" >>"$GITHUB_STEP_SUMMARY"
  exit 0
fi

if [[ -n "${VERTI_EXPECTED_ACTIVE_VERSION:-}" && "$active" != "$VERTI_EXPECTED_ACTIVE_VERSION" ]]; then
  fail "The prior active version changed after staging; refusing to promote."
fi
if ! "$wrangler" versions view "$id" --name "$worker" --json >"$dir/version.json" 2>"$dir/err"; then
  fail "The exact version could not be read from the target Worker."
fi
if ! node - "$dir/version.json" "$id" "$tag" <<'JS'
const fs = require('node:fs');
try {
  const v = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
  const matches = v.id === process.argv[3] && v.annotations?.['workers/tag'] === process.argv[4];
  if (!matches) process.exit(1);
} catch { process.exit(1); }
JS
then
  fail "Version is not tagged for this exact main commit. Review the intended staged version; do not guess."
fi

if [[ "$active" == "$id" ]]; then
  printf 'Version `%s` is already serving 100%%; nothing changed.\n' "$id" >>"$GITHUB_STEP_SUMMARY"
  exit 0
fi
if ! "$wrangler" versions deploy "$id@100%" --name "$worker" --yes \
  --message "Promote reviewed GitHub main $GITHUB_SHA" >"$dir/promote" 2>&1; then
  fail "Cloudflare did not confirm promotion. Check Deployments before retrying."
fi
after=$(active_version) || fail "Promotion was accepted, but active traffic could not be verified. Inspect Deployments before retrying."
[[ "$after" == "$id" ]] || fail "Promotion was accepted, but another version remains active. Inspect Deployments before retrying."
printf 'Verified version `%s` serving 100%%. Verify both live language routes before reporting publication.\n' "$id" >>"$GITHUB_STEP_SUMMARY"
