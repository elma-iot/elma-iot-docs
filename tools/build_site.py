from __future__ import annotations
import html, json, shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"_site"; BASE="/elma-iot-docs"
CAT=json.loads((ROOT/"data/catalog.json").read_text(encoding="utf-8"))
TOPICS=json.loads((ROOT/"content/topics.json").read_text(encoding="utf-8"))
TUTORIALS=json.loads((ROOT/"content/tutorials.json").read_text(encoding="utf-8"))
SCREENSHOTS=json.loads((ROOT/"data/screenshots.json").read_text(encoding="utf-8"))
TYPE_COLORS={"execution":"#edf2fb","boolean":"#f33f4a","number":"#24bc73","integer":"#13bbdb","string":"#df59ba","analog":"#ef9900","peripheral":"#438deb","path":"#438deb","audio":"#20bac4","scalar":"#13bbdb"}
RTL={"ar","fa"}
LOCALE_NAMES={"en":"English","es":"Español","zh":"中文","hi":"हिन्दी","ar":"العربية","pt":"Português","bn":"বাংলা","ru":"Русский","ja":"日本語","de":"Deutsch","fr":"Français","ko":"한국어","tr":"Türkçe","it":"Italiano","id":"Bahasa Indonesia","pl":"Polski","uk":"Українська","vi":"Tiếng Việt","th":"ไทย","fa":"فارسی"}
UI={
 "en":{"search":"Search documentation","fallback":"This article is shown in English while its translation is being prepared.","contents":"Contents","related":"Related topics","applies":"Applies to","helpful":"Was this helpful?","report":"Report documentation issue"},
 "ru":{"search":"Поиск в документации","fallback":"Эта статья показана на английском языке, пока готовится перевод.","contents":"Содержание","related":"Связанные темы","applies":"Применимо к","helpful":"Была ли эта статья полезна?","report":"Сообщить о проблеме в документации"},
 "es":{"search":"Buscar en la documentación","fallback":"Este artículo se muestra en inglés mientras se prepara la traducción.","contents":"Contenido","related":"Temas relacionados","applies":"Se aplica a","helpful":"¿Fue útil?","report":"Informar de un problema"},
}

def esc(v): return html.escape(str(v),quote=True)
def route(help_id): return help_id.replace(".","/")
def href(locale,help_id): return f"{BASE}/{locale}/{route(help_id)}/"
def write(path,text): path.parent.mkdir(parents=True,exist_ok=True); path.write_text(text,encoding="utf-8")
def pill(kind): return f'<span class="type" style="--type:{TYPE_COLORS.get(kind,"#8894a5")}">{esc(kind.title())}</span>'
def table(headers,rows):
    if not rows:return '<p class="muted">None.</p>'
    return '<div class="table"><table><thead><tr>'+''.join(f'<th>{esc(x)}</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def connector_rules(kind,direction):
    if direction=="output": return {"execution":"Flow inputs","boolean":"Boolean or scalar inputs","integer":"Integer, number, or scalar inputs","number":"Number or scalar inputs","analog":"Analog, number, or scalar inputs","string":"Text or scalar inputs","peripheral":"Peripheral inputs","path":"Path or audio inputs","audio":"Audio inputs"}.get(kind,"same-type inputs")
    return {"execution":"Flow outputs","boolean":"Boolean outputs","integer":"Integer outputs","number":"Number, integer, or analog outputs","analog":"Analog outputs","string":"Text outputs","scalar":"Number, integer, analog, Boolean, or text outputs","peripheral":"Peripheral reference outputs","path":"Path outputs","audio":"Audio or path outputs"}.get(kind,"same-type outputs")

def node_body(n):
    ins=[p for p in n["ports"] if p["direction"]=="input"]; outs=[p for p in n["ports"] if p["direction"]=="output"]
    def prow(p):
        default=n["parameters"].get(p["id"],"")
        req="Required" if p.get("required") else "Optional"
        if p["id"] in n["parameters"]: req+="; inline default is used while unwired"
        return [esc(p["label"]),pill(p["type"]),esc(req),esc(default),esc(connector_rules(p["type"],"input"))]
    def orow(p): return [esc(p["label"]),pill(p["type"]),esc(connector_rules(p["type"],"output"))]
    enable=next((p for p in ins if p["id"] in ("enabled","enable","en")),None)
    binding=n.get("binding") or {}; mode=binding.get("kind","")
    execution={"status":"Reads current live device state without generating Flow.","transition":"Emits Flow only when the named state transition occurs.","action":"Runs when Flow reaches the required In connector; Out means the request was submitted.","event":"Emits Flow for the named lifecycle event."}.get(mode,"Values update through data connections; actions with an In connector run when Flow arrives.")
    common="A Boolean result is data, not a Flow pulse; use Rising Edge, Falling Edge, IF, or Branch when an action must run on a condition." if any(p["type"]=="boolean" for p in outs) else "Do not connect incompatible colors/types, and do not expect a value/source connection by itself to trigger an action."
    params=[[esc(k),esc(type(v).__name__),esc(v)] for k,v in n["parameters"].items()]
    review='<aside class="review">Technical review needed: the implementation registry has no specific behavioral explanation for this block.</aside>' if n.get("technicalReview") else ''
    return f'''<p class="lead">{esc(n["purpose"])}</p>{review}
<h2>When to use it</h2><p>Use this block when the workflow needs the behavior described above and its typed connectors match the adjacent blocks.</p>
<h2>Inputs</h2>{table(["Connector","Type","Requirement","Default","Accepts"],[prow(p) for p in ins])}
<h2>Outputs</h2>{table(["Connector","Type","Connects to"],[orow(p) for p in outs])}
<h2>Enable behavior</h2><p>{esc("When Enabled is false, the block does not pass or produce its controlled execution. When true, normal behavior resumes." if enable else "This block has no EN/Enabled connector. Control it with its documented Flow or data inputs.")}</p>
<h2>Parameters and defaults</h2>{table(["Parameter","Stored type","Default"],params)}
<h2>Execution and trigger behavior</h2><p>{esc(execution)}</p>
<h2>State and persistence</h2><p>Stored inline values, graph connections, positions, and group membership are saved with the project and embedded during compilation. Runtime values come from the device and do not replace project defaults.</p>
<h2>Valid and invalid connections</h2><p>Connect outputs only to compatible input types shown above. A wired value overrides its inline default. An incompatible connection is rejected by the editor and firmware validation.</p>
<h2>Common mistake</h2><p>{esc(common)}</p>
<h2>Practical example</h2><pre>{esc(n["example"])}</pre>'''

def peripheral_body(p):
    req=[[esc(k),esc(v),esc(p["rails"].get(k,""))] for k,v in p["requirements"].items()]
    pins=[[esc(x),esc(p["rails"].get(x,"Signal or profile-dependent"))] for x in p["pins"]]
    return f'''<p class="lead">The {esc(p["title"])} profile configures a {esc(p["group"])} peripheral for ELMA-IoT.</p>
<h2>Purpose and compatibility</h2><p>This built-in profile is available to supported boards when its required signals can be assigned without a GPIO conflict. Board-specific validity is checked by the project validator.</p>
<h2>Power, pins, and interfaces</h2>{table(["Pin or signal","Known rail / role"],pins)}{table(["Signal","Direction","Rail"],req)}
<h2>Configuration fields and defaults</h2><p>Add the profile in the {esc(p["group"])} section, then review every assigned signal. No undocumented electrical limits are assumed; verify the module manufacturer’s voltage and current requirements.</p>
<h2>Logics values, events, and actions</h2><p>The Logics palette exposes only capabilities generated for the selected profile. Values use colored typed connectors; actions require a white Flow input. Availability varies by peripheral category.</p>
<h2>Wiring and usage</h2><ol><li>Select the exact board and this profile.</li><li>Open the generated wiring diagram and connect every listed signal and rail.</li><li>Add the profile’s generated Logics block, if available, and connect compatible types.</li><li>Compile, flash, and verify the live value or action.</li></ol>
<h2>Known limitations</h2><p>Manufacturer model, library version, power limits, and bus-address details not present in the maintained profile metadata require technical review before they can be stated here.</p>'''

def board_body(b):
    pins=[[esc(x.get("label","")),esc(x.get("pin") if x.get("pin") is not None else "Power / ground")] for x in b["pins"]]
    reserved=[[esc(k),esc(v)] for k,v in b["reserved"].items()]
    return f'''<p class="lead">ELMA-IoT target for the {esc(b["chip"].upper())} family. {esc(b["assetAlt"])}</p>
<h2>GPIO map</h2>{table(["Board label","GPIO"],pins)}
<h2>Reserved and boot pins</h2>{table(["GPIO","Reason"],reserved)}<p>Automatic GPIO assignment uses the board metadata. Enable reserved-pin overrides only after verifying boot, USB, flash, PSRAM, and on-board-device restrictions.</p>
<h2>Interfaces and capabilities</h2><p>ADC, DAC, PWM, I2C, SPI, UART, I2S, CAN/TWAI, USB, flash, and PSRAM availability depends on the selected {esc(b["chip"])} target and exposed board pins. The editor validates requested peripheral signals against the maintained board capability metadata.</p>
<h2>Power and compatibility</h2><p>Use the voltage printed on the board and module documentation. A GPIO is a logic signal, not a general power source. Peripheral compatibility also depends on required buses, free pins, and firmware support.</p>
<aside class="review">Technical review: the source catalog does not yet state complete electrical limits and every silicon capability for this board. Consult the board manufacturer before wiring hardware outside the generated diagram.</aside>'''

def generic_body(t):
    hid=t["helpId"]
    extras={
      "logics.connectors":connector_reference(),
      "logics.overview":"<h2>How a workflow runs</h2><p>Data connectors carry current values. White Flow connectors trigger actions. Groups define independently controllable automations with Play, Pause, and Stop. Save and compile to embed the graph in firmware; the device web interface recreates the supported graph and overlays live values.</p><h2>Editing</h2><p>Drag blocks from the palette, connect compatible ports, set inline defaults, and group complete automations. Hover or long-press for local guidance, and use Documentation to open the exact online article.</p>",
      "flash.ota":"<h2>Before updating</h2><p>The device must be reachable over HTTP, identify as compatible ELMA firmware or pass the explicit migration checks, match the compiled chip, and have an OTA-capable partition layout. Keep power stable until restart completes.</p>",
      "flash.usb":"<h2>Safe sequence</h2><p>Select the correct serial device, enter download mode if requested, write and verify all required regions, then allow the application to restart and acknowledge configuration. A verified image without configuration acknowledgement should be reconnected and checked rather than assumed complete.</p>",
      "mqtt.overview":"<h2>Key terms</h2><p><strong>Topic</strong> is the exact destination name. <strong>Retained</strong> asks the broker to keep the last message for new subscribers. <strong>QoS 0</strong> sends at most once; <strong>QoS 1</strong> requests at least one delivery and can duplicate a message. A successful queue operation is not the same as broker acknowledgement.</p>",
    }.get(hid,"")
    return f'<p class="lead">{esc(t["summary"])}</p>{extras}<h2>Recommended workflow</h2><p>Open contextual Documentation from the feature whenever possible. It preserves the active language and routes directly to the relevant article. ELMA-IoT continues working if online Help is unavailable.</p>'

def connector_reference():
    descriptions={"execution":"White Flow pulses start actions; they do not carry a sensor value.","boolean":"True/False conditions. Use an edge or branch to turn a condition into Flow.","integer":"Whole numbers.","number":"Floating-point or compatible integer/analog values.","analog":"Measured numeric values from ADC-style inputs.","string":"Text values.","scalar":"Accepts a number, integer, analog, Boolean, or text value.","peripheral":"A configured hardware reference used by generic actions.","path":"A stored file/path source; it can feed compatible audio input.","audio":"An audio source description; a separate Flow trigger starts playback."}
    rows=[[pill(k),f'<span class="swatch" style="--type:{v}"></span>{v}',esc(descriptions[k])] for k,v in TYPE_COLORS.items()]
    return '<h2>Connector colors and meaning</h2>'+table(["Type","Color","Meaning"],rows)+'<h2>Direction and inline values</h2><p>Outputs face away from their block and connect to inputs. Required inputs must be wired. Optional inputs can use stored inline values; after wiring, the connected live value overrides the stored default. EN/Enabled is Boolean gating. Invalid type combinations are rejected.</p>'

def tutorial_body(t):
    return f'<p class="lead">{esc(t["why"])}</p><h2>Steps</h2><ol>'+''.join(f'<li>{esc(x)}</li>' for x in t["steps"])+f'</ol><h2>What to verify</h2><p>Save the project, check validation, and confirm the resulting behavior on the actual target. Use the linked feature articles for connector, pin, and flashing details.</p>'

def related_for(item,kind):
    if kind=="node":
        category=item["category"]
        related=[n["helpId"] for n in CAT["nodes"] if n["category"]==category and n["helpId"]!=item["helpId"]][:4]
        if any(p["type"] in ("execution","boolean","scalar") for p in item["ports"]): related.insert(0,"logics.connectors")
        return related[:5]
    if kind=="peripheral": return ["setup.peripherals","setup.gpio","graphic-designer","logics.overview"]
    if kind=="board": return ["setup.gpio","setup.peripherals","flash.usb","flash.ota"]
    return ["getting-started","tutorials","troubleshooting"]

def page(locale,item,kind,all_titles):
    ui={**UI["en"],**UI.get(locale,{})}; help_id=item["helpId"]; title=item["title"]
    body=node_body(item) if kind=="node" else peripheral_body(item) if kind=="peripheral" else board_body(item) if kind=="board" else tutorial_body(item) if kind=="tutorial" else generic_body(item)
    related=related_for(item,kind)
    figures=''.join(f'<figure><img src="{BASE}/{esc(s["path"])}" alt="Current {esc(s["platform"])} {esc(s["feature"].replace("-"," "))} screen" loading="lazy"><figcaption>{esc(s["platform"])} {esc(s["applicationVersion"])} · captured {esc(s["capturedAt"])}</figcaption></figure>' for s in SCREENSHOTS if s['helpId']==help_id)
    rel=''.join(f'<li><a href="{href(locale,x)}">{esc(all_titles.get(x,x))}</a></li>' for x in related if x in all_titles)
    options=''.join(f'<option value="{esc(code)}" {"selected" if code==locale else ""}>{esc(LOCALE_NAMES[code])}</option>' for code in CAT["locales"])
    fallback='' if locale=="en" else f'<aside class="fallback">{esc(ui["fallback"])}</aside>'
    issue=f'https://github.com/elma-iot/elma-iot-docs/issues/new?title=Documentation%3A%20{help_id}'
    return f'''<!doctype html><html lang="{locale}" dir="{'rtl' if locale in RTL else 'ltr'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · ELMA-IoT Help</title><meta name="description" content="{esc(item.get('summary',item.get('purpose','ELMA-IoT documentation')))}"><link rel="stylesheet" href="{BASE}/assets/site.css"></head><body data-locale="{locale}" data-help-id="{esc(help_id)}"><header><a class="brand" href="{BASE}/{locale}/">ELMA-IoT Help</a><input id="search" type="search" placeholder="{esc(ui['search'])}" autocomplete="off"><select id="locale" aria-label="Language">{options}</select></header><div id="results" hidden></div><main><nav><strong>{esc(ui['contents'])}</strong><a href="{href(locale,'getting-started')}">Getting started</a><a href="{href(locale,'setup.overview')}">Setup</a><a href="{href(locale,'logics.overview')}">Logics</a><a href="{href(locale,'tutorials')}">Tutorials</a><a href="{href(locale,'troubleshooting')}">Troubleshooting</a></nav><article>{fallback}<p class="eyebrow">{esc(help_id)}</p><h1>{esc(title)}</h1><p class="version">{esc(ui['applies'])}: Android {CAT['appliesTo']['android']} · Windows {CAT['appliesTo']['windows']} · Firmware {CAT['appliesTo']['firmware']}</p>{body}{figures}<h2>{esc(ui['related'])}</h2><ul>{rel}</ul><footer><strong>{esc(ui['helpful'])}</strong> <a href="{issue}">{esc(ui['report'])}</a>. No usage telemetry is collected.</footer></article></main><script src="{BASE}/assets/site.js"></script></body></html>'''

def home(locale,items):
    cards=''.join(f'<a class="card" href="{href(locale,x["helpId"])}"><strong>{esc(x["title"])}</strong><span>{esc(x.get("summary","Open documentation"))}</span></a>' for x in items if x["helpId"] in ("getting-started","setup.overview","graphic-designer","logics.overview","mqtt.overview","flash.usb","flash.ota","serial-monitor","web-interface","tutorials","troubleshooting"))
    return page(locale,{"helpId":"home","title":"ELMA-IoT online documentation","summary":"One public source for ELMA-IoT setup, Logics, hardware, flashing, tutorials, and troubleshooting."},"generic",{"getting-started":"Getting started","tutorials":"Tutorials","troubleshooting":"Troubleshooting"}).replace('<h2>Recommended workflow</h2>',f'<div class="cards">{cards}</div><h2>Recommended workflow</h2>')

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    items=[]
    items += [(x,"generic") for x in TOPICS]
    items += [({"helpId":"tutorials."+x["id"],"title":x["title"],"summary":x["why"],**x},"tutorial") for x in TUTORIALS]
    items += [(x,"node") for x in CAT["nodes"]]
    items += [(x,"peripheral") for x in CAT["peripherals"]]
    items += [(x,"board") for x in CAT["boards"]]
    titles={x["helpId"]:x["title"] for x,_ in items}; titles.update({"getting-started":"Getting started","tutorials":"Tutorials","troubleshooting":"Troubleshooting"})
    for locale in CAT["locales"]:
        write(OUT/locale/"index.html",home(locale,TOPICS))
        search=[]
        for item,kind in items:
            write(OUT/locale/route(item["helpId"])/"index.html",page(locale,item,kind,titles))
            search.append({"title":item["title"],"helpId":item["helpId"],"url":href(locale,item["helpId"]),"text":" ".join(map(str,[item.get("summary",""),item.get("purpose",""),item.get("example","")," ".join(item.get("aliases",[]))]))})
        write(OUT/"assets"/"search"/(locale+".json"),json.dumps(search,ensure_ascii=False))
    root='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ELMA-IoT Help</title><script>const s=["en","es","zh","hi","ar","pt","bn","ru","ja","de","fr","ko","tr","it","id","pl","uk","vi","th","fa"];let l=(navigator.language||"en").toLowerCase().split("-")[0];location.replace("'''+BASE+'''/"+(s.includes(l)?l:"en")+"/")</script></head><body><a href="'''+BASE+'''/en/">ELMA-IoT Help</a></body></html>'''
    write(OUT/"index.html",root); write(OUT/"404.html",root)
    shutil.copytree(ROOT/"assets",OUT/"assets",dirs_exist_ok=True)
    print(f"Built {len(items)} topics for {len(CAT['locales'])} locales ({len(items)*len(CAT['locales'])} routes)")

if __name__=="__main__": main()
