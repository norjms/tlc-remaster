"""Convert a ComfyUI UI workflow to API format using /object_info, with overrides, and run it.
usage: wf2api.py <workflow.json> <overrides.json>   overrides: {"<node id>": {"input": value}}"""
import json, sys, os, time, urllib.request
API = 'http://127.0.0.1:8188'
D = r'D:\AI\comfyui\ComfyUI\custom_nodes\ComfyUI-Trellis2\example_workflows'
CONN = None

def get(p): return json.loads(urllib.request.urlopen(API + p).read())
def post(p, o):
    r = urllib.request.Request(API + p, json.dumps(o).encode(), {'Content-Type': 'application/json'})
    try: return json.loads(urllib.request.urlopen(r).read())
    except urllib.error.HTTPError as e: print(e.read().decode()); raise

def convert(w):
    info = get('/object_info')
    links = {l[0]: l for l in w['links']}
    prims = {}
    for n in w['nodes']:
        if n['type'].startswith('Primitive'): prims[n['id']] = n['widgets_values'][0]
    api = {}
    for n in w['nodes']:
        t = n['type']
        if t.startswith('Primitive') or t in ('Note', 'MarkdownNote', 'Preview3D', 'PreviewImage', 'Reroute'): continue
        oi = info[t]['input']; spec = list(oi.get('required', {}).items()) + list(oi.get('optional', {}).items())
        linked = {}
        for i in n.get('inputs', []):
            if i.get('link') is not None:
                l = links[i['link']]
                linked[i['name']] = prims[l[1]] if l[1] in prims else [str(l[1]), l[2]]
        wv = list(n.get('widgets_values') or []); k = 0; inputs = {}
        for name, s in spec:
            typ = s[0]; opts = s[1] if len(s) > 1 and isinstance(s[1], dict) else {}
            is_widget = isinstance(typ, list) or typ in ('INT', 'FLOAT', 'STRING', 'BOOLEAN', 'COMBO')
            if is_widget and k < len(wv):
                inputs[name] = wv[k]; k += 1
                if typ == 'INT' and (opts.get('control_after_generate') or name in ('seed', 'noise_seed')): k += 1
            if name in linked: inputs[name] = linked[name]
        api[str(n['id'])] = {'class_type': t, 'inputs': inputs}
    return api

if __name__ == '__main__':
    w = json.load(open(os.path.join(D, sys.argv[1]), encoding='utf-8'))
    api = convert(w)
    ov = json.load(open(sys.argv[2])) if len(sys.argv) > 2 else {}
    for nid, d in ov.items(): api[nid]['inputs'].update(d)
    for nid, n in api.items(): print(nid, n['class_type'], {k: v for k, v in n['inputs'].items()})
    if '--dry' in sys.argv: sys.exit()
    pid = post('/prompt', {'prompt': api})['prompt_id']; t0 = time.time()
    while True:
        time.sleep(5)
        h = get(f'/history/{pid}')
        if pid in h:
            st = h[pid].get('status', {}); print('status', st.get('status_str'), int(time.time() - t0), 's')
            for m in st.get('messages', []):
                if m[0] == 'execution_error': print(json.dumps(m[1])[:3000])
            print(json.dumps(h[pid]['outputs'])[:2000]); break
