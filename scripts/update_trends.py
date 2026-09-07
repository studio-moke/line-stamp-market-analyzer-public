from __future__ import annotations
import json, os, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

ROOT=os.path.dirname(os.path.dirname(__file__))
OUT=os.path.join(ROOT,'data','trends.json')
URL='https://trends.google.co.jp/trending/rss?geo=JP'

def fetch_items():
    req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 stamp-moke-trend-bot/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        xml=r.read()
    root=ET.fromstring(xml)
    ns={'ht':'https://trends.google.com/trending/rss'}
    items=[]
    for item in root.findall('.//item'):
        title=(item.findtext('title') or '').strip()
        if not title: continue
        traffic=(item.findtext('ht:approx_traffic',default='',namespaces=ns) or '').strip()
        news=[]
        for n in item.findall('ht:news_item',ns):
            t=(n.findtext('ht:news_item_title',default='',namespaces=ns) or '').strip()
            if t: news.append(t)
        items.append({'title':title,'traffic':traffic,'news':news[:3]})
    return items[:30]

def load():
    if not os.path.exists(OUT): return {'source':'Google Trends RSS JP','snapshots':[]}
    try:
        with open(OUT,encoding='utf-8') as f: return json.load(f)
    except Exception:
        return {'source':'Google Trends RSS JP','snapshots':[]}

def main():
    data=load()
    now=datetime.now(timezone.utc)
    items=fetch_items()
    snaps=data.get('snapshots',[])
    snaps.append({'capturedAt':now.isoformat().replace('+00:00','Z'),'items':items})
    cutoff=now-timedelta(days=400)
    kept=[]
    for s in snaps:
        try:
            dt=datetime.fromisoformat(s['capturedAt'].replace('Z','+00:00'))
            if dt>=cutoff: kept.append(s)
        except Exception: pass
    data.update({'source':'Google Trends RSS JP','updatedAt':now.isoformat().replace('+00:00','Z'),'current':items,'snapshots':kept[-1800:]})
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    with open(OUT,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

if __name__=='__main__': main()
