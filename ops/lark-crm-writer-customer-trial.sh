#!/usr/bin/env bash
set -euo pipefail

# Reviewed replacement template; install separately as root:ccconnect 0550.
# The same protected bot/profile performs both CRM and personnel lookups.
# batch_get_id requires contact:user.id:readonly and visible contacts; get-user
# must also expose name and is_activated/is_frozen/is_resigned. Unknown status
# is blocked, not treated as an active colleague. This has not been live-tested.
# Input email means contact.user.email, NOT enterprise_email. No user OAuth.
expected_version=1.0.90
profile=crm-writer
cli=/usr/local/libexec/lark-cli-1.0.90

usage() {
  printf '%s\n' 'The CRM writer accepts only fixed CRM and personnel operations.' >&2
  exit 64
}

if (( $# == 1 )) && [[ $1 == whoami ]]; then
  :
elif (( $# >= 2 )) && [[ $1 == base ]]; then
  case "$2" in
    +field-list|+record-get|+record-list|+record-search|+record-batch-create|+record-batch-update) ;;
    *) usage ;;
  esac
else
  # Validate the complete personnel argv, not merely its endpoint prefix.
  python3 - "$@" <<'PY' || usage
import json
import re
import sys

args = sys.argv[1:]
valid = False
if (len(args) == 8 and args[:3] == ['contact', '+get-user', '--user-id']
        and re.fullmatch(r'ou_[A-Za-z0-9]+', args[3])
        and args[4:] == ['--user-id-type', 'open_id', '--format', 'json']):
    valid = True
elif (len(args) == 7 and args[:4] == [
        'api', 'POST', '/open-apis/contact/v3/users/batch_get_id', '--params']
        and args[5] == '--data'):
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('duplicate field')
                result[key] = value
            return result
        params = json.loads(args[4], object_pairs_hook=unique)
        data = json.loads(args[6], object_pairs_hook=unique)
        if isinstance(data, dict) and params == {'user_id_type': 'open_id'} and data.get('include_resigned') is False:
            key = 'emails' if 'emails' in data else 'mobiles'
            values = data.get(key)
            if set(data) == {key, 'include_resigned'} and isinstance(values, list) and len(values) == 1 and isinstance(values[0], str):
                pattern = r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+' if key == 'emails' else r'(?:1[0-9]{10}|\+[1-9][0-9]{5,14})'
                valid = len(values[0]) <= 254 and re.fullmatch(pattern, values[0]) is not None
    except (TypeError, ValueError):
        pass
raise SystemExit(0 if valid else 64)
PY
fi

for argument in "$@"; do
  case "$argument" in
    --profile|--profile=*|--as|--as=*|--yes) usage ;;
  esac
done

[[ -x $cli ]] || { printf '%s\n' 'Pinned CRM lark-cli is unavailable.' >&2; exit 69; }
[[ $("$cli" --version 2>/dev/null) == "lark-cli version $expected_version" ]] || {
  printf '%s\n' 'Pinned CRM lark-cli version check failed.' >&2
  exit 69
}
export LARKSUITE_CLI_NO_UPDATE_NOTIFIER=1
export LARKSUITE_CLI_NO_SKILLS_NOTIFIER=1
unset MYANC_CRM_HOST_SECRET MYANC_CRM_HOST_SECRET_FILE
unset MYANC_CRM_ACTION_TOKEN MYANC_CRM_STAGE_INPUT
exec "$cli" "$@" --profile "$profile" --as bot
