#!/bin/sh
# Encrypt .env into .env.enc — gitignored, NEVER commit it (the repo is public). Move it by hand. Run it YOURSELF:
#   sh scripts/env-lock.sh          -> prompts for a passphrase twice
#   ENV_PASS='...' sh scripts/env-lock.sh   (non-interactive; never type this through Claude)
set -eu
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "no .env here"; exit 1; }
if [ -n "${ENV_PASS:-}" ]; then
  openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -in .env -out .env.enc -pass env:ENV_PASS
else
  openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -in .env -out .env.enc
fi
echo "wrote .env.enc ($(wc -c < .env.enc) bytes) - it is gitignored: copy it to the laptop by hand (never git); keep the passphrase in your password manager"
