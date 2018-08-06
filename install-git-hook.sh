#!/bin/bash -e

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"

echo 'Installing pre-push hook...'

echo '#!/bin/bash -e
remote="$1"
url="$2"

if [[ $url = "git@github.com:cf-platform-eng/tile-generator.git" ]]; then
  ./scripts/run_local_tests.sh withcache
fi

exit 0' > "${SCRIPT_DIR}"/.git/hooks/pre-push

chmod +x "${SCRIPT_DIR}"/.git/hooks/pre-push

echo 'Done!'
