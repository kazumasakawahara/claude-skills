#!/usr/bin/env bash
# check-parity.sh — 配布前の機械検査（3 点）。すべて通れば 0 終了、1 つでも落ちれば非 0。
#
#   1. LEDGER テンプレートの写しの一致
#      deliberation-sim と hypothesis-arena は単体で配るため templates/LEDGER.md を
#      両方に持つ。「## 固有欄」より前（共通部分）が同一テキストであることを diff で確かめる。
#   2. 環境固有の語の混入検査
#      追跡ファイル全体（local.md.example と本スクリプトを除く）に、作者の環境に固有の
#      パス・人名・スキル名・法人名が 1 件も無いこと。
#   3. git archive に local.md が入らないこと
#
# 使い方:  scripts/check-parity.sh
set -uo pipefail

cd "$(git rev-parse --show-toplevel)"
fail=0

# ---- 1. LEDGER parity -------------------------------------------------------
A=skills/deliberation-sim/templates/LEDGER.md
B=skills/hypothesis-arena/templates/LEDGER.md
MARK='## 固有欄'
common_part() { awk -v m="$MARK" '$0 == m { exit } { print }' "$1"; }

if [ -f "$A" ] && [ -f "$B" ]; then
  if diff -u <(common_part "$A") <(common_part "$B"); then
    echo "OK  LEDGER common part is identical"
  else
    echo "NG  LEDGER common part differs (above)" >&2
    fail=1
  fi
else
  echo "NG  LEDGER.md missing: $A or $B" >&2
  fail=1
fi

# ---- 2. local-term scan -----------------------------------------------------
# 部分一致で探す語
terms=(
  'k-kawahara' '/Users/' 'AI-Workspace' 'Ai-Workspace' '河原'
  'my-assistant' 'my-knowledge' 'my-research' 'threads/'
  'wiki-crystallize' 'wiki-query' 'session-closing-check' 'skill-sync'
  'legal-research' 'snapshot-shared-docs' 'inspect-cue'
)
# 単語一致で探す語（"nested" "honest" 等の英単語を誤検知しないため）
word_terms=( 'nest' )

files=()
while IFS= read -r f; do
  case "$f" in
    */local.md.example) continue ;;
    scripts/check-parity.sh) continue ;;
  esac
  files+=("$f")
done < <(git ls-files)

hits=0
for t in "${terms[@]}"; do
  out=$(grep -n -F -- "$t" "${files[@]}" 2>/dev/null || true)
  if [ -n "$out" ]; then
    echo "NG  term '$t':" >&2
    printf '%s\n' "$out" >&2
    hits=$((hits + $(printf '%s\n' "$out" | wc -l)))
  fi
done
for t in "${word_terms[@]}"; do
  out=$(grep -n -w -- "$t" "${files[@]}" 2>/dev/null || true)
  if [ -n "$out" ]; then
    echo "NG  word '$t':" >&2
    printf '%s\n' "$out" >&2
    hits=$((hits + $(printf '%s\n' "$out" | wc -l)))
  fi
done
if [ "$hits" -eq 0 ]; then
  echo "OK  local-term scan: 0 hits in ${#files[@]} tracked files"
else
  echo "NG  local-term scan: ${hits} hit(s)" >&2
  fail=1
fi

# ---- 3. git archive must not contain local.md ------------------------------
if git archive HEAD | tar -t | grep -q '/local\.md$'; then
  echo "NG  git archive HEAD contains local.md" >&2
  fail=1
else
  echo "OK  git archive HEAD contains no local.md"
fi

exit "$fail"
