from __future__ import annotations
import html,json,re,sys
from pathlib import Path
from translate_content import TextCollector

ROOT=Path(__file__).resolve().parents[1]; SITE=ROOT/'_site'
catalog=json.loads((ROOT/'data/catalog.json').read_text(encoding='utf-8'))
topics=json.loads((ROOT/'content/topics.json').read_text(encoding='utf-8'))
tutorials=json.loads((ROOT/'content/tutorials.json').read_text(encoding='utf-8'))
guides=[]
for guide_path in sorted((ROOT/'content/guides').glob('*.json')):
    value=json.loads(guide_path.read_text(encoding='utf-8'));guides.extend(value if isinstance(value,list) else [value])
screens=json.loads((ROOT/'data/screenshots.json').read_text(encoding='utf-8'))
errors=[]
all_items=[*catalog['nodes'],*catalog['peripherals'],*catalog['boards'],*topics,*guides]
ids=[x.get('helpId') for x in all_items]
if any(not x for x in ids):errors.append('Every registered item must have helpId')
duplicates=sorted({x for x in ids if ids.count(x)>1})
if duplicates:errors.append('Duplicate helpId: '+', '.join(duplicates))
if len(catalog['nodes'])<100:errors.append('Logic catalog unexpectedly incomplete')
if len(catalog['peripherals'])<100:errors.append('Peripheral catalog unexpectedly incomplete')
if len(catalog['boards'])<10:errors.append('Board catalog unexpectedly incomplete')
if len(tutorials)!=18:errors.append('Expected 18 initial tutorials')
if len(guides)<15:errors.append('Comprehensive learning guide set is incomplete')
for guide in guides:
    body=''.join(guide.get('body',[])) if isinstance(guide.get('body'),list) else str(guide.get('body',''))
    if len(body)<500:errors.append('Guide is too short to be useful: '+str(guide.get('helpId')))
placeholder='Open contextual Documentation from the feature whenever possible.'
if placeholder in (ROOT/'tools/build_site.py').read_text(encoding='utf-8'):errors.append('Generic placeholder Help prose is still present in the site generator')
tutorial_ids=['tutorials.'+x.get('id','') for x in tutorials]
if len(set(tutorial_ids))!=len(tutorial_ids):errors.append('Duplicate tutorial id')
for tutorial in tutorials:
    if not tutorial.get('title') or not tutorial.get('why'):errors.append('Tutorial requires title and purpose: '+str(tutorial.get('id')))
    if len(tutorial.get('steps',[]))<3:errors.append('Tutorial requires at least three actionable steps: '+str(tutorial.get('id')))
for locale in catalog['locales']:
    if not (SITE/locale/'index.html').exists():errors.append(f'Missing locale home: {locale}')
    for help_id in ids:
        page=SITE/locale/help_id.replace('.', '/')/'index.html'
        if not page.exists():errors.append(f'Missing route: {locale}/{help_id}')
        else:
            rendered=page.read_text(encoding='utf-8')
            if placeholder in rendered:errors.append(f'Placeholder Help body: {locale}/{help_id}')
            if 'class="screenshot-gallery"' not in rendered:errors.append(f'Page has no current application visual: {locale}/{help_id}')
            if locale!='en' and f'/assets/screenshots/android/{locale}/' not in rendered:errors.append(f'Page has no screenshot in selected language: {locale}/{help_id}')
            if locale!='en' and 'class="fallback"' in rendered:errors.append(f'Untranslated fallback banner remains: {locale}/{help_id}')
            if locale=='en':
                article=re.search(r'<article>(.*?)</article>',rendered,re.S)
                visible=' '.join(re.sub(r'<[^>]+>',' ',html.unescape(article.group(1) if article else '')).split())
                if len(visible)<700:errors.append(f'Help page is too short to be detailed: {help_id} ({len(visible)} characters)')
                if rendered.count('<h2>')<3:errors.append(f'Help page lacks a practical section structure: {help_id}')
    tutorial_index=(SITE/locale/'tutorials'/'index.html')
    if tutorial_index.exists():
        tutorial_html=tutorial_index.read_text(encoding='utf-8')
        if 'class="doc-tree"' not in tutorial_html:errors.append(f'Missing documentation tree: {locale}/tutorials')
        for help_id in tutorial_ids:
            if f'/{locale}/{help_id.replace(".", "/")}/' not in tutorial_html:errors.append(f'Tutorial index does not link {locale}/{help_id}')
    for help_id in tutorial_ids:
        page=SITE/locale/help_id.replace('.', '/')/'index.html'
        if not page.exists():errors.append(f'Missing tutorial route: {locale}/{help_id}')
        else:
            tutorial_page=page.read_text(encoding='utf-8')
            if 'class="tutorial-steps"' not in tutorial_page:errors.append(f'Tutorial has no rendered steps: {locale}/{help_id}')
            if 'class="doc-tree"' not in tutorial_page:errors.append(f'Tutorial has no navigation tree: {locale}/{help_id}')
            if 'class="screenshot-gallery"' not in tutorial_page:errors.append(f'Tutorial has no screenshot gallery: {locale}/{help_id}')
for peripheral in catalog['peripherals']:
    page=SITE/'en'/peripheral['helpId'].replace('.', '/')/'index.html'
    if page.exists():
        peripheral_html=page.read_text(encoding='utf-8')
        for required_text in ('Runtime support:', 'Minimal configuration', 'Configuration fields', 'Runtime behavior and Logics', 'Common mistakes'):
            if required_text not in peripheral_html:errors.append(f'Peripheral reference missing {required_text}: {peripheral["helpId"]}')
internal_targets={}
for page in SITE.rglob('*.html'):
    text=page.read_text(encoding='utf-8')
    for target in re.findall(r'href="(/elma-iot-docs/[^"#?]+)"',text):
        internal_targets.setdefault(target,page.relative_to(SITE))
for target,source in internal_targets.items():
    rel=target.removeprefix('/elma-iot-docs/').strip('/')
    candidate=SITE/rel
    if candidate.is_dir():candidate=candidate/'index.html'
    if not candidate.exists():errors.append(f'Broken internal link in {source}: {target}')
required={'device-setup-wizard','board-selection','peripheral-selection','graphic-designer','vertical-logics-constructor','blueprint-logics-canvas','instrument-panel','compile-flash','usb','ota','serial-monitor'}
for locale in catalog['locales']:
    present={x.get('feature') for x in screens if x.get('locale','en')==locale}
    missing=sorted(required-present)
    if missing:errors.append(f'Missing current Android screenshots for {locale}: '+', '.join(missing))
for item in screens:
    path=ROOT/item.get('path','')
    if not path.is_file():errors.append('Missing screenshot file: '+str(path))
    for field in ('platform','applicationVersion','feature','helpId','capturedAt'):
        if not item.get(field):errors.append(f'Screenshot missing {field}: {item}')
    if not item.get('locale'):errors.append(f'Screenshot missing locale: {item}')
collector=TextCollector()
for path in (SITE/'en').rglob('*.html'):collector.feed(path.read_text(encoding='utf-8'))
for locale in catalog['locales']:
    if locale=='en':continue
    translation_path=ROOT/'content/locales'/(locale+'.json')
    if not translation_path.is_file():errors.append(f'Missing documentation translation: {locale}');continue
    mapping=json.loads(translation_path.read_text(encoding='utf-8'))
    missing=collector.values-set(mapping)
    if missing:errors.append(f'{locale} translation is missing {len(missing)} source strings')
    markers=[value for value in mapping.values() if re.search(r'\[\[ELMA\d+\]\]',str(value))]
    if markers:errors.append(f'{locale} translation contains batch markers')
    translated=sum(1 for source,value in mapping.items() if source.strip()!=str(value).strip())
    if translated<max(1,int(len(mapping)*.75)):errors.append(f'{locale} translation appears mostly untranslated ({translated}/{len(mapping)})')
for path in ROOT.rglob('*'):
    if not path.is_file() or '.git' in path.parts or path.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.gif'}:continue
    if path.stat().st_size>3_000_000:errors.append(f'Unexpected large public file: {path.relative_to(ROOT)}')
    text=path.read_text(encoding='utf-8',errors='ignore')
    patterns=[r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',r'(?i)password\s*[:=]\s*["\'][^"\']+["\']',r'gh[pousr]_[A-Za-z0-9_]{20,}',r'AIza[0-9A-Za-z_-]{30,}']
    if any(re.search(pattern,text) for pattern in patterns):errors.append(f'Potential secret in {path.relative_to(ROOT)}')
if errors:
    print('\n'.join('ERROR: '+x for x in errors[:100]));sys.exit(1)
print(f'Validated {len(catalog["nodes"])} nodes, {len(catalog["peripherals"])} peripherals, {len(catalog["boards"])} boards, {len(tutorials)} tutorials, {len(guides)} learning guides, {len(screens)} screenshots, {len(catalog["locales"])} locale routes')
