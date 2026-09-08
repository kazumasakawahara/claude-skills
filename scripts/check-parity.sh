#!/usr/bin/env bash
# check-parity.sh — 配布前の機械検査（3 点）。すべて通れば 0 終了、1 つでも落ちれば非 0。
#
#   1. LEDGER テンプレートの写しの一致
#      deliberation-sim と hypothesis-arena は単体で配るため templates/LEDGER.md を
#      両方に持つ。「## 固有欄」より前（共通部分）が同一テキストであることを diff で確かめる。
#   2. 環境固有の語の混入検査（保守者用。scripts/local-terms.txt があるときだけ）
#      追跡ファイル全体（local.md.example を除く）に、作者の環境に固有の
#      パス・人名・スキル名・法人名が 1 件も無いこと。語のリストは追跡外の
#      scripts/local-terms.txt（1 行 1 語。行頭 "word:" で単語一致、それ以外は部分一致、
#      "#" で始まる行は無視）。ファイルが無ければこの検査は「省略」と表示して他の 2 検査だけ回す。
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
  # プロセス置換 <(…) や一時ファイルは /dev/fd・TMPDIR が制限された環境（sandbox 等）で失敗するので、
  # 文字列で比較し、差分の表示だけ python3 があれば difflib で出す
  a_part=$(common_part "$A")
  b_part=$(common_part "$B")
  if [ "$a_part" = "$b_part" ]; then
    echo "OK  LEDGER common part is identical"
  else
    echo "NG  LEDGER common part differs:" >&2
    if command -v python3 >/dev/null 2>&1; then
      python3 - "$A" "$B" "$MARK" <<'PY' >&2
import sys, difflib
a, b, mark = sys.argv[1:4]
def common(p):
    out = []
    for line in open(p, encoding="utf-8"):
        if line.rstrip("\n") == mark:
            break
        out.append(line)
    return out
sys.stderr.writelines(difflib.unified_diff(common(a), common(b), a, b))
PY
    fi
    fail=1
  fi
else
  echo "NG  LEDGER.md missing: $A or $B" >&2
  fail=1
fi

# ---- 2. local-term scan (maintainer-only) -----------------------------------
TERMS_FILE=scripts/local-terms.txt
if [ ! -f "$TERMS_FILE" ]; then
  echo "SKIP local-term scan: ${TERMS_FILE} not found (maintainer-only check; untracked by design)"
else
  files=()
  while IFS= read -r f; do
    case "$f" in
      */local.md.example) continue ;;
    esac
    files+=("$f")
  done < <(git ls-files)

  hits=0
  nterms=0
  while IFS= read -r line; do
    case "$line" in
      ''|'#'*) continue ;;
    esac
    nterms=$((nterms + 1))
    case "$line" in
      word:*)
        t="${line#word:}"
        # 単語一致（"nested" "honest" 等の英単語を誤検知しないため）
        out=$(grep -n -w -- "$t" "${files[@]}" 2>/dev/null || true)
        ;;
      *)
        t="$line"
        out=$(grep -n -F -- "$t" "${files[@]}" 2>/dev/null || true)
        ;;
    esac
    if [ -n "$out" ]; then
      echo "NG  term '$t':" >&2
      printf '%s\n' "$out" >&2
      hits=$((hits + $(printf '%s\n' "$out" | wc -l)))
    fi
  done < "$TERMS_FILE"

  if [ "$nterms" -eq 0 ]; then
    echo "NG  local-term scan: ${TERMS_FILE} has no terms" >&2
    fail=1
  elif [ "$hits" -eq 0 ]; then
    echo "OK  local-term scan: 0 hits for ${nterms} terms in ${#files[@]} tracked files"
  else
    echo "NG  local-term scan: ${hits} hit(s)" >&2
    fail=1
  fi
fi

# ---- 3. git archive must not contain local.md ------------------------------
if git archive HEAD | tar -t | grep -q '/local\.md$'; then
  echo "NG  git archive HEAD contains local.md" >&2
  fail=1
else
  echo "OK  git archive HEAD contains no local.md"
fi

exit "$fail"
