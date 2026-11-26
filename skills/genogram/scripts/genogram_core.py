# -*- coding: utf-8 -*-
"""ジェノグラム（家族関係の図）を描く。

モデルは使わない。標準ライブラリだけで動き、同じ入力からは同じ図が出る。入力は人ごとの記録（形は SKILL.md）。
- genogram_svg(persons, spread_past=False, dead_style="cross")：SVG の文字列を返す。男性□・女性○・性別の記載なし◇、死亡は×（dead_style="fill" なら黒塗り）、同居の範囲は破線の囲み、年齢は記号の中。
  資料に書かれていない人（placeholder）は破線の記号と「情報なし」。凡例つき。記号は資料に記載された性別を表す
  中心の人（"center": true）は二重の枠。印の無い記録では、図は前と変わらない
  2 人の関係の線：婚姻＝二重線、離婚＝二重線に // と年月（年だけでもよい）、事実婚・内縁＝破線、その解消＝破線に // と年月、婚姻外の親どうし＝点線と「婚姻外」
  親族の線は推し量らない。資料に無い親族関係は線を引かず、注記に「資料に記載なし（戸籍で確かめる）」と出す（kinship_gaps）
- inference_notes(persons)：資料に書かれていない人、推し量った点（親族関係以外）、資料に記載のない親族関係の一覧。図の下の注記に使う
- layout(persons)：人ごとの位置（横は枠の単位、縦は世代）

配置：家族の単位（血縁の人＋婚姻で入った人、その子）ごとに幅を計算し、子を左から並べて親をその中央に置く。
根の夫婦は男性を左、婚姻で入った人は相手の右。子は年齢の高い順。同居の範囲は世代ごとの同居の人の左右の端をつないだ囲み。
"""
SEX_LABELS = {"male": "男性", "female": "女性", "not_recorded": "記載なし", "unknown": "記載なし"}   # unknown は古い値（not_recorded と同じに読む）
INFERRED = "推認"

SLOT, ROW_H, SYM, MARGIN, TOP = 150, 130, 40, 40, 50
C_LINE, C_COHABIT, C_TEXT, C_SUB = "#333333", "#2f7ac0", "#222222", "#555555"
LABEL_PAD = 6                                                # ひとりの親の字を、下りる線から離す幅
GAP = 2.5                                                    # 二重線の半分の間隔
DOUBLE = ("married", "divorced")
LINE_DASH = {"de_facto": "6,4", "de_facto_ended": "6,4", "non_marital": "1.5,3"}
LINE_LEGEND = (("married", "二重線＝婚姻"), ("divorced", "二重線に //＝離婚"), ("de_facto", "破線＝事実婚・内縁"),
               ("de_facto_ended", "破線に //＝事実婚の解消"), ("non_marital", "点線＝婚姻外の親どうし"))
PAST = ("divorced", "de_facto_ended", "non_marital")


def _status(pmap, a, b):
    for p, o in ((a, b), (b, a)):
        for x in pmap[p].get("partners") or []:
            if isinstance(x, dict) and x.get("person") == o:
                return x.get("status")
    return None


def _esc(v):
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _n(v):
    return ("%.1f" % v).rstrip("0").rstrip(".")


def _val(p, k):
    a = p.get(k)
    return a.get("value") if isinstance(a, dict) else None


def _recs(persons):
    out, seen = [], set()
    for p in persons.get("persons") or []:
        if isinstance(p, dict) and p.get("id") and p["id"] not in seen:
            seen.add(p["id"])
            out.append(p)
    return out


def kinship_gaps(persons):
    """資料に記載のない親族関係（誤りにも警告にもしない。図の注記と確認の一覧に「資料に記載なし（戸籍で確かめる）」として出す）。
    資料に書かれている人ごとに、記録の順で：親が 1 人だけ（one_parent）、親 2 人の間に partners の線がない（parents_without_line）。親が 0 人の人は出さない。"""
    recs = _recs(persons)
    pmap = dict((p["id"], p) for p in recs)
    out = []
    for p in recs:
        if p.get("placeholder"):
            continue
        ps = []
        for x in p.get("parents") or []:
            if isinstance(x, dict) and x.get("person") in pmap and x["person"] not in ps:
                ps.append(x["person"])
        if len(ps) == 1:
            out.append({"person": p["id"], "kind": "one_parent", "parents": ps})
        elif len(ps) >= 2:
            linked = lambda a, b: any(isinstance(y, dict) and y.get("person") == b for y in pmap[a].get("partners") or [])
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    if not (linked(ps[i], ps[j]) or linked(ps[j], ps[i])):
                        out.append({"person": p["id"], "kind": "parents_without_line", "parents": [ps[i], ps[j]]})
    return out


# ---- 配置 ----------------------------------------------------------------------------

def _structure(recs):
    ids = [p["id"] for p in recs]
    pmap = dict((p["id"], p) for p in recs)
    parents = dict((pid, [x.get("person") for x in pmap[pid].get("parents") or [] if x.get("person") in pmap]) for pid in ids)
    partners = dict((pid, []) for pid in ids)
    for pid in ids:
        for x in pmap[pid].get("partners") or []:
            o = x.get("person")
            if o in pmap and o != pid:
                if o not in partners[pid]:
                    partners[pid].append(o)
                if pid not in partners[o]:
                    partners[o].append(pid)
    children = dict((pid, [c for c in ids if pid in parents[c]]) for pid in ids)
    return ids, pmap, parents, partners, children


def _age_key(pmap, ids):
    def key(c):
        a = _val(pmap[c], "age")
        return (0 if isinstance(a, int) and not isinstance(a, bool) else 1, -(a if isinstance(a, int) and not isinstance(a, bool) else 0), ids.index(c))
    return key


def layout(persons, spread_past=False):
    """{id: (x_slot, generation)} と構造。x は slot 単位（中心）。
    spread_past を真にすると、続いている相手がいない人の、終わった関係の相手を左右に分けて置く（既定は偽。偽のときの配置は前と変わらない）。"""
    recs = _recs(persons)
    ids, pmap, parents, partners, children = _structure(recs)
    key = _age_key(pmap, ids)
    placed = {}

    def free(p, taken):
        return [s for s in partners[p] if not parents[s] and s not in placed and s != p and s not in taken]

    def unit(head):
        spouses = free(head, ())
        extra = [q for s in spouses for q in free(s, [head] + spouses)]
        if len(spouses) < 2 and not extra:
            members = [head] + spouses
            if not parents[head] and spouses and (_val(pmap[head], "sex") == "female"):
                members = spouses + [head]                          # 根の夫婦は男性を左
        else:
            # 相手が複数：終わった関係・婚姻外の相手は左、続いている相手は右。相手の別の相手は、その相手の外側。線が隣どうしを結ぶ
            left = [s for s in spouses if _status(pmap, head, s) in PAST]
            right = [s for s in spouses if s not in left]
            if spread_past and len(left) >= 2 and not right:      # 続いている相手がいないとき：終わった関係の最後の 1 人を右に置く（線が隣どうしを結ぶ）
                right = [left.pop()]
            members, taken = [head], [head] + spouses
            for s in left:
                more = free(s, taken)
                taken += more
                members = more + [s] + members
            for s in right:
                more = free(s, taken)
                taken += more
                members = members + [s] + more
        kids = sorted(set(c for m in members for c in children[m]), key=key)
        return members, kids

    def width(head, seen):
        members, kids = unit(head)
        seen = seen | set(members)
        w = sum(width(k, seen) for k in kids if k not in seen)
        return max(len(members), w)

    def place(head, x0, gen):
        members, kids = unit(head)
        w = width(head, set())
        for i, m in enumerate(members):
            placed[m] = (x0 + w / 2.0 - (len(members) - 1) / 2.0 + i, gen)
        todo = [k for k in kids if k not in placed]
        x = x0 + (w - sum(width(k, set(members)) for k in todo)) / 2.0         # 子の並びを親の中央の下に
        for k in todo:
            kw = width(k, set(members))
            place(k, x, gen + 1)
            x += kw

    x = 0.0
    for pid in ids:
        if pid in placed or parents[pid]:
            continue
        if any(not parents[s] and s in placed for s in partners[pid]):
            continue
        # 根：子のある人を頭に（配偶者だけの根は相手の単位で置かれる）
        if not children[pid] and any(children[s] for s in partners[pid]):
            continue
        w = width(pid, set())                                         # 置く前に測る（置いた後は相手が置き済みで狭く測れる）
        place(pid, x, 0)
        x += w
    for pid in ids:                                                   # 取り残し（親が記録にない等）
        if pid not in placed:
            placed[pid] = (x + 0.5, 0)
            x += 1
    return placed, pmap, parents, partners, children


# ---- 図 ------------------------------------------------------------------------------

def _label(p):
    name = p.get("name", p["id"])
    if p.get("placeholder"):
        alive = p.get("alive") if isinstance(p.get("alive"), dict) else {}
        if alive.get("value") is False and alive.get("inferred"):
            return "%s（死亡・%s）" % (name, INFERRED)
        return "%s（情報なし）" % name
    if _val(p, "alive") is False:
        return "%s（死亡）" % name
    return name


def genogram_svg(persons, spread_past=False, dead_style="cross"):
    """dead_style：死亡の表し方。"cross"（既定。記号に×）か "fill"（記号を黒く塗る。×は描かない）。"""
    placed, pmap, parents, partners, children = layout(persons, spread_past)
    xs = [v[0] for v in placed.values()] or [0]
    gens = max([v[1] for v in placed.values()] or [0]) + 1
    minx = min(xs)
    W = int(max((max(xs) - minx + 1) * SLOT + 2 * MARGIN, 640))
    W = max(W, 2 * MARGIN + 640)
    shown = set()
    for pid in placed:
        for o in partners[pid]:
            if o in placed:
                shown.add(_status(pmap, *sorted((pid, o), key=lambda v: placed[v][0])))
    line_rows, row, used = [], [], 0
    for st, label in LINE_LEGEND:                                      # 凡例の線は図に出た種類だけ。幅を超えたら折り返す
        if st not in shown:
            continue
        iw = 36 + 11 * len(label)
        if row and used + iw > W - 2 * MARGIN:
            line_rows.append(row)
            row, used = [], 0
        row.append((st, label))
        used += iw
    if row:
        line_rows.append(row)
    legend_rows = 2 + len(line_rows)
    H = TOP + gens * ROW_H + 52 + 18 * legend_rows

    def X(pid):
        return MARGIN + (placed[pid][0] - minx + 0.5) * SLOT

    def Y(pid):
        return TOP + placed[pid][1] * ROW_H + SYM / 2.0

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" font-family="Hiragino Sans, sans-serif" font-size="11">' % (W, H, W, H),
           '<rect x="0" y="0" width="%d" height="%d" fill="#ffffff"/>' % (W, H)]
    # 同居の範囲（世代ごとの左右の端をつなぐ囲み）
    rows = []
    for g in range(gens):
        co = [pid for pid in placed if placed[pid][1] == g and _val(pmap[pid], "cohabiting") is True]
        if co:
            rows.append((min(X(p) for p in co) - SYM, max(X(p) for p in co) + SYM, TOP + g * ROW_H - 12, TOP + (g + 1) * ROW_H - 12))
    if rows:
        pts = [(rows[0][0], rows[0][2]), (rows[0][1], rows[0][2])]
        for i, (l, r, t, b) in enumerate(rows):
            if i:
                pts.append((r, t))
            pts.append((r, b))
        for i in range(len(rows) - 1, -1, -1):
            l, r, t, b = rows[i]
            pts.append((l, b))
            pts.append((l, t))
        out.append('<path class="cohabit" d="M %s z" fill="none" stroke="%s" stroke-width="1.2" stroke-dasharray="5,4"/>' % (
            " L ".join("%s %s" % (_n(x), _n(y)) for x, y in pts), C_COHABIT))
        l, r, t, b = rows[-1]
        out.append('<text x="%s" y="%s" font-size="10" fill="%s">同居</text>' % (_n(l + 4), _n(b - 4), C_COHABIT))
    # 2 人の関係の線
    pair_status = {}
    done = set()
    for pid in placed:
        for o in partners[pid]:
            pair = tuple(sorted((pid, o)))
            if pair in done or o not in placed:
                continue
            done.add(pair)
            a, b = sorted(pair, key=lambda v: X(v))
            y = Y(a)
            x1, x2 = X(a) + SYM / 2.0, X(b) - SYM / 2.0
            links = [x for x in pmap[a].get("partners") or [] if x.get("person") == b] + [x for x in pmap[b].get("partners") or [] if x.get("person") == a]
            st = _status(pmap, a, b)
            pair_status[pair] = st
            line = '<line x1="%s" y1="%%s" x2="%s" y2="%%s" stroke="%s" stroke-width="%s"%s/>'
            if st in DOUBLE:
                body = [line % (_n(x1), _n(x2), C_LINE, "1.2", "") % (_n(y - GAP), _n(y - GAP)), line % (_n(x1), _n(x2), C_LINE, "1.2", "") % (_n(y + GAP), _n(y + GAP))]
            elif st in LINE_DASH:
                body = [line % (_n(x1), _n(x2), C_LINE, "1.4", ' stroke-dasharray="%s"' % LINE_DASH[st]) % (_n(y), _n(y))]
            else:
                body = [line % (_n(x1), _n(x2), C_LINE, "1", "") % (_n(y), _n(y))]
            out.append('<g class="partner %s">%s</g>' % (_esc(st or "none"), "".join(body)))
            mx = (x1 + x2) / 2.0
            if st in ("divorced", "de_facto_ended"):
                key, word, cls = ("divorced", "離婚", "divorce") if st == "divorced" else ("ended", "解消", "ended")
                out.append('<g class="%s"><line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.4"/><line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.4"/></g>' % (
                    cls, _n(mx - 6), _n(y + 8), _n(mx - 1), _n(y - 8), C_LINE, _n(mx), _n(y + 8), _n(mx + 5), _n(y - 8), C_LINE))
                when = next((x.get(key) for x in links if x.get(key)), None)
                label = ("%s.%s %s" % (tuple(str(when).split("-")[:2]) + (word,))) if when and "-" in str(when) else ("%s %s" % (when, word) if when else word)
                out.append('<text x="%s" y="%s" font-size="10" text-anchor="middle" fill="%s">%s</text>' % (_n(mx), _n(y - 12), C_SUB, _esc(label)))
            elif st == "non_marital":
                out.append('<text x="%s" y="%s" font-size="10" text-anchor="middle" fill="%s">婚姻外</text>' % (_n(mx), _n(y - 6), C_SUB))
    # 親子
    groups = {}
    for pid in placed:
        ps = tuple(sorted(p for p in parents[pid] if p in placed))
        if ps:
            groups.setdefault(ps, []).append(pid)
    lone_parents = set(ps[0] for ps in groups if len(ps) == 1)
    for ps, kids in sorted(groups.items()):
        ax = sum(X(p) for p in ps) / float(len(ps))
        ay = (Y(ps[0]) + (GAP if pair_status.get(ps) in DOUBLE else 0)) if len(ps) > 1 else Y(ps[0]) + SYM / 2.0
        top = min(Y(k) for k in kids) - SYM / 2.0
        bar = top - 18
        kx = sorted(X(k) for k in kids)
        out.append('<line class="descent" x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.2"/>' % (_n(ax), _n(ay), _n(ax), _n(bar), C_LINE))
        out.append('<line class="sibling" x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.2"/>' % (_n(min(kx + [ax])), _n(bar), _n(max(kx + [ax])), _n(bar), C_LINE))
        for k in kids:
            out.append('<line class="descent" x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.2"/>' % (_n(X(k)), _n(bar), _n(X(k)), _n(top), C_LINE))
    # 記号
    for pid in sorted(placed, key=lambda v: (placed[v][1], placed[v][0])):
        p = pmap[pid]
        cx, cy = X(pid), Y(pid)
        sex = _val(p, "sex") if _val(p, "sex") in ("male", "female") else "not_recorded"
        cls = sex + (" placeholder" if p.get("placeholder") else "")
        dash = ' stroke-dasharray="4,3"' if p.get("placeholder") else ""
        h = SYM / 2.0
        filled = dead_style == "fill" and _val(p, "alive") is False     # 死亡を黒塗りで表す図の、亡くなった人
        body = C_LINE if filled else "#ffffff"
        if sex == "male":
            out.append('<rect class="%s" x="%s" y="%s" width="%d" height="%d" fill="%s" stroke="%s" stroke-width="1.6"%s/>' % (cls, _n(cx - h), _n(cy - h), SYM, SYM, body, C_LINE, dash))
        elif sex == "female":
            out.append('<circle class="%s" cx="%s" cy="%s" r="%s" fill="%s" stroke="%s" stroke-width="1.6"%s/>' % (cls, _n(cx), _n(cy), _n(h), body, C_LINE, dash))
        else:
            out.append('<path class="%s" d="M %s %s L %s %s L %s %s L %s %s z" fill="%s" stroke="%s" stroke-width="1.6"%s/>' % (
                cls, _n(cx), _n(cy - h), _n(cx + h), _n(cy), _n(cx), _n(cy + h), _n(cx - h), _n(cy), body, C_LINE, dash))
        if p.get("center") is True:                                   # 中心の人：記号の内側にもう 1 本の枠（二重の枠）
            g = h - 4
            inner = "#ffffff" if filled else C_LINE
            if sex == "male":
                out.append('<rect class="center" x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="1"/>' % (_n(cx - g), _n(cy - g), _n(2 * g), _n(2 * g), inner))
            elif sex == "female":
                out.append('<circle class="center" cx="%s" cy="%s" r="%s" fill="none" stroke="%s" stroke-width="1"/>' % (_n(cx), _n(cy), _n(g), inner))
            else:
                out.append('<path class="center" d="M %s %s L %s %s L %s %s L %s %s z" fill="none" stroke="%s" stroke-width="1"/>' % (
                    _n(cx), _n(cy - g), _n(cx + g), _n(cy), _n(cx), _n(cy + g), _n(cx - g), _n(cy), inner))
        if _val(p, "alive") is False and not filled:
            out.append('<g class="dead"><line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.4"/><line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.4"/></g>' % (
                _n(cx - h), _n(cy - h), _n(cx + h), _n(cy + h), C_LINE, _n(cx - h), _n(cy + h), _n(cx + h), _n(cy - h), C_LINE))
        age = _val(p, "age")
        if isinstance(age, int) and not isinstance(age, bool):
            out.append('<text x="%s" y="%s" font-size="13" font-weight="bold" text-anchor="middle"%s>%d</text>' % (_n(cx), _n(cy + 5), ' fill="#ffffff"' if filled else "", age))
        elif p.get("placeholder") and _val(p, "alive") is not False:
            out.append('<text x="%s" y="%s" font-size="13" text-anchor="middle" fill="%s">?</text>' % (_n(cx), _n(cy + 5), C_SUB))
        # ひとりの親（自分の記号の下から子へ線が下りる人）は、字を線の右に置く（線が字の上を通らない）
        tx, anchor = (cx + LABEL_PAD, "") if pid in lone_parents else (cx, ' text-anchor="middle"')
        out.append('<text x="%s" y="%s" font-size="11" font-weight="bold"%s fill="%s">%s</text>' % (_n(tx), _n(cy + h + 15), anchor, C_TEXT, _esc(_label(p))))
        rel = _val(p, "relation")
        if rel and not p.get("placeholder"):
            out.append('<text x="%s" y="%s" font-size="10"%s fill="%s">%s</text>' % (_n(tx), _n(cy + h + 29), anchor, C_SUB, _esc(rel)))
    # 凡例：1 行目は性別の記号の断り、2 行目は記号（いつも）、3 行目は図に出た線だけ
    lx = MARGIN
    ly = H - 18 * legend_rows - 4
    out.append('<text x="%d" y="%d" font-size="10" fill="%s">記号は資料に記載された性別</text>' % (lx, ly + 10, C_SUB))
    if kinship_gaps(persons):                                          # 記載のない親族関係がある図にだけ出す
        out.append('<text x="%d" y="%d" font-size="10">線の無い親族関係＝資料に記載なし（戸籍で確かめる）</text>' % (lx + 170, ly + 10))
    if any(p.get("center") is True for p in pmap.values()):          # 中心の人がいる図にだけ出す
        out.append('<rect x="%d" y="%d" width="12" height="12" fill="#ffffff" stroke="%s"/><rect x="%d" y="%d" width="6" height="6" fill="none" stroke="%s"/>'
                   '<text x="%d" y="%d" font-size="10">二重の枠＝中心の人</text>' % (lx + 480, ly, C_LINE, lx + 483, ly + 3, C_LINE, lx + 498, ly + 10))
    ly += 18
    out.append('<rect x="%d" y="%d" width="12" height="12" fill="#ffffff" stroke="%s"/><text x="%d" y="%d" font-size="10">男性</text>' % (lx, ly, C_LINE, lx + 16, ly + 10))
    out.append('<circle cx="%d" cy="%d" r="6" fill="#ffffff" stroke="%s"/><text x="%d" y="%d" font-size="10">女性</text>' % (lx + 56, ly + 6, C_LINE, lx + 66, ly + 10))
    out.append('<path d="M %d %d L %d %d L %d %d L %d %d z" fill="#ffffff" stroke="%s"/><text x="%d" y="%d" font-size="10">性別の記載なし</text>' % (
        lx + 108, ly, lx + 114, ly + 6, lx + 108, ly + 12, lx + 102, ly + 6, C_LINE, lx + 118, ly + 10))
    dead_word, dx = ("黒塗り＝死亡", 20) if dead_style == "fill" else ("×＝死亡", 0)     # 黒塗りの凡例は 2 字長いので、右の項目を寄せる
    out.append('<text x="%d" y="%d" font-size="10">%s　記号の中の数字＝年齢　破線の記号＝資料に記載なし（情報なし）</text>' % (lx + 200, ly + 10, dead_word))
    out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-dasharray="5,4"/><text x="%d" y="%d" font-size="10">同居の範囲</text>' % (
        lx + 560 + dx, ly + 6, lx + 590 + dx, ly + 6, C_COHABIT, lx + 596 + dx, ly + 10))
    for row in line_rows:
        ly += 18
        x = lx
        for st, label in row:
            yy = ly + 6
            if st in DOUBLE:
                out.append('<line x1="%d" y1="%s" x2="%d" y2="%s" stroke="%s"/><line x1="%d" y1="%s" x2="%d" y2="%s" stroke="%s"/>' % (
                    x, _n(yy - GAP), x + 28, _n(yy - GAP), C_LINE, x, _n(yy + GAP), x + 28, _n(yy + GAP), C_LINE))
            else:
                out.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="1.4" stroke-dasharray="%s"/>' % (x, yy, x + 28, yy, C_LINE, LINE_DASH[st]))
            out.append('<text x="%d" y="%d" font-size="10">%s</text>' % (x + 34, ly + 10, _esc(label)))
            x += 36 + 11 * len(label)
    out.append("</svg>\n")
    return "\n".join(out)


# ---- 注記 ------------------------------------------------------------------------------

FIELD_WORDS = {"relation": "続柄", "sex": "性別", "age": "年齢", "cohabiting": "同居", "alive": "生死", "health": "健康・障害", "services": "制度・サービスの利用",
               "role": "家の中の役割", "agencies": "関わる機関"}


def _show(k, v):
    if k == "alive":
        return "存命" if v else "死亡"
    if k == "cohabiting":
        return "同居" if v else "別居"
    if k == "sex":
        return SEX_LABELS.get(v, v)
    return str(v)


def inference_notes(persons):
    recs = _recs(persons)
    names = dict((p["id"], p.get("name", p["id"])) for p in recs)
    out = []
    for p in recs:
        parts = []
        for k in FIELD_WORDS:
            a = p.get(k) if isinstance(p.get(k), dict) else {}
            if a.get("inferred") and a.get("value") not in (None, ""):
                parts.append("%s は%s（%s。理由：%s）" % (FIELD_WORDS[k], _show(k, a["value"]), INFERRED, a["inferred"]))
        if p.get("placeholder"):
            out.append("%s：相談資料に記載がない（情報なし）。%s" % (p.get("name", p["id"]), "。".join(parts) + "。" if parts else ""))
        elif parts:
            out.append("%s：%s。" % (p.get("name", p["id"]), "。".join(parts)))
    for g in kinship_gaps(persons):                                    # 資料に記載のない親族関係
        if g["kind"] == "one_parent":
            out.append("%s：もう一方の親は資料に記載なし（戸籍で確かめる）。" % names.get(g["person"], g["person"]))
        else:
            out.append("%s：親 %s と %s の関係は資料に記載なし（戸籍で確かめる）。" % tuple(names.get(x, x) for x in [g["person"]] + g["parents"]))
    return out
