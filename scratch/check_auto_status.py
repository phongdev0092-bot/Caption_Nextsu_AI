import urllib.request, json

def get_json(url):
    try:
        r = urllib.request.urlopen(url, timeout=5)
        return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'error': str(e)}

print('=== AUTO MODES ===')
print(json.dumps(get_json('http://localhost:5001/api/auto-modes'), indent=2))

print('=== AUTO OVERVIEW ===')
ov = get_json('http://localhost:5001/api/auto/overview')
print('Last scan:', ov.get('last_scan'))
print('Running:', ov.get('running'))
print('Tabs:')
for k, v in ov.get('tabs', {}).items():
    p = v.get('pending')
    tot = v.get('total')
    a = v.get('auto')
    shds = v.get('shds', [])[:5]
    print(f'  {k}: pending={p}, total={tot}, auto={a}, shds={shds}')

print('=== RECENT LOGS ===')
for l in ov.get('logs', [])[:15]:
    t = l.get('time', '')
    lvl = l.get('level', '')
    txt = l.get('text', '').encode('ascii', errors='replace').decode()
    print(f'[{t}] [{lvl.upper()}] {txt}')
