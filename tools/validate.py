from __future__ import annotations
import json,re,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SITE=ROOT/'_site'
catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
topics=json.loads((ROOT/'content/topics.json').read_text(encoding='utf-8'))
tutorials=json.loads((ROOT/'content/tutorials.json').read_text(encoding='utf-8'))
screens=json.loads((ROOT/'data/screenshots.json').read_text(encoding='utf-8'))
errors=[]
all_items=[*catalog['nodes'],*catalog['peripherals'],*catalog['boards'],*topics]
ids=[x.get('helpId') for x in all_items]
if any(not x for x in ids):errors.append('Every registered item must have helpId')
duplicates=sorted({x for x in ids if ids.count(x)>1})
if duplicates:errors.append('Duplicate helpId: '+', '.join(duplicates))
if len(catalog['nodes'])<100:errors.append('Logic catalog unexpectedly incomplete')
if len(catalog['peripherals'])<100:errors.append('Peripheral catalog unexpectedly incomplete')
if len(catalog['boards'])<10:errors.append('Board catalog unexpectedly incomplete')
if len(tutorials)!=18:errors.append('Expected 18 initial tutorials')
for locale in catalog['locales']:
    if not (SITE/locale/'index.html').exists():errors.append(f'Missing locale home: {locale}')
    for help_id in ids:
        if not (SITE/locale/help_id.replace('.', '/')/'index.html').exists():errors.append(f'Missing route: {locale}/{help_id}')
for page in SITE.rglob('*.html'):
    text=page.read_text(encoding='utf-8')
    for target in re.findall(r'href="(/elma-iot-docs/[^"#?]+)"',text):
        rel=target.removeprefix('/elma-iot-docs/').strip('/')
        candidate=SITE/rel
        if candidate.is_dir():candidate=candidate/'index.html'
        if not candidate.exists():errors.append(f'Broken internal link in {page.relative_to(SITE)}: {target}')
required={'device-setup-wizard','board-selection','peripheral-selection','graphic-designer','vertical-logics-constructor','blueprint-logics-canvas','instrument-panel','compile-flash','usb','ota','serial-monitor'}
present={x.get('feature') for x in screens}
missing=sorted(required-present)
if missing:errors.append('Missing current Android screenshots: '+', '.join(missing))
for item in screens:
    path=ROOT/item.get('path','')
    if not path.is_file():errors.append('Missing screenshot file: '+str(path))
    for field in ('platform','applicationVersion','feature','helpId','capturedAt'):
        if not item.get(field):errors.append(f'Screenshot missing {field}: {item}')
for path in ROOT.rglob('*'):
    if not path.is_file() or '.git' in path.parts or path.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.gif'}:continue
    if path.stat().st_size>3_000_000:errors.append(f'Unexpected large public file: {path.relative_to(ROOT)}')
    text=path.read_text(encoding='utf-8',errors='ignore')
    patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)password\s*[:=]\s*["\'][^"\']+["\']',r'gh[pousr]_[A-Za-z0-9_]{20,}',r'AIza[0-9A-Za-z_-]{30,}']
    if any(re.search(pattern,text) for pattern in patterns):errors.append(f'Potential secret in {path.relative_to(ROOT)}')
if errors:
    print('\n'.join('ERROR: '+x for x in errors[:100]));sys.exit(1)
print(f'Validated {len(catalog["nodes"])} nodes, {len(catalog["peripherals"])} peripherals, {len(catalog["boards"])} boards, {len(tutorials)} tutorials, {len(screens)} screenshots, {len(catalog["locales"])} locale routes')
