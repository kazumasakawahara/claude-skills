#!/usr/bin/env bash
# build-release.sh — スキル単位の配布 ZIP を git のツリーから生成する
#
# 使い方:  scripts/build-release.sh [tag]      （tag 省略時は HEAD）
# 出力:    dist/<skill-name>.zip  （ZIP のルートは <skill-name>/SKILL.md）
#
# git archive で作るので、追跡外のファイル（local.md、*.bak*、.DS_Store 等）は
# 構造的に入らない。作業ツリーに何が転がっていても配布物には影響しない。
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
tag="${1:-HEAD}"
skills=(deliberation-sim hypothesis-arena acceptance-inspector)

mkdir -p dist
status=0
for name in "${skills[@]}"; do
  out="dist/${name}.zip"
  rm -f "$out"
  git archive --format=zip --prefix="${name}/" -o "$out" "${tag}:skills/${name}"

  # 検査 1: ZIP に local.md が入っていない
  if unzip -Z1 "$out" | grep -q '/local\.md$'; then
    echo "NG  ${out}: local.md が含まれている" >&2
    status=1
  fi
  # 検査 2: <name>/SKILL.md がルート直下にある
  if ! unzip -Z1 "$out" | grep -qx "${name}/SKILL.md"; then
    echo "NG  ${out}: ${name}/SKILL.md が無い" >&2
    status=1
  fi
  printf 'built %s (%s entries, %s bytes)\n' "$out" "$(unzip -Z1 "$out" | wc -l | tr -d ' ')" "$(wc -c < "$out" | tr -d ' ')"
done

exit "$status"
