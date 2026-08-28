#!/bin/sh
# Decrypt .env.enc back into .env on a new machine:
#   sh scripts/env-unlock.sh        -> prompts for the passphrase
#   ENV_PASS='...' sh scripts/env-unlock.sh
set -eu
cd "$(dirname "$0")/.."
[ -f .env.enc ] || { echo "no .env.enc here - git pull first"; exit 1; }
if [ -f .env ]; then echo ".env already exists; move it aside first"; exit 1; fi
if [ -n "${ENV_PASS:-}" ]; then
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in .env.enc -out .env -pass env:ENV_PASS
else
  openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in .env.enc -out .env
fi
chmod 600 .env 2>/dev/null || true
echo "wrote .env ($(grep -c '' .env) lines). It is gitignored; never commit it."
