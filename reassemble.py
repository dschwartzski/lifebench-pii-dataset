#!/usr/bin/env python3
"""Re-assemble records with junk faceRecognition prompts stripped. Same text otherwise.
Writes records_clean.jsonl. Labels (mentions) recompute offsets via post_all on this.
"""
import json,collections,re
USERS=["fenghaoran","leimingxuan","lumingqiang","maxiulan","songyajing","sunyuwei","yemingxuan","yinhao","yuxiaowei","yuxiaowen"]
types=["sms","call","agent_chat","note","calendar","photo","push"]
JUNK=re.compile(r'translate|Translation requirements|Semantic accuracy|Chinese text|原文|adhering to the following',re.I)
def loc(v):
    if isinstance(v,dict):
        return ", ".join(str(x) for x in [v.get('poi'),v.get('streetNumber'),v.get('streetName'),v.get('district'),v.get('city'),v.get('province')] if x)
    return str(v or "")
def clean_faces(faces):
    s=", ".join(faces) if isinstance(faces,list) else str(faces or "")
    if not s: return ""
    if JUNK.search(s) or len(s)>160: return ""   # drop leaked-prompt junk, keep short name lists
    return s
def fmt(t,r):
    g=lambda k: r.get(k,"") or ""
    if t=="sms":   return f"[SMS] {g('contactName')}: {g('message_content')}"
    if t=="call":  return f"[Call {g('direction')}] {g('contactName')} ({g('phoneNumber')}) — {g('call_result')}"
    if t=="agent_chat":
        out=[]
        for turn in (g('conversation') or {}).values():
            for role in ("user","assistant"):
                if isinstance(turn.get(role),dict): out.append(f"{role.capitalize()}: {turn[role].get('content','')}")
        return "[Assistant chat]\n"+"\n".join(out)
    if t=="note":  return f"[Note] {g('title')}\n{g('content')}"
    if t=="calendar": return f"[Calendar] {g('title')}\n{g('description')}"
    if t=="photo":
        faces=clean_faces(g('faceRecognition')); extra=loc(g('location'))
        tail=(f" (at {extra}"+(f"; with {faces}" if faces else "")+")") if (extra or faces) else ""
        return f"[Photo] {g('caption') or g('title')}{tail}"
    if t=="push":  return f"[Push/{g('source')}] {g('title')}: {g('content')}"
    return json.dumps(r,ensure_ascii=False)
def pv(s):
    out={s}
    if re.fullmatch(r"\+?\d{11,13}",s): out|={s.lstrip("+"),s[-11:],"+86"+s[-11:]}
    return out

allrecs=[]
for u in USERS:
    D=f"all/{u}"
    def Lf(f): return json.load(open(f"{D}/{f}.json"))
    qa=Lf("QA_clean"); persona=Lf("persona"); contacts=Lf("contact")
    data={t:Lf(t) for t in types}
    idx={t:collections.defaultdict(list) for t in types}
    for t in types:
        for r in data[t]: idx[t][str(r.get("phone_id"))].append(r)
    cat=set([persona.get("name","")])
    for a in (persona.get("home_address",{}),persona.get("workplace",{}),persona.get("birth_place",{})):
        if isinstance(a,dict): cat|={str(v) for v in a.values()}
    cat|={persona.get("occupation",""),persona.get("job","")}
    for c in contacts:
        for f in ("name","nickname","phoneNumber","personalEmail","workEmail","idNumber"):
            if c.get(f): cat.add(str(c[f]))
    cat={x for c in cat if c and len(str(c))>=3 for x in pv(str(c))}
    for i,q in enumerate(qa):
        parts=[]
        for e in q.get("evidence",[]):
            t,pid=e.get("type"),str(e.get("id"))
            if t not in idx: continue
            for r in idx[t].get(pid,[]): parts.append(fmt(t,r))
        text="\n\n".join(parts).strip()
        if not text: continue
        seed=sorted({c for c in cat if c in text},key=len,reverse=True)
        allrecs.append({"id":f"{u}_{i:04d}","user":u,"question":q.get("question",""),
                        "answer":q.get("answer",""),"question_type":q.get("question_type",""),
                        "text":text,"seed":seed})
with open("records_clean.jsonl","w") as f:
    for r in allrecs: f.write(json.dumps(r,ensure_ascii=False)+"\n")
print(f"reassembled {len(allrecs)} records (junk faceRecognition stripped)")
