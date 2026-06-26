#!/usr/bin/env python3
"""Deterministic precision cleanup of enrichment-injected false positives.
Drops, at the mention level: bare generic role words (PERSON), generic descriptor/
placeholder ORGs, certification names, and bracket-markup wrappers. Keeps title+surname
(Mr. Feng), real brands, and address components.
Usage: python precision_clean.py <in_labels.json> <out_labels.json>
"""
import json, sys, re

INP, OUT = sys.argv[1], sys.argv[2]

ROLE_WORDS = {  # bare relationship/role words -> not PII on their own
 "father","mother","mom","mum","mommy","dad","daddy","papa","mama","wife","husband",
 "spouse","brother","sister","son","daughter","grandfather","grandmother","grandpa",
 "grandma","granny","parents","parent","child","children","kid","kids","boss","manager",
 "broker","driver","colleague","colleagues","friend","friends","neighbor","neighbour",
 "teacher","doctor","nurse","agent","client","customer","landlord","tenant","uncle",
 "aunt","auntie","cousin","nephew","niece","mother-in-law","father-in-law","in-law",
 "him","her","me","myself","mum","dad",
}
PRONOUNS = {  # pronouns wrongly tagged PERSON -> not identifying PII
 "i","he","she","him","her","his","hers","me","my","mine","we","us","our","ours",
 "you","your","yours","they","them","their","theirs","it","its","myself","himself",
 "herself","themselves","this","that","who",
}
GENERIC_ORG = {
 "browser","health","obtain","time sequence","time order","platform a","platform b",
 "electronic data capture system","medical english learning platform",
 "b medical english platform","b platform medical english course","edc",
 "cfa","cfa level i","cfa level ii","cfa level iii","app","the app","apps","system",
 "platform","the platform","website","email","note","calendar","photo","push","sms",
}
MARKUP = re.compile(r'[\[\]【】]')   # source-tag/bracket markup wrappers
PUSH_TAG = re.compile(r'^(push|sms|note|calendar|photo|call)\s*/', re.I)  # channel-tag markup like "Push/WeChat"
# generic feature/descriptor ORG labels (e.g. "Health App", "Pressure Monitoring")
FEATURE_ORG = re.compile(r'(?i)^(health|pressure|sleep|heart[\s-]?rate|step|steps|activity|'
                         r'exercise|sport|sports|fitness|weather|blood\s?\w*|workout|run(ning)?|'
                         r'calorie|nutrition|diet|water|mood|stress)\s+'
                         r'(app|monitoring|monitor|tracking|tracker|data|reminder|record|management|assistant)s?$')

def keep_mention(typ, m):
    s = m.strip()
    low = s.lower()
    if MARKUP.search(s): return False
    if PUSH_TAG.search(s): return False                  # drop "Push/X" channel markup
    if typ == "PERSON" and low in ROLE_WORDS: return False
    if typ == "PERSON" and low in PRONOUNS: return False
    if typ == "ORG" and low in GENERIC_ORG: return False
    if typ == "ORG" and FEATURE_ORG.match(s): return False
    return True

d = json.load(open(INP))
if "result" in d: d = d["result"]
out=[]; dropped=0; ent_dropped=0
for r in d["records"]:
    ents=[]
    for e in r.get("entities",[]):
        kept=[m for m in e.get("mentions",[]) if keep_mention(e["type"], m)]
        dropped += len(e.get("mentions",[]))-len(kept)
        if kept: ents.append({**e, "mentions":kept})
        else: ent_dropped+=1
    out.append({"id":r["id"],"entities":ents})
json.dump({"records":out}, open(OUT,"w"), ensure_ascii=False)
print(f"cleaned {len(out)} records | mentions dropped: {dropped} | entities emptied: {ent_dropped} -> {OUT}")
