#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人ごとの記録（persons.json）を検査して、ジェノグラムの SVG を書き出す。

使い方: draw.py persons.json [-o genogram.svg] [--only id,id,...] [--dead fill|cross] [--font フォントの名前]
  --only：図を分けるとき。並べた id の人だけを描く（記録は書き換えない。描かない人への線は、その図では省く）。
  検査で誤りがあれば、図を書かずに誤りを表示して終わる（終了コード 1）。
  誤りが無ければ SVG を書き、警告と図の下に添える注記を表示する（終了コード 0）。

モデルは使わない。標準ライブラリだけで動く。検査は check(persons)、値の形をそろえるのは normalize(persons)。
"""
import argparse
import copy
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import genogram_core  # noqa: E402

ATTRS = ("relation", "sex", "age", "cohabiting", "alive", "health", "services", "role", "agencies")
KINSHIP_ATTRS = ("relation", "sex", "alive")          # 推し量ってはいけない欄
SEXES = ("male", "female", "not_recorded", "unknown")
STATUSES = ("married", "divorced", "de_facto", "de_facto_ended", "non_marital", "couple")
DATE_KEYS = {"divorced": "divorced", "ended": "de_facto_ended"}   # 年月の欄 → その欄を持てる状態
DATE_RE = re.compile(r"^\d{4}(-\d{2})?$")              # 年月（YYYY-MM）か、年だけ（YYYY）


def normalize(data):
    """書きやすい形を、描く道具の形にそろえる。
    人の並びだけ → {"persons": 並び}。"age": 45 → {"value": 45}。"parents": ["a"] → [{"person": "a"}]。"""
    if isinstance(data, list):
        data = {"persons": data}
    if not isinstance(data, dict) or not isinstance(data.get("persons"), list):
        return data
    for p in data["persons"]:
        if not isinstance(p, dict):
            continue
        for k in ATTRS:
            if k in p and not isinstance(p[k], dict):
                p[k] = {"value": p[k]}
        for k in ("parents", "partners"):
            if isinstance(p.get(k), list):
                p[k] = [{"person": x} if isinstance(x, str) else x for x in p[k]]
    return data


def add_couples(data):
    """同じ子の親である 2 人（父と母）に、2 人の関係が何も書かれていないとき、婚姻の線（married）で結ぶ。結んだ組（名前の組）の並びを返す。"""
    persons = [p for p in data.get("persons") or [] if isinstance(p, dict) and isinstance(p.get("id"), str)]
    pmap = dict((p["id"], p) for p in persons)
    added = []
    for c in persons:
        ps = []
        for x in c.get("parents") or []:
            o = x.get("person") if isinstance(x, dict) else None
            if o in pmap and o != c["id"] and o not in ps:
                ps.append(o)
        if len(ps) != 2:
            continue
        a, b = ps
        linked = any(isinstance(y, dict) and y.get("person") == t for s, t in ((a, b), (b, a)) for y in pmap[s].get("partners") or [])
        if linked:
            continue
        for s, t in ((a, b), (b, a)):
            if not isinstance(pmap[s].get("partners"), list):
                pmap[s]["partners"] = []
            pmap[s]["partners"].append({"person": t, "status": "married"})
        added.append((pmap[a].get("name", a), pmap[b].get("name", b)))
    return added


def subset(data, keep):
    """keep に並べた id の人だけの記録を作る（図を分けるとき）。描かない人を指す parents・partners は、その図では省く。
    返り値：(記録, 描かない人の名前の並び, 記録にない id の並び)。元の記録は書き換えない。"""
    persons = [p for p in data.get("persons") or [] if isinstance(p, dict)]
    known = [p.get("id") for p in persons]
    missing = [k for k in keep if k not in known]
    out, left = [], []
    for p in persons:
        if p.get("id") not in keep:
            left.append(p.get("name", p.get("id")))
            continue
        q = dict(p)
        for k in ("parents", "partners"):
            if isinstance(q.get(k), list):
                q[k] = [x for x in q[k] if not (isinstance(x, dict) and x.get("person") in known and x.get("person") not in keep)]
        out.append(q)
    return {"persons": out}, left, missing


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def check(data):
    """{"errors": [[種類, 説明]], "warnings": [[種類, 説明]]} を返す。誤りが 1 件でもあれば描かない。"""
    errors, warnings = [], []
    if not isinstance(data, dict) or not isinstance(data.get("persons"), list) or not data["persons"]:
        return {"errors": [["bad_shape", '{"persons": [人, ...]} の形になっていない（人が 1 人もいない）']], "warnings": []}
    ids, pmap = [], {}
    for i, p in enumerate(data["persons"]):
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not p["id"]:
            errors.append(["bad_shape", "%d 番目の人に id（文字列）が無い" % (i + 1)])
            continue
        if p["id"] in pmap:
            errors.append(["duplicate_id", "id が重なっている：%s" % p["id"]])
            continue
        ids.append(p["id"])
        pmap[p["id"]] = p
    if errors:
        return {"errors": errors, "warnings": warnings}

    def val(p, k):
        return (p.get(k) or {}).get("value") if isinstance(p.get(k), dict) else None

    centers = [pid for pid in ids if pmap[pid].get("center") is True]
    if len(centers) > 1:
        errors.append(["multiple_center", "中心の人（center）が 2 人以上いる：%s。中心の人は 1 人だけ" % "・".join(centers)])
    parents = {}
    for pid in ids:
        p = pmap[pid]
        if p.get("center") not in (True, False, None):
            errors.append(["bad_flag", "%s：center は true／false（中心の人だけ true）" % pid])
        for k in KINSHIP_ATTRS:
            if isinstance(p.get(k), dict) and p[k].get("inferred"):
                errors.append(["kinship_inferred", "%s：%s に推し量った理由（inferred）が付いている。続柄・性別・生死は、述べられたことだけを書く" % (pid, k)])
        if val(p, "sex") not in SEXES + (None,):
            errors.append(["bad_sex", "%s：sex は male／female／not_recorded のどれか（分からなければ書かない）" % pid])
        if val(p, "age") is not None and not (_is_int(val(p, "age")) and val(p, "age") >= 0):
            errors.append(["bad_age", "%s：age は 0 以上の整数（分からなければ書かない）" % pid])
        for k in ("cohabiting", "alive"):
            if val(p, k) not in (True, False, None):
                errors.append(["bad_flag", "%s：%s は true／false（分からなければ書かない）" % (pid, k)])
        for k in ("parents", "partners"):
            for x in p.get(k) or []:
                if isinstance(x, dict) and x.get("inferred"):
                    errors.append(["kinship_inferred", "%s：%s の線に推し量った理由（inferred）が付いている。親子・夫婦の線は、述べられたことだけを書く" % (pid, k)])
        ps = []
        for x in p.get("parents") or []:
            o = x.get("person") if isinstance(x, dict) else None
            if o not in pmap:
                errors.append(["unknown_person", "%s：parents の相手が記録にない：%s" % (pid, o)])
            elif o == pid:
                errors.append(["self_reference", "%s：自分を親にしている" % pid])
            elif o not in ps:
                ps.append(o)
        if len(ps) > 2:
            errors.append(["too_many_parents", "%s：親が 3 人以上ある（養親と実親を 1 つの図に描くことはできない）" % pid])
        parents[pid] = ps
        for x in p.get("partners") or []:
            o = x.get("person") if isinstance(x, dict) else None
            if o not in pmap:
                errors.append(["unknown_person", "%s：partners の相手が記録にない：%s" % (pid, o)])
                continue
            if o == pid:
                errors.append(["self_reference", "%s：自分を相手にしている" % pid])
                continue
            st = x.get("status")
            if st not in STATUSES:
                errors.append(["bad_partner_status", "%s と %s：status は %s のどれか" % (pid, o, "／".join(STATUSES))])
            for dk, need in DATE_KEYS.items():
                if x.get(dk) is None:
                    continue
                if not (isinstance(x[dk], str) and DATE_RE.match(x[dk])):
                    errors.append(["bad_date", "%s と %s：%s は YYYY-MM か YYYY の形（西暦）" % (pid, o, dk)])
                elif st != need:
                    errors.append(["partner_date_mismatch", "%s と %s：%s の年月は status が %s のときだけ書ける" % (pid, o, dk, need)])
            back = [y.get("status") for y in pmap[o].get("partners") or [] if isinstance(y, dict) and y.get("person") == pid]
            if back and st in STATUSES and any(b != st for b in back) and pid < o:
                errors.append(["partner_status_mismatch", "%s と %s：2 人の側で status が違う" % (pid, o)])

    def ancestors(pid, seen):
        for a in parents.get(pid, []):
            if a in seen:
                return True
            if ancestors(a, seen | {a}):
                return True
        return False

    for pid in ids:
        if ancestors(pid, {pid}):
            errors.append(["parent_cycle", "%s：親子の線が輪になっている" % pid])
            break
    if not errors:
        for pid in ids:
            n = len(set(x["person"] for x in pmap[pid].get("partners") or []))
            if n >= 4:
                warnings.append(["many_partners", "%s：相手が %d 人いる。きれいに描けるのは 3 人まで。4 人目からは、線どうしが重なる" % (pid, n)])
        placed = genogram_core.layout(data, True, True)[0]             # 描くときと同じ配置で、ほかの人をまたぐ線を探す
        for pid in ids:
            others = set(x["person"] for x in pmap[pid].get("partners") or [])
            far = [o for o in others if any(placed[q][1] == placed[pid][1] and min(placed[pid][0], placed[o][0]) < placed[q][0] < max(placed[pid][0], placed[o][0]) for q in placed)]
            if far and len(others) >= 3 and any(pid in parents[c] for c in ids):
                warnings.append(["partners_children", "%s：相手が 3 人いて、子もいる。子へ下りる線が、記号の下に回した線をまたぐ。どの相手との子かが読み取れるかを、図を画像で確かめる" % pid])
        done = set()
        for pid in ids:
            for x in pmap[pid].get("partners") or []:
                o = x["person"]
                pair = tuple(sorted((pid, o)))
                if pair in done:
                    continue
                done.add(pair)
                if parents[pid] and parents[o]:
                    warnings.append(["both_sides_parents", "%s と %s：2 人とも親の記録がある。この道具は一方の家系だけを描く。"
                                     "2 人を結ぶ線がほかの人の記号に重なるので、どちらかの親を記録から外して描き直す" % pair])
    return {"errors": errors, "warnings": warnings}


def for_drawing(data):
    """図に渡す写し。名前と続柄が同じ人（名前を続柄にした人）は、続柄の段を出さない（同じ言葉が 2 段に並ぶため）。記録と注記は変えない"""
    shown = copy.deepcopy(data)
    for p in shown["persons"]:
        rel = p.get("relation")
        rel = rel.get("value") if isinstance(rel, dict) else rel
        if rel and p.get("name") == rel:
            del p["relation"]
    return shown


def main(argv=None):
    ap = argparse.ArgumentParser(description="persons.json を検査して、ジェノグラムの SVG を書き出す")
    ap.add_argument("persons")
    ap.add_argument("-o", "--output", default="genogram.svg")
    ap.add_argument("--only", help="図を分けるとき。描く人の id をコンマで並べる（記録は書き換えない）")
    ap.add_argument("--dead", choices=("fill", "cross"), default="fill", help="死亡の表し方。fill＝記号を黒く塗る（既定）、cross＝記号に×")
    ap.add_argument("--font", help="図の文字のフォント（その環境にある日本語のフォントの名前。PNG に変換するときに使う）")
    args = ap.parse_args(argv)
    with io.open(args.persons, encoding="utf-8") as f:
        data = normalize(json.load(f))
    left, whole = [], None
    if args.only and isinstance(data, dict):
        whole = data
        keep = [k.strip() for k in args.only.split(",") if k.strip()]
        data, left, missing = subset(data, keep)
        if missing:
            print("誤り [unknown_person] --only に、記録にない id がある：%s" % "・".join(missing))
            return 1
    joined = add_couples(data) if isinstance(data, dict) and isinstance(data.get("persons"), list) else []
    report = check(data)
    for kind, text in report["errors"]:
        print("誤り [%s] %s" % (kind, text))
    if report["errors"]:
        print("誤りが %d 件あるので、図は書いていない。" % len(report["errors"]))
        return 1
    with io.open(args.output, "w", encoding="utf-8") as f:
        svg = genogram_core.genogram_svg(for_drawing(data), spread_past=True, dead_style=args.dead, tidy=True)
        if args.font:
            svg = svg.replace('font-family="Hiragino Sans, sans-serif"', 'font-family="%s, sans-serif"' % args.font.replace('"', ""), 1)
        f.write(svg)
    print("図を書いた：%s" % args.output)
    for kind, text in report["warnings"]:
        print("警告 [%s] %s" % (kind, text))
    if left:
        print("この図に描いていない人（記録にはある）：%s" % "・".join(left))
    notes = genogram_core.inference_notes(data)
    if whole is not None:                                             # 分けた図：描かない人がいるために出た注記（記録の全体では出ないもの）は添えない
        all_notes = genogram_core.inference_notes(whole)
        notes = [n for n in notes if n in all_notes]
    names = dict((p.get("id"), p.get("name", p.get("id"))) for p in data["persons"])
    for a, b in joined:
        notes.append("%s と %s：婚姻は伝えられていない。両親として婚姻の線で結んだ（違えば直す）。" % (a, b))
    for p in data["persons"]:
        for x in p.get("parents") or []:
            if isinstance(x, dict) and x.get("assumed"):
                notes.append("%s：親を %s としたのは、続柄からの読み取り（伝えられてはいない。違えば直す）。" % (names.get(p.get("id")), names.get(x.get("person"))))
    if notes:
        print("図の下に添える注記：")
        for n in notes:
            print("- %s" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
