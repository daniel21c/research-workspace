import sys, json, hashlib
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
B=Path(__file__).parent
out={}
for name in ['owned','inputs']:
    old=json.loads((B/f'before_{name}.json').read_text(encoding='utf-8'))
    now=[]; changed=[]
    for row in old:
        p=Path(row['path'])
        if not p.exists():
            changed.append({'path':str(p),'status':'missing'}); continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            while z:=f.read(4*1024*1024): h.update(z)
        n={'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
        now.append(n)
        if n['sha256']!=row['sha256'] or n['bytes']!=row['bytes']: changed.append(n)
    (B/f'after_{name}.json').write_text(json.dumps(now,ensure_ascii=False,indent=2),encoding='utf-8')
    out[name]={'count_before':len(old),'count_after':len(now),'changed':changed}
p=Path(r'C:\Users\cyion\.claude\projects\C--Users-cyion\699e0cef-003f-4543-bb89-3764cfec73e2.jsonl')
out['session']={'path':str(p),'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(B/'final_hash_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
