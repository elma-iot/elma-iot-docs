from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FEATURE_HELP={
 'device-setup-wizard':'setup.overview','board-selection':'tutorials.select-esp-board',
 'peripheral-selection':'tutorials.add-peripherals','graphic-designer':'graphic-designer',
 'vertical-logics-constructor':'tutorials.first-logic','blueprint-logics-canvas':'logics.overview',
 'instrument-panel':'getting-started','compile-flash':'compile','usb':'flash.usb',
 'ota':'flash.ota','serial-monitor':'serial-monitor',
}
entries=[]
base=ROOT/'assets/screenshots/android'
for locale_dir in sorted(x for x in base.iterdir() if x.is_dir()):
 for feature,help_id in FEATURE_HELP.items():
  image=locale_dir/(feature+'.png')
  if not image.is_file():continue
  entries.append({'platform':'Android','applicationVersion':'1.0.13 debug','locale':locale_dir.name,
   'feature':feature,'helpId':help_id,'capturedAt':'2026-09-19','path':image.relative_to(ROOT).as_posix()})
(ROOT/'data/screenshots.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'Indexed {len(entries)} localized screenshots across {len({x["locale"] for x in entries})} locales')
