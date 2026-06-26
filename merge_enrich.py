#!/usr/bin/env python3
"""Union base labels with enrichment labels per record, clustering entities by shared
mentions so one real entity stays one entity (one placeholder). Applies an FP blocklist.
Usage: python merge_enrich.py <base_labels.json> <enrich_output.json> <out_labels.json>
enrich_output.json is the workflow result file (has {"result":{"records":[...]}} or {"records":[...]}).
"""
import json, sys, collections

BASE, ENR, OUT = sys.argv[1], sys.argv[2], sys.argv[3]

# clear, non-PII ORG labels the audit flagged (generic notification-category descriptors)
FP_BLOCK = {"time sequence", "time order"}

def load_records(path):
    d = json.load(open(path))
    if "result" in d: d = d["result"]
    return {r["id"]: r.get("entities", []) for r in d["records"]}

base = load_records(BASE)
enr  = load_records(ENR)

all_ids = set(base) | set(enr)
out_records = []
for rid in all_ids:
    ents = list(base.get(rid, [])) + list(enr.get(rid, []))
    # union-find clustering by shared (case-insensitive) mention
    parent = list(range(len(ents)))
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b): parent[find(a)]=find(b)
    mention_owner = {}
    for i,e in enumerate(ents):
        for m in e.get("mentions",[]):
            k=m.strip().lower()
            if not k: continue
            if k in mention_owner: union(i, mention_owner[k])
            else: mention_owner[k]=i
    clusters = collections.defaultdict(list)
    for i in range(len(ents)): clusters[find(i)].append(i)
    merged = []
    for idxs in clusters.values():
        members=[ents[i] for i in idxs]
        # type: majority vote (stable)
        tcount=collections.Counter(m["type"] for m in members)
        typ=tcount.most_common(1)[0][0]
        # mentions: union, drop blocklisted
        mset=[]
        seen=set()
        for m in members:
            for s in m.get("mentions",[]):
                if not s: continue
                if s.strip().lower() in FP_BLOCK: continue
                if s not in seen: seen.add(s); mset.append(s)
        if not mset: continue
        canon=max((m.get("canonical","") for m in members), key=len) or mset[0]
        merged.append({"type":typ,"canonical":canon,"mentions":mset})
    out_records.append({"id":rid,"entities":merged})

json.dump({"records":out_records}, open(OUT,"w"), ensure_ascii=False)
print(f"merged labels for {len(out_records)} records -> {OUT}")
