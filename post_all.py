#!/usr/bin/env python3
"""Generalized: records_file + labels_file -> final.{jsonl,json} with exact spans.
Usage: python post_all.py <records.jsonl> <labels.json> <out_prefix>
"""
import json, sys, collections
REC, LAB, OUTP = sys.argv[1], sys.argv[2], sys.argv[3]

recs={}
for line in open(REC):
    r=json.loads(line); recs[r["id"]]=r
labels=json.load(open(LAB))
by_id={}
for rec in labels.get("records",[]):
    by_id[rec["id"]]=rec.get("entities",[])

def occ(hay,needle):
    if not needle: return
    i=hay.find(needle)
    while i!=-1:
        yield i,i+len(needle); i=hay.find(needle,i+1)

out=[]; stats=collections.Counter(); span_total=0
for rid,r in recs.items():
    text=r["text"]; ents=by_id.get(rid,[])
    eo=[]
    for e in ents:
        ms=[m for m in e.get("mentions",[]) if m]
        first=min([text.find(m) for m in ms if text.find(m)!=-1] or [10**9])
        eo.append({"type":e.get("type"),"canonical":e.get("canonical",""),"mentions":ms,"first":first})
    eo.sort(key=lambda x:x["first"])
    tc=collections.Counter()
    for e in eo:
        if e["first"]>=10**9: continue
        tc[e["type"]]+=1; e["ph"]=f"[{e['type']}_{tc[e['type']]}]"
    cands=[]
    for e in eo:
        if "ph" not in e: continue
        for m in set(e["mentions"]):
            for s,en in occ(text,m): cands.append((s,en,e["type"],e["canonical"],e["ph"],m))
    cands.sort(key=lambda c:(-(c[1]-c[0]),c[0]))
    chosen=[]; used=[False]*len(text)
    for s,en,t,can,p,m in cands:
        if any(used[s:en]): continue
        for k in range(s,en): used[k]=True
        chosen.append({"start":s,"end":en,"type":t,"text":m,"placeholder":p,"entity":can})
    chosen.sort(key=lambda x:x["start"])
    buf=[]; cur=0
    for sp in chosen: buf.append(text[cur:sp["start"]]); buf.append(sp["placeholder"]); cur=sp["end"]
    buf.append(text[cur:]); redacted="".join(buf)
    for sp in chosen:
        assert text[sp["start"]:sp["end"]]==sp["text"], (rid,sp)
        stats[sp["type"]]+=1
    span_total+=len(chosen)
    out.append({"id":rid,"user":r.get("user",""),"question_type":r.get("question_type",""),
                "question":r["question"],"answer":r["answer"],
                "data_to_answer":text,"scrubber_data":redacted,"pii_spans":chosen})

with open(OUTP+".jsonl","w") as f:
    for o in out: f.write(json.dumps(o,ensure_ascii=False)+"\n")
json.dump(out, open(OUTP+".json","w"), ensure_ascii=False, indent=2)
print(f"records: {len(out)} | spans: {span_total} (avg {span_total/max(len(out),1):.1f}) | by type: {dict(stats)}")
print("all spans verified exact -> "+OUTP+".jsonl / .json")
