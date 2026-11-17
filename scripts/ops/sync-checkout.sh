#!/usr/bin/env bash
# Refresh a clean main/feed checkout. Never stash, reset, commit, or push.
set -euo pipefail
repo=${1:?usage: sync-checkout.sh /absolute/repository}
cd -- "$repo"
common=$(git rev-parse --git-common-dir)
exec 9>"$common/local-sync.lock"
flock -n 9 || { echo 'Another sync is running'; exit 0; }
branch=$(git symbolic-ref --quiet --short HEAD) || { echo 'Detached checkout; skipped'; exit 0; }
case "$branch" in main|feed) ;; *) echo "Working branch $branch; skipped"; exit 0 ;; esac
if [[ -n $(git status --porcelain --untracked-files=normal) ]]; then
    echo 'Local changes present; skipped'
    exit 0
fi
for operation in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
    if [[ -e $(git rev-parse --git-path "$operation") ]]; then
        echo 'Git operation in progress; skipped'
        exit 0
    fi
done
git fetch --no-tags origin "refs/heads/$branch:refs/remotes/origin/$branch"
target=$(git rev-parse "refs/remotes/origin/$branch")
if ! git merge-base --is-ancestor HEAD "$target"; then
    echo 'Local commits or divergence present; skipped'
    exit 0
fi
# Recheck after network I/O before changing tracked files.
[[ $(git symbolic-ref --quiet --short HEAD) == "$branch" ]]
[[ -z $(git status --porcelain --untracked-files=normal) ]]
git -c core.hooksPath=/dev/null merge --ff-only --no-edit "$target"
