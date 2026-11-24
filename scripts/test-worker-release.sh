#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
mkdir -p "$fixture/node_modules/.bin"
cp "$root/scripts/worker-release.sh" "$fixture/"
cat > "$fixture/node_modules/.bin/wrangler" <<'MOCK'
#!/bin/bash
set -euo pipefail
printf '%s\n' "$1 $2" >> calls
case "$1 $2" in
'deployments status')
  [[ -f active ]] || printf '%s' "$TEST_OLD" > active
  printf '{"versions":[{"version_id":"%s","percentage":100}]}\n' "$(cat active)" ;;
'versions upload')
  [[ "$3" == --name && "$4" == steep-meadow-46e1 && "$5" == --tag && "$6" == "github-$GITHUB_SHA" ]]
  printf '{"type":"version-upload","version_id":"%s","preview_url":"https://not-printed.example"}\n' "$TEST_NEW" >"$WRANGLER_OUTPUT_FILE_PATH" ;;
'versions view')
  printf '{"id":"%s","annotations":{"workers/tag":"%s"}}\n' "$TEST_NEW" "${TEST_TAG:-github-$GITHUB_SHA}" ;;
'versions deploy')
  [[ "$3" == "$TEST_NEW@100%" ]]
  printf '%s' "$TEST_NEW" > active ;;
*) exit 99 ;;
esac
MOCK
chmod +x "$fixture/node_modules/.bin/wrangler"
cd "$fixture"
export GITHUB_REPOSITORY=Troly2025/Verti GITHUB_REF=refs/heads/main
export GITHUB_SHA=4e5cdbc4ea8966ac93190552284361b4bd9239b2
export CLOUDFLARE_ACCOUNT_ID=d29afda5c9fd5a4bb66ffdab0e1d5ab1 CLOUDFLARE_API_TOKEN=local-placeholder-not-a-credential
export GITHUB_STEP_SUMMARY="$fixture/summary"
export TEST_OLD=11111111-1111-1111-1111-111111111111
export TEST_NEW=22222222-2222-2222-2222-222222222222
VERTI_OPERATION=stage bash worker-release.sh
test "$(cat active)" = "$TEST_OLD"
grep -Fq "$TEST_NEW" summary
! grep -q 'not-printed' summary
! grep -q 'versions deploy' calls
if VERTI_OPERATION=promote VERTI_VERSION_ID="$TEST_NEW" TEST_TAG=unexpected bash worker-release.sh 2>error; then exit 2; fi
grep -Fq 'not tagged for this exact main commit' error
test "$(cat active)" = "$TEST_OLD"
if VERTI_OPERATION=promote VERTI_VERSION_ID='not-a-uuid' bash worker-release.sh 2>error; then exit 3; fi
grep -Fq 'exact reviewed Cloudflare version UUID' error
if GITHUB_REF=refs/heads/other VERTI_OPERATION=stage bash worker-release.sh 2>error; then exit 4; fi
grep -Fq 'only on Troly2025/Verti main' error
VERTI_OPERATION=promote VERTI_VERSION_ID="$TEST_NEW" bash worker-release.sh
test "$(cat active)" = "$TEST_NEW"
grep -q 'serving 100%' summary
VERTI_OPERATION=promote VERTI_VERSION_ID="$TEST_NEW" bash worker-release.sh
test "$(grep -c 'versions deploy' calls)" -eq 1
printf 'Mock boundary QA passed: stage does not deploy; wrong tag, UUID and branch reject; exact reviewed version promotes once.\n'
