#!/bin/bash -e

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
HOOKS_DIR="${SCRIPT_DIR}"/.git/hooks

echo 'Installing pre-push hook...'

mkdir -p "${HOOKS_DIR}"
echo '#!/bin/bash -e
remote="$1"
url="$2"

if [[ $url = "git@github.com:cf-platform-eng/tile-generator.git" ]]; then
  ./scripts/run_local_tests.sh withcache
fi

exit 0' > "${HOOKS_DIR}"/pre-push

chmod +x "${HOOKS_DIR}"/pre-push

echo 'Done!'
