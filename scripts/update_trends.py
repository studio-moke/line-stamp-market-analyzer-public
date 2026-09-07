from __future__ import annotations
import json, os, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

ROOT=os.path.dirname(os.path.dirname(__file__))
OUT=os.path.join(ROOT,'data','trends.json')
URL='https://trends.google.co.jp/trending/rss?geo=JP'
MAX_SNAPSHOTS=1800
RETENTION_DAYS=400


def _fetch_once():
    req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 stamp-moke-trend-bot/1.1'})
    with urllib.request.urlopen(req,timeout=20) as r:
        xml=r.read()
    root=ET.fromstring(xml)
    ns={'ht':'https://trends.google.com/trending/rss'}
    items=[]
    seen=set()
    for item in root.findall('.//item'):
        title=(item.findtext('title') or '').strip()
        key=title.casefold()
        if not title or key in seen:
            continue
        seen.add(key)
        traffic=(item.findtext('ht:approx_traffic',default='',namespaces=ns) or '').strip()
        news=[]
        for n in item.findall('ht:news_item',ns):
            t=(n.findtext('ht:news_item_title',default='',namespaces=ns) or '').strip()
            if t and t not in news:
                news.append(t)
        items.append({'title':title,'traffic':traffic,'news':news[:3]})
    return items[:30]


def fetch_items():
    last_error=None
    for attempt in range(2):
        try:
            return _fetch_once()
        except Exception as e:
            last_error=e
            if attempt == 0:
                time.sleep(5)
    raise last_error


def load():
    if not os.path.exists(OUT):
        return {'source':'Google Trends RSS JP','snapshots':[]}
    try:
        with open(OUT,encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {'source':'Google Trends RSS JP','snapshots':[]}


def fingerprint(items):
    return tuple((x.get('title','').casefold(),x.get('traffic','')) for x in items)


def main():
    data=load()
    now=datetime.now(timezone.utc)
    try:
        items=fetch_items()
    except Exception as e:
        print(f'Trend fetch failed after retry: {e}')
        # Keep the last good file untouched so a temporary upstream failure never erases history.
        return

    snaps=data.get('snapshots',[])
    # Do not store an identical consecutive snapshot. This keeps history compact and reduces commits.
    if not snaps or fingerprint(snaps[-1].get('items',[])) != fingerprint(items):
        snaps.append({'capturedAt':now.isoformat().replace('+00:00','Z'),'items':items})

    cutoff=now-timedelta(days=RETENTION_DAYS)
    kept=[]
    for s in snaps:
        try:
            dt=datetime.fromisoformat(s['capturedAt'].replace('Z','+00:00'))
            if dt>=cutoff:
                kept.append(s)
        except Exception:
            continue

    data.update({
        'source':'Google Trends RSS JP',
        'updatedAt':now.isoformat().replace('+00:00','Z'),
        'retentionDays':RETENTION_DAYS,
        'current':items,
        'snapshots':kept[-MAX_SNAPSHOTS:]
    })
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    with open(OUT,'w',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2)


if __name__=='__main__':
    main()
