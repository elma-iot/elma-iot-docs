from __future__ import annotations
import html,json,re,subprocess,sys,time,urllib.parse,urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
LOCALES=['es','zh','hi','ar','pt','bn','ru','ja','de','fr','ko','tr','it','id','pl','uk','vi','th','fa']
SKIP_TAGS={'script','style','code','pre','kbd','samp'}
KEEP={'ELMA-IoT','Android','Windows','Firmware','GPIO','MQTT','Wi-Fi','OTA','USB','ADC','DAC','PWM','I2C','SPI','UART','I2S','CAN','TWAI','PSRAM','QoS','JSON','HTML','ESP32','ESP32-S3','ESP32-C3','ESP8266','DRV8833','Home Assistant'}

def polish(value,locale):
 if locale=='ru':
  for source,target in [('Доски','Платы'),('доски','платы'),('Доску','Плату'),('доску','плату'),('Доска','Плата'),('доска','плата'),('Доске','Плате'),('доске','плате'),('Доской','Платой'),('доской','платой'),('Досок','Плат'),('досок','плат')]:value=value.replace(source,target)
 if locale=='es':
  for source,target in [('Tableros','Placas'),('tableros','placas'),('Tablero','Placa'),('tablero','placa')]:value=value.replace(source,target)
  value=value.replace('placa seleccionado','placa seleccionada').replace('placa exacto','placa exacta').replace('placa físico','placa física')
 return value

def useful(value):
 value=html.unescape(value.strip())
 return len(value)>1 and bool(re.search('[A-Za-z]',value)) and value not in KEEP and not value.startswith(('http://','https://','/elma-iot-docs/')) and not re.fullmatch(r'[a-z0-9_.:/-]+',value)

class TextCollector(HTMLParser):
 def __init__(self):super().__init__(convert_charrefs=False);self.stack=[];self.values=set()
 def handle_starttag(self,tag,attrs):
  self.stack.append(tag)
  for key,value in attrs:
   if key in {'title','aria-label','placeholder','alt','content'} and value and useful(value):self.values.add(html.unescape(value.strip()))
 def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.stack.pop()
 def handle_endtag(self,tag):
  if self.stack:self.stack.pop()
 def handle_data(self,data):
  if not any(x in SKIP_TAGS for x in self.stack) and useful(data):self.values.add(html.unescape(data.strip()))

def translate_batch(strings,locale):
 payload='\n'.join(f'[[ELMA{i:04d}]] {value}' for i,value in enumerate(strings))
 url='https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl='+locale+'&dt=t&q='+urllib.parse.quote(payload)
 request=urllib.request.Request(url,headers={'User-Agent':'ELMA-IoT documentation builder'})
 result=json.loads(urllib.request.urlopen(request,timeout=45).read().decode('utf-8'))
 joined=''.join(part[0] for part in result[0]);matches=list(re.finditer(r'\[\[ELMA(\d{4})\]\]\s*',joined))
 translated={}
 for pos,match in enumerate(matches):
  end=matches[pos+1].start() if pos+1<len(matches) else len(joined)
  translated[int(match.group(1))]=joined[match.end():end].strip()
 if len(translated)!=len(strings):
  if len(strings)==1:
   clean=re.sub(r'^\s*\[\[ELMA\d{4}\]\]\s*','',joined).strip()
   if not clean:raise RuntimeError(f'{locale}: empty translation for {strings[0]!r}')
   return [clean]
  middle=len(strings)//2
  return translate_batch(strings[:middle],locale)+translate_batch(strings[middle:],locale)
 return [translated[i] for i in range(len(strings))]

def main():
 subprocess.run([sys.executable,str(ROOT/'tools/build_site.py')],check=True)
 collector=TextCollector()
 for path in (ROOT/'_site/en').rglob('*.html'):collector.feed(path.read_text(encoding='utf-8'))
 strings=sorted(collector.values,key=lambda x:(len(x),x));target=ROOT/'content/locales';target.mkdir(parents=True,exist_ok=True)
 for locale in LOCALES:
  path=target/(locale+'.json');mapping=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
  missing=[x for x in strings if x not in mapping];print(f'{locale}: {len(missing)} missing of {len(strings)}')
  batch=[];size=0
  for value in [*missing,None]:
   if value is not None and batch and size+len(value)>3200:
    for source,translated in zip(batch,translate_batch(batch,locale)):mapping[source]=translated
    path.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');batch=[];size=0;time.sleep(.18)
   if value is not None:batch.append(value);size+=len(value)+18
  if batch:
   for source,translated in zip(batch,translate_batch(batch,locale)):mapping[source]=translated
  mapping={source:polish(value,locale) for source,value in mapping.items()}
  path.write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'Translated {len(strings)} documentation strings into {len(LOCALES)} locales')

if __name__=='__main__':main()
