# SPDX-License-Identifier: MIT
# Copyright (c) 2026 【公司全称待补】
"""公共读取函数（仅用标准库）。"""
import json, glob, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('YXZ_DATA', os.path.join(ROOT, 'data'))
TERM_ORDER = {'上': 0, '全年': 0, '下': 1}

def load():
    topics, deps, files = [], [], {}
    for f in sorted(glob.glob(os.path.join(DATA, '*', '*', 'topics.json'))):
        items = json.load(open(f, encoding='utf-8'))
        files[f] = items
        topics += items
    for f in sorted(glob.glob(os.path.join(DATA, '*', '*', 'dependencies.json'))):
        deps += json.load(open(f, encoding='utf-8'))
    chains = json.load(open(os.path.join(DATA, 'chains.json'), encoding='utf-8'))
    return topics, deps, chains, files

def position(t):
    """知识点在教材里最早出现的位置：(年级, 学期, 单元序)。"""
    return min((r['grade'], TERM_ORDER.get(r['term'], 0), r.get('unit_order', 0)) for r in t['textbook_refs'])

def required_depth(topics, deps):
    """沿“必需”前置边的最长深度（根=0）。"""
    req = {}
    for d in deps:
        if d['strength'] == '必需':
            req.setdefault(d['to'], []).append(d['from'])
    memo = {}
    def depth(i, stack=()):
        if i in memo: return memo[i]
        if i in stack: return 0  # 有环时由环检测报错
        v = 0 if i not in req else 1 + max(depth(p, stack + (i,)) for p in req[i])
        memo[i] = v
        return v
    return {t['id']: depth(t['id']) for t in topics}

def level_from_depth(d):
    """难度定档规则（见 CONTRIBUTING/讲法规范.md）：必需前置深度 0→D1，1→D2，2–3→D3，4–6→D4，≥7→D5。"""
    if d == 0: return 1
    if d == 1: return 2
    if d <= 3: return 3
    if d <= 6: return 4
    return 5

def topo_order(topics, deps):
    """学习顺序：拓扑排序；同一时刻可学的，按 难度→教材位置→主题链步号 排。"""
    byid = {t['id']: t for t in topics}
    indeg = {i: 0 for i in byid}
    out = {i: [] for i in byid}
    for d in deps:
        if d['from'] in byid and d['to'] in byid:
            indeg[d['to']] += 1; out[d['from']].append(d['to'])
    key = lambda i: (byid[i]['difficulty_level'], position(byid[i]), byid[i]['topic_chain']['step'], i)
    ready = sorted([i for i, n in indeg.items() if n == 0], key=key)
    order = []
    while ready:
        i = ready.pop(0); order.append(i)
        for j in out[i]:
            indeg[j] -= 1
            if indeg[j] == 0: ready.append(j)
        ready.sort(key=key)
    return order
