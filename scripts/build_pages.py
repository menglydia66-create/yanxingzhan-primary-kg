#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 上海语星宝教育科技有限公司
"""把 data/ 生成可读页面。"""
import os, re, json
from common import load, position, topo_order, ROOT

topics, deps, chains, _ = load()
byid = {t['id']: t for t in topics}
pre = {}; post = {}
for d in deps:
    pre.setdefault(d['to'], []).append(d); post.setdefault(d['from'], []).append(d)
SUBJ = {'数学': 'math', '语文': 'chinese', '英语': 'english'}
def page(t): return f"docs/知识点/{SUBJ[t['subject']]}/{t['id']}.md"
def ref_text(r):
    ver = r.get('verification', '')
    base = f"{r['edition']} {r['grade']}年级{r['term']} · {r['unit_name']}"
    if ver: base += f"（{ver}）"
    if r.get('note'): base += f"；{r['note']}"
    return base
SIGN = "\n---\n研星站 出品｜上海语星宝教育科技有限公司｜本页知识点名称与讲解均为自写，不含教材原文、原题和插图；教材位置以孩子手里的课本为准。｜这不是考试，也不需要家长批改。｜授权：图谱数据 CC BY 4.0，讲解文字 CC BY-NC-SA 4.0（机构商用需另行授权），详见仓库 LICENSE。\n"

os.makedirs(os.path.join(ROOT, 'docs', '知识点'), exist_ok=True)
for t in topics:
    e = t['explain']; m = e['mistake']; od = t['oral_diagnosis']
    L = [f"# {t['name']}｜{t['subject']}小学知识点讲解", "",
         f"> **一句话讲透：** {t['essence']}", "",
         f"- 难度档：D{t['difficulty_level']}　主题链：{t['topic_chain']['chain_name']}（第 {t['topic_chain']['step']} 步）",
         "- 对应教材：" + "；".join(ref_text(r) for r in t['textbook_refs']), "",
         "## 学它之前要会的（前置知识）"]
    L += [f"- [{byid[d['from']]['name']}](../{SUBJ[byid[d['from']]['subject']]}/{d['from']}.md)（{d['strength']}）：{d['reason']}" for d in pre.get(t['id'], [])] or ["- 无，可以直接学。"]
    L += ["", "## 怎么讲孩子容易懂", f"**① 从生活里引入：** {e['scene']}", "", f"**② 一句话本质：** {t['essence']}", "", f"**③ 口诀 / 类比：** {e['hook']}", "", "**④ 一步一步来：**"]
    L += [f"{i}. {s}" for i, s in enumerate(e['steps'], 1)]
    if e.get('example'): L += ["", f"**例子：** {e['example']}"]
    L += ["", "**⑤ 最常见的错：**", "", "| 常见想法 | 可以怎样 | 为什么 |", "|---|---|---|", f"| {m['wrong']} | {m['right']} | {m['why']} |", "",
          "## 易错点提示"] + [f"- {p}" for p in t['pitfalls']]
    L += ["", "## 怎样算学会了（掌握标准）"] + [f"- {x}" for x in t['mastery']]
    L += ["", "## 口头诊断卡（了解懂没懂，不是考试）", "", "一次一问，让孩子说出来。答完再问「你怎么想的」。"]
    for i, q in enumerate(od['questions'], 1):
        L += ["", f"**问 {i}：** {q['ask']}", f"- 通过：{q['pass']}", f"- 典型误概念：{q['misconception']}"]
    L += ["", f"**退步：** {od['fallback']}", "", "## 家长随口问一句（短版）", f"> {t['parent_check']}"]
    if t.get("error_understanding"):
        L += ["", "## 如何理解错题", t["error_understanding"]]
    if t.get("variant_pattern"):
        L += ["", "## 变题模式提示（不配原题）", t["variant_pattern"], "", "> 错题库全文与变式练习体系不在本开源库；这里只提示「可以怎么换」。"]
    else:
        L += ["", "## 变题模式提示（不配原题）", "用家里已有练习，只换数字或情境、不换本点考点；不搬课本原题。", "", "> 错题库全文与变式练习体系不在本开源库；这里只提示「可以怎么换」。"]
    L += ["", "## 学会以后接着学"]
    L += [f"- [{byid[d['to']]['name']}](../{SUBJ[byid[d['to']]['subject']]}/{d['to']}.md)" for d in post.get(t['id'], [])] or ["- （后续知识点陆续补充）"]
    L += ["", f"状态：{t['status']}｜更新：{t.get('updated','')}", SIGN]
    p = os.path.join(ROOT, page(t)); os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write("\n".join(L))

# 学习路线
L = ["# 学习路线：由易到难（按前置关系和难度排序）", "", "表里越靠前越早学（先满足前置关系，再按难度由低到高；「有帮助」的前置也会排在前面，所以偶尔会出现低档排在高档后面）。难度档 D1–D5 只看前置深度，与年级无关。想按校内进度查，看 [按教材查](按教材查.md)。", ""]
for s in ['数学', '语文', '英语']:
    sub = [t for t in topics if t['subject'] == s]
    if not sub: continue
    order = [i for i in topo_order(topics, deps) if byid[i]['subject'] == s]
    L += [f"## {s}", "", "| 顺序 | 难度 | 知识点 | 主题链 | 校内位置 |", "|---|---|---|---|---|"]
    for n, i in enumerate(order, 1):
        t = byid[i]; r = t['textbook_refs'][0]
        L.append(f"| {n} | D{t['difficulty_level']} | [{t['name']}](知识点/{SUBJ[s]}/{i}.md) | {t['topic_chain']['chain_name']} | {r['grade']}年级{r['term']} {r['unit_name']} |")
    L.append("")
open(os.path.join(ROOT, 'docs', '学习路线.md'), 'w', encoding='utf-8').write("\n".join(L) + SIGN)

# 按教材查
L = ["# 按教材查：孩子学到哪，就看哪", "", "只列教材版本、年级、册、单元名，不含教材原文。以孩子手里的课本为准。位置旁标注核对状态：已核 / 待核对。", ""]
rows = []
for t in topics:
    for r in t['textbook_refs']:
        rows.append((t['subject'], r['edition'], r['grade'], r['term'], r.get('unit_order', 0), r['unit_name'], r.get('verification', ''), t))
for s in ['数学', '语文', '英语']:
    L += [f"## {s}", "", "| 教材 | 年级/册 | 单元 | 核对 | 知识点 | 难度 |", "|---|---|---|---|---|---|"]
    for row in sorted([x for x in rows if x[0] == s], key=lambda x: (x[2], x[3] != '上', x[4], x[7]['id'])):
        t = row[7]
        L.append(f"| {row[1]} | {row[2]}年级{row[3]} | {row[5]} | {row[6]} | [{t['name']}](知识点/{SUBJ[s]}/{t['id']}.md) | D{t['difficulty_level']} |")
    L.append("")
open(os.path.join(ROOT, 'docs', '按教材查.md'), 'w', encoding='utf-8').write("\n".join(L) + SIGN)

# 主题链
L = ["# 主题链：跨年级把同一主题串起来", ""]
for c in chains:
    L += [f"## {c['chain_name']}（{c['subject']}）", "", f"方向：{c['summary']}", ""]
    for t in sorted([t for t in topics if t['topic_chain']['chain_id'] == c['chain_id']], key=lambda t: t['topic_chain']['step']):
        L.append(f"- 第 {t['topic_chain']['step']} 步 · D{t['difficulty_level']} · [{t['name']}](知识点/{SUBJ[t['subject']]}/{t['id']}.md)")
    L.append("")
open(os.path.join(ROOT, 'docs', '主题链.md'), 'w', encoding='utf-8').write("\n".join(L) + SIGN)

# README 索引
idx = ["<!-- INDEX:START 本区块由 scripts/build_pages.py 自动生成，勿手改 -->", ""]
for s in ['数学', '语文', '英语']:
    idx.append(f"**{s}**：" + "、".join(f"[{byid[i]['name']}]({page(byid[i])})" for i in topo_order(topics, deps) if byid[i]['subject'] == s))
    idx.append("")
idx.append("<!-- INDEX:END -->")
rp = os.path.join(ROOT, 'README.md')
if os.path.exists(rp):
    s = open(rp, encoding='utf-8').read()
    s = re.sub(r"<!-- INDEX:START.*?<!-- INDEX:END -->", "\n".join(idx), s, flags=re.S)
    # bump sample count mention if present
    s = re.sub(r"已有人教版数学一年级上册 \d+ 个点、统编版语文 \d+ 个点、英语（译林版三起 \+ Super Minds 第 2 版）\d+ 个点",
               f"已有人教版数学一年级上册 {sum(1 for t in topics if t['subject']=='数学')} 个点、统编版语文 {sum(1 for t in topics if t['subject']=='语文')} 个点、英语（译林版三起 + Super Minds 第 2 版）{sum(1 for t in topics if t['subject']=='英语')} 个点",
               s)
    open(rp, 'w', encoding='utf-8').write(s)
print('pages:', len(topics))

import sys, glob
from validate import BANNED, CONTENT_BANNED, has_content_banned
bad = []
for f in [rp] + glob.glob(os.path.join(ROOT, 'docs', '**', '*.md'), recursive=True):
    if not os.path.exists(f): continue
    s = open(f, encoding='utf-8').read()
    bad += [(os.path.relpath(f, ROOT), w) for w in BANNED if w in s]
    for w in CONTENT_BANNED:
        if has_content_banned(s, w):
            # 页脚/说明里的「不需要」等可放过：只拦「必须」「一定要」「落后」出现在非声明语境较难，页脚含「不需要家长批改」OK
            if w in ('必须', '一定要', '落后') and ('不需要' in s or '不是考试' in s):
                # still flag if 必须/一定要/落后 appear
                if w == '一定要' and '不一定要' in s and w not in re.sub(r'不一定要', '', s):
                    continue
                if has_content_banned(s, w):
                    bad.append((os.path.relpath(f, ROOT), w))
            else:
                bad.append((os.path.relpath(f, ROOT), w))
# de-dup
bad = sorted(set(bad))
# allow README 「不一定要」
bad = [(f, w) for f, w in bad if not (f == 'README.md' and w == '一定要')]
if bad:
    for f, w in bad: print(f'ERROR {f} 含禁用词「{w}」')
    sys.exit(1)
print('pages banned-word scan: OK')
