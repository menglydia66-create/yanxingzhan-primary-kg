#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 上海语星宝教育科技有限公司
"""质检：字段、去重、无环、前置不倒序、难度单调、禁词、讲解长度、诊断卡、传递约简、必需前置≤3。
用法：python3 scripts/validate.py
      python3 scripts/validate.py --fix-levels
有任何 ERROR 时退出码为 1，不得合入。"""
import json, re, sys, unicodedata
from common import load, position, required_depth, level_from_depth, DATA

REQUIRED = ["id", "subject", "name", "kind", "topic_chain", "difficulty_level", "textbook_refs",
            "essence", "mastery", "explain", "pitfalls", "parent_check", "oral_diagnosis", "status"]
# 全库扫描（引流/人设/广告）
BANNED = ["名师", "特级教师", "教龄", "15年", "十五年", "一线教师", "提分", "保分", "保过", "包过", "必考", "押题", "秒杀", "满分",
          "竞赛", "奥数", "杯赛", "超前", "抢跑", "先学", "预习班", "一对一", "补课", "提高班", "培优",
          "扫码", "公众号", "微信搜", "视频号", "小店", "家长课", "启蒙课", "付费课", "买课", "完整版见", "更多内容见", "关注我", "加微信", "私信", "点赞", "评论区", "领取", "报名", "限时", "优惠", "价格", "¥", "元/",
          "最好", "第一", "唯一", "100%", "保证", "冲刺"]
# 家长可读字段额外禁词（报告 v0）：必须 / 一定要 / 落后 —— 用内容域扫描，避免误伤「不一定要」
CONTENT_BANNED = ["必须", "一定要", "落后", "提分", "超前", "冲刺", "保证"]
CONTENT_KEYS_TOP = ("name", "essence", "parent_check")
VERIFICATION_OK = {"已核-官方", "已核-双源", "已核-单源", "待核对"}
EXPLAIN_WARN, EXPLAIN_MAX = 320, 400

def norm(s):
    s = unicodedata.normalize('NFKC', s)
    return re.sub(r'[\s\W_（）()“”"：:、，,。.！!？?]+', '', s).lower()

def explain_len(t):
    e = t['explain']
    parts = [e.get('scene', ''), e.get('hook', ''), e.get('example', '')] + e.get('steps', []) + list(e.get('mistake', {}).values())
    return sum(len(p) for p in parts)

def content_blobs(t):
    """家长会直接读到的字段。"""
    blobs = [t.get(k, '') for k in CONTENT_KEYS_TOP]
    blobs += t.get('mastery', []) + t.get('pitfalls', [])
    e = t.get('explain', {})
    blobs += [e.get('scene', ''), e.get('hook', ''), e.get('example', '')] + e.get('steps', [])
    m = e.get('mistake', {})
    blobs += [m.get('wrong', ''), m.get('right', ''), m.get('why', '')]
    od = t.get('oral_diagnosis') or {}
    blobs.append(od.get('fallback', ''))
    for q in od.get('questions', []):
        blobs += [q.get('ask', ''), q.get('pass', ''), q.get('misconception', '')]
    return blobs

def has_content_banned(text, word):
    if word == '一定要':
        # 允许「不一定要」
        return bool(re.search(r'(?<!不)一定要', text))
    return word in text

def transitive_redundant(required_edges):
    """required_edges: list of (a,b). Return set of redundant (a,c) where a→…→c via other required edges."""
    from collections import defaultdict
    succ = defaultdict(set)
    for a, b in required_edges:
        succ[a].add(b)
    def reaches(src, dst, banned_edge):
        stack = [src]
        seen = {src}
        while stack:
            u = stack.pop()
            for v in succ.get(u, ()):
                if (u, v) == banned_edge:
                    continue
                if v == dst:
                    return True
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        return False
    red = set()
    for a, b in required_edges:
        if reaches(a, b, (a, b)):
            red.add((a, b))
    return red

def main():
    fix = '--fix-levels' in sys.argv
    topics, deps, chains, files = load()
    errs, warns = [], []
    E = errs.append; W = warns.append
    byid = {}
    chain_ids = {c['chain_id'] for c in chains}
    # 1 字段
    for t in topics:
        for k in REQUIRED:
            if k not in t: E(f"{t.get('id')} 缺字段 {k}")
        if t['id'] in byid: E(f"ID 重复：{t['id']}")
        byid[t['id']] = t
        if t['topic_chain']['chain_id'] not in chain_ids: E(f"{t['id']} 主题链 {t['topic_chain']['chain_id']} 未在 chains.json 登记")
        for k in ('scene', 'hook', 'steps', 'mistake'):
            if not t['explain'].get(k): E(f"{t['id']} 讲法缺 {k}（讲法五件套不全）")
        for m in t['mastery']:
            if not m.startswith('能'): W(f"{t['id']} 掌握标准建议以“能”开头：{m}")
        n = explain_len(t)
        if n > EXPLAIN_MAX: E(f"{t['id']} 讲解 {n} 字，超过上限 {EXPLAIN_MAX}")
        elif n > EXPLAIN_WARN: W(f"{t['id']} 讲解 {n} 字，偏长（建议 ≤{EXPLAIN_WARN}）")
        # textbook_refs
        for i, r in enumerate(t.get('textbook_refs') or []):
            if 'verification' not in r: E(f"{t['id']} textbook_refs[{i}] 缺 verification")
            elif r['verification'] not in VERIFICATION_OK: E(f"{t['id']} verification 非法：{r['verification']}")
            for fld in ('edition', 'unit_name', 'unit_id'):
                if not r.get(fld): E(f"{t['id']} textbook_refs[{i}] 缺 {fld}")
            # 不允许空猜：若写了具体单元却标待核对以外的假已核——仅告警由人工；这里拦「待核对」却编造数字年级缺失
        # oral_diagnosis
        od = t.get('oral_diagnosis')
        if not od:
            E(f"{t['id']} 缺 oral_diagnosis")
        else:
            qs = od.get('questions') or []
            if not (1 <= len(qs) <= 3): E(f"{t['id']} oral_diagnosis.questions 要 1–3 条，实际 {len(qs)}")
            for qi, q in enumerate(qs):
                for k in ('ask', 'pass', 'misconception'):
                    if not q.get(k): E(f"{t['id']} oral_diagnosis.questions[{qi}] 缺 {k}")
            if not od.get('fallback'): E(f"{t['id']} oral_diagnosis 缺 fallback")
            if qs and t.get('parent_check') and t['parent_check'] != qs[0].get('ask'):
                W(f"{t['id']} parent_check 与 oral_diagnosis 第一问不一致")
        # 全库禁词
        blob = json.dumps(t, ensure_ascii=False)
        for w in BANNED:
            if w in blob: E(f"{t['id']} 含禁用词「{w}」")
        # 内容域禁词
        for piece in content_blobs(t):
            for w in CONTENT_BANNED:
                if has_content_banned(piece, w):
                    E(f"{t['id']} 讲解/诊断含禁词「{w}」：{piece[:40]}…")
    # 2 去重
    seen = {}
    for t in topics:
        k = (t['subject'], norm(t['name']))
        if k in seen: E(f"疑似重复知识点：{seen[k]} 与 {t['id']}（{t['name']}）")
        seen[k] = t['id']
    # 3 边
    edges = set()
    req_edges = []
    req_in = {i: [] for i in byid}
    for d in deps:
        a, b = d['from'], d['to']
        if a not in byid or b not in byid: E(f"前置边引用不存在的 ID：{a}→{b}"); continue
        if a == b: E(f"自环：{a}")
        if (a, b) in edges: E(f"重复边：{a}→{b}")
        edges.add((a, b))
        if d['strength'] not in ('必需', '有帮助'): E(f"{a}→{b} strength 只能是 必需/有帮助")
        if not d.get('reason'): E(f"{a}→{b} 缺 reason")
        pa, pb = position(byid[a]), position(byid[b])
        if pa > pb:
            (E if d['strength'] == '必需' else W)(f"前置倒序：{a}{pa} 出现在 {b}{pb} 之后（{d['strength']}）")
        ca, cb = byid[a]['topic_chain'], byid[b]['topic_chain']
        if ca['chain_id'] == cb['chain_id'] and d['strength'] == '必需' and ca['step'] >= cb['step']:
            E(f"主题链步号倒序：{a}(step {ca['step']}) 应排在 {b}(step {cb['step']}) 前")
        if d['strength'] == '必需':
            req_edges.append((a, b))
            req_in[b].append(a)
    # 必需前置 ≤3
    for tid, preds in req_in.items():
        if len(preds) > 3:
            E(f"{tid} 必需前置 {len(preds)} 个 >3：{preds}")
    # 传递约简：冗余必需边报 ERROR
    red = transitive_redundant(req_edges)
    for a, b in sorted(red):
        E(f"传递冗余必需边（应删）：{a}→{b}")
    # 4 无环
    indeg = {i: 0 for i in byid}; out = {i: [] for i in byid}
    for a, b in edges: indeg[b] += 1; out[a].append(b)
    q = [i for i, v in indeg.items() if v == 0]; cnt = 0
    while q:
        i = q.pop(); cnt += 1
        for j in out[i]:
            indeg[j] -= 1
            if indeg[j] == 0: q.append(j)
    if cnt != len(byid): E(f"前置关系有环，涉及：{[i for i, v in indeg.items() if v > 0]}")
    # 5 难度
    depth = required_depth(topics, deps)
    for t in topics:
        sug = level_from_depth(depth[t['id']])
        if t['difficulty_level'] == 0 and fix:
            t['difficulty_level'] = sug
        lv = t['difficulty_level']
        if lv == 0: E(f"{t['id']} 未定难度档（可用 --fix-levels 按规则回填）"); continue
        if abs(lv - sug) > 1: E(f"{t['id']} 难度 D{lv} 与规则建议 D{sug} 相差超过1档")
        elif lv != sug and not t.get('difficulty_note'): E(f"{t['id']} 人工调档 D{sug}→D{lv} 但没写 difficulty_note")
    for d in deps:
        if d['strength'] == '必需' and d['from'] in byid and d['to'] in byid:
            if byid[d['to']]['difficulty_level'] < byid[d['from']]['difficulty_level']:
                E(f"难度倒挂：{d['to']} 比它的必需前置 {d['from']} 档位低")
    if fix:
        for f, items in files.items():
            json.dump(items, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
            open(f, 'a', encoding='utf-8').write('\n')
    for w in warns: print('WARN ', w)
    for e in errs: print('ERROR', e)
    print(f"共 {len(topics)} 个知识点、{len(deps)} 条前置边；ERROR {len(errs)}，WARN {len(warns)}")
    sys.exit(1 if errs else 0)

if __name__ == '__main__':
    main()
