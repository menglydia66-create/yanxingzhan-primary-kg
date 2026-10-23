#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 上海语星宝教育科技有限公司
"""自测：故意造坏数据，校验器必须全部拦下。"""
import json, os, shutil, subprocess, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tmp = tempfile.mkdtemp()
shutil.copytree(os.path.join(ROOT, 'data'), os.path.join(tmp, 'data'))
d = os.path.join(tmp, 'data', 'math', 'pep2024')
topics = json.load(open(f'{d}/topics.json')); deps = json.load(open(f'{d}/dependencies.json'))
dup = json.loads(json.dumps(topics[0])); dup['id'] = 'MA-1A-901'; dup['name'] = topics[0]['name']
bad = json.loads(json.dumps(topics[1])); bad['id'] = 'MA-1A-902'; bad['name'] = '测试禁用词'; bad['essence'] = '名师教你提分，完整版见公众号'; del bad['explain']['hook']
# 缺诊断卡
bad2 = json.loads(json.dumps(topics[2])); bad2['id'] = 'MA-1A-903'; bad2['name'] = '缺诊断卡测试'; del bad2['oral_diagnosis']
# 内容禁词「必须」
bad3 = json.loads(json.dumps(topics[3])); bad3['id'] = 'MA-1A-904'; bad3['name'] = '内容禁词测试'; bad3['explain']['mistake']['why'] = '你必须这样算'
topics += [dup, bad, bad2, bad3]
deps += [{"from": "MA-1A-012", "to": "MA-1A-001", "strength": "必需", "reason": "倒序且成环"}]
# 传递冗余：若 001→004→005 存在，再加 001→005
if not any(d['from']=='MA-1A-001' and d['to']=='MA-1A-005' for d in deps):
    deps += [{"from": "MA-1A-001", "to": "MA-1A-005", "strength": "必需", "reason": "故意冗余"}]
json.dump(topics, open(f'{d}/topics.json', 'w'), ensure_ascii=False); json.dump(deps, open(f'{d}/dependencies.json', 'w'), ensure_ascii=False)
r = subprocess.run([sys.executable, os.path.join(ROOT, 'scripts', 'validate.py')], env={**os.environ, 'YXZ_DATA': os.path.join(tmp, 'data')}, capture_output=True, text=True)
out = r.stdout
need = ['疑似重复知识点', '含禁用词「名师」', '含禁用词「公众号」', '含禁用词「完整版见」', '讲法缺 hook', '前置倒序', '有环',
        '缺 oral_diagnosis', '讲解/诊断含禁词「必须」', '传递冗余必需边']
miss = [n for n in need if n not in out]
shutil.rmtree(tmp)
if r.returncode == 1 and not miss:
    print('selftest OK：坏数据全部被拦下'); sys.exit(0)
print('selftest FAIL，未拦下：', miss); print(out); sys.exit(1)
