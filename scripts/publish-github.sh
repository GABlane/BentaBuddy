#!/bin/bash
# Run in your own Terminal; the coding session cannot write .git or authenticate Git pushes.
set -euo pipefail
cd "$(dirname "$0")/.."
repo_url='https://github.com/GABlane/BentaBuddy.git'
command -v git >/dev/null || { echo 'Install Git first.' >&2; exit 1; }
command -v gh >/dev/null || { echo 'Install GitHub CLI (gh) first.' >&2; exit 1; }
if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  gh auth login --hostname github.com --git-protocol https --web
fi
account=$(gh api user --jq .login)
if [[ "$account" != 'GABlane' ]]; then
  echo "Signed in as $account. Switch to GABlane with: gh auth switch --user GABlane" >&2
  exit 1
fi
gh auth setup-git --hostname github.com
if [[ ! -d .git && ! -f .git ]]; then
  git init -b main
fi
repo_root=$(git rev-parse --show-toplevel)
if [[ "$repo_root" != "$(pwd -P)" ]]; then
  echo 'This folder is inside a different repository. Stopping to protect that repository.' >&2
  exit 1
fi
if git remote get-url origin >/dev/null 2>&1; then
  if [[ "$(git remote get-url origin)" != "$repo_url" ]]; then
    echo 'origin points to another repository. No remote was changed.' >&2
    exit 1
  fi
else
  git remote add origin "$repo_url"
fi
git config user.name GABlane
if ! git config --get user.email >/dev/null; then
  git config user.email '154031355+GABlane@users.noreply.github.com'
fi
# Use a specific source-file list. Never stage models, databases, secrets, or the event PDF.
git add -- .gitignore .env.example BUILD_PLAN.md README.md index.html package.json package-lock.json tsconfig.json vite.config.ts requirements.txt requirements.lock.txt src backend scripts tests docs public
# Refuse a push if private/runtime files were staged separately before this script ran.
if git diff --cached --name-only | LC_ALL=C grep -E '(^|/)(data|node_modules|dist|\.runtime|\.venv)/|(^|/)\.env$|(^|/)\.env\.[^/]+$|\.sqlite3($|-)|\.pdf$' | LC_ALL=C grep -v '^\.env\.example$'; then
  echo 'Private/runtime files are staged. Unstage those files before publishing.' >&2
  exit 1
fi
if ! git diff --cached --quiet; then
  git commit -m 'Build BentaBuddy local AI bakery order manager'
fi
# A co-author trailer must never be introduced by this publishing script.
if git log -1 --format=%B | LC_ALL=C grep -qi '^Co-authored-by:'; then
  echo 'Latest commit includes a co-author trailer. Review it before publishing.' >&2
  exit 1
fi
git push --set-upstream origin HEAD:main
printf '\nPublished: https://github.com/GABlane/BentaBuddy\n'
git log -1 --format='Commit: %h%nAuthor: %an <%ae>%nMessage: %s'
