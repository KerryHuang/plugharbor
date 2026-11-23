# 用法：python3 scan.py（讀本機 ~/.claude/projects，跳過 -private-tmp 測試沙箱）。量 M-20261109-02～05。
import json,glob,os,re,collections,sys
root=os.path.expanduser('~/.claude/projects')
BASE=('2026-10-26','2026-11-09T04:00')   # UTC; commits ~12:00 +08
PER=('2026-11-09T04:21','2026-11-23T23:59')
WS={'workspace:debugging','workspace:agent-orchestration','workspace:review'}
SP={'workspace:debugging':'superpowers:systematic-debugging','workspace:review':'superpowers:requesting-code-review','workspace:agent-orchestration':'superpowers:dispatching-parallel-agents'}
sess={}
for f in glob.glob(root+'/*/*.jsonl'):
    if '-private-tmp' in f: continue   # e2e 測試沙箱
    s=dict(skills=[],agents=[],user=[],ts=None,text=[],proj=os.path.basename(os.path.dirname(f)))
    try:
        for line in open(f,encoding='utf-8',errors='ignore'):
            try:d=json.loads(line)
            except:continue
            ts=d.get('timestamp');
            if ts and not s['ts']: s['ts']=ts
            m=d.get('message') or {}
            c=m.get('content')
            if d.get('type')=='user' and not d.get('isSidechain'):
                if isinstance(c,str): s['user'].append(c[:400])
                elif isinstance(c,list):
                    for b in c:
                        if b.get('type')=='text': s['user'].append(b['text'][:400])
            if d.get('type')=='assistant' and isinstance(c,list):
                for b in c:
                    if b.get('type')=='tool_use':
                        n=b.get('name');i=b.get('input',{})
                        if n=='Skill': s['skills'].append((ts,i.get('skill')))
                        if n in('Agent','Task'): s['agents'].append((ts,i.get('subagent_type'),i.get('model')))
                    if b.get('type')=='text': s['text'].append(b['text'][:300])
    except Exception as e: continue
    sess[f]=s
def inr(ts,r): return ts and r[0]<=ts<=r[1]
# M-04
tot=withm=0;miss=collections.Counter()
for s in sess.values():
    for ts,t,mo in s['agents']:
        if inr(ts,PER):
            tot+=1
            if mo: withm+=1
            else: miss[t or '(none)']+=1
print('M04 Agent calls',tot,'with model',withm, f'{withm/tot:.1%}' if tot else '', 'missing by type',dict(miss))
# M-03
for name,r in (('base',BASE),('period',PER)):
    c=collections.Counter(sk for s in sess.values() for ts,sk in s['skills'] if inr(ts,r) and sk in WS)
    print('M03',name,dict(c))
dup=[]
for f,s in sess.items():
    names={sk for ts,sk in s['skills'] if inr(ts,PER)}
    for w,p in SP.items():
        if w in names and p in names: dup.append((os.path.basename(f)[:8],w))
print('M03 same-session dup',dup)
# M-02
impl_intent=re.compile(r'照(規格|計畫|spec|plan)|開始實作|依(規格|計畫)實作|implement (the|this) (spec|plan)|執行計畫')
rows=[]
for f,s in sess.items():
    sk=[x for ts,x in s['skills'] if inr(ts,PER)]
    if not sk and not (s['ts'] and inr(s['ts'],PER)): continue
    intent=any(impl_intent.search(u) for u in s['user'] if not u.startswith('<') ) or any(x in('superpowers:executing-plans','superpowers:subagent-driven-development') for x in sk)
    if intent:
        rows.append((os.path.basename(f)[:8],s['proj'][-30:],'lifecycle:implement' in sk,[x for x in sk if x and ('implement' in x or 'executing' in x or 'subagent-driven' in x)][:4]))
hit=sum(r[2] for r in rows)
print('M02 intent sessions',len(rows),'with lifecycle:implement',hit)
for r in rows: print('  ',r)
# M-05
for f,s in sess.items():
    sk=[x for ts,x in s['skills'] if inr(ts,PER)]
    if any(x and 'ticket-create' in x for x in sk) and 'lifecycle:implement' in sk:
        bug=any(re.search(r'\bBug\b|bug 票|錯誤票',u) for u in s['user'])
        gate=[t for t in s['text'] if re.search(r'規格閘門|沒有規格|缺規格|spec gate',t)]
        print('M05',os.path.basename(f)[:8],s['proj'][-30:],'bug-ish',bug,'gate-msgs',len(gate),'sysdebug','superpowers:systematic-debugging' in sk)
