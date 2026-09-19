from __future__ import annotations
import html, json, re, shutil
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"_site"; BASE="/elma-iot-docs"
CAT=json.loads((ROOT/"data/catalog.json").read_text(encoding="utf-8"))
TOPICS=json.loads((ROOT/"content/topics.json").read_text(encoding="utf-8"))
TUTORIALS=json.loads((ROOT/"content/tutorials.json").read_text(encoding="utf-8"))
GUIDES=[]
for guide_path in sorted((ROOT/"content/guides").glob("*.json")):
    value=json.loads(guide_path.read_text(encoding="utf-8")); GUIDES.extend(value if isinstance(value,list) else [value])
SCREENSHOTS=json.loads((ROOT/"data/screenshots.json").read_text(encoding="utf-8"))
SCREENSHOT_BY_LOCALE_FEATURE={(x.get("locale","en"),x["feature"]):x for x in SCREENSHOTS}
TRANSLATIONS={}
for locale_path in (ROOT/"content/locales").glob("*.json") if (ROOT/"content/locales").exists() else []:
    TRANSLATIONS[locale_path.stem]=json.loads(locale_path.read_text(encoding="utf-8"))
TUTORIAL_SCREENSHOTS={
 "first-esp-project":["device-setup-wizard","board-selection","peripheral-selection","compile-flash"],
 "select-esp-board":["board-selection"], "add-peripherals":["peripheral-selection"],
 "automatic-gpio":["peripheral-selection","graphic-designer"], "wiring-diagram":["graphic-designer"],
 "first-logic":["vertical-logics-constructor","blueprint-logics-canvas"],
 "sensor-compare-relay":["vertical-logics-constructor","blueprint-logics-canvas"],
 "low-battery-warning":["blueprint-logics-canvas"], "mqtt-live-value":["blueprint-logics-canvas"],
 "oled-output":["peripheral-selection","blueprint-logics-canvas"],
 "audio-tts":["peripheral-selection","blueprint-logics-canvas"],
 "compile-firmware":["compile-flash"], "flash-usb":["usb"], "ota-update":["ota"],
 "serial-monitor":["serial-monitor"], "compile-troubleshooting":["compile-flash"],
 "usb-troubleshooting":["usb","serial-monitor"], "ota-troubleshooting":["ota"],
}
GUIDE_SCREENSHOTS={
 "getting-started.architecture":["instrument-panel","blueprint-logics-canvas"],
 "getting-started.installation":["device-setup-wizard","usb"],
 "getting-started.first-15-minutes":["device-setup-wizard","board-selection","peripheral-selection","graphic-designer","compile-flash","usb"],
 "building-devices":["graphic-designer","blueprint-logics-canvas"],
 "logics.thinking":["vertical-logics-constructor","blueprint-logics-canvas"],
 "logics.state-timing":["blueprint-logics-canvas"],
 "configuration.reference":["device-setup-wizard","peripheral-selection"],
 "cookbook.thermostat":["blueprint-logics-canvas"],
 "cookbook.mini-piano":["vertical-logics-constructor","blueprint-logics-canvas"],
 "troubleshooting.wifi":["ota","serial-monitor"],
 "troubleshooting.hardware":["graphic-designer","serial-monitor"],
}
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
def screenshot(locale,feature): return SCREENSHOT_BY_LOCALE_FEATURE.get((locale,feature)) or SCREENSHOT_BY_LOCALE_FEATURE.get(("en",feature))

class LocalizedHtml(HTMLParser):
    ATTRIBUTES={"title","aria-label","placeholder","alt","content"};SKIP={"script","style","code","pre","kbd","samp","locale-select"}
    def __init__(self,mapping):super().__init__(convert_charrefs=False);self.mapping=mapping;self.parts=[];self.stack=[]
    def translated(self,value):
        leading=value[:len(value)-len(value.lstrip())];trailing=value[len(value.rstrip()):];core=value.strip()
        return leading+self.mapping.get(html.unescape(core),core)+trailing if core else value
    def handle_decl(self,decl):self.parts.append(f'<!{decl}>')
    def handle_comment(self,data):self.parts.append(f'<!--{data}-->')
    def handle_starttag(self,tag,attrs):
        marker="locale-select" if tag=="select" and dict(attrs).get("id")=="locale" else tag
        self.stack.append(marker);render=[]
        for key,value in attrs:
            if value is None:render.append(key);continue
            localized=self.mapping.get(html.unescape(value),value) if key in self.ATTRIBUTES else value
            render.append(f'{key}="{html.escape(localized,quote=True)}"')
        self.parts.append('<'+tag+(' '+' '.join(render) if render else '')+'>')
    def handle_startendtag(self,tag,attrs):self.handle_starttag(tag,attrs);self.stack.pop();self.parts[-1]=self.parts[-1][:-1]+'/>'
    def handle_endtag(self,tag):
        if self.stack:self.stack.pop()
        self.parts.append(f'</{tag}>')
    def handle_data(self,data):self.parts.append(data if any(x in self.SKIP for x in self.stack) else self.translated(data))
    def handle_entityref(self,name):self.parts.append(f'&{name};')
    def handle_charref(self,name):self.parts.append(f'&#{name};')

def localize_document(document,locale):
    if locale=="en":return document
    parser=LocalizedHtml(TRANSLATIONS.get(locale,{}));parser.feed(document);return ''.join(parser.parts)
def localized_text(locale,value):return TRANSLATIONS.get(locale,{}).get(str(value),str(value))
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
    visual_inputs=''.join(f'<span class="visual-port input" style="--port:{TYPE_COLORS.get(p["type"],"#8894a5")}"><i></i>{esc(p["label"])}</span>' for p in ins)
    visual_outputs=''.join(f'<span class="visual-port output" style="--port:{TYPE_COLORS.get(p["type"],"#8894a5")}">{esc(p["label"])}<i></i></span>' for p in outs)
    visual=f'<figure class="node-visual"><figcaption>Current block layout and connector positions</figcaption><div class="node-card"><strong>{esc(n["title"])}</strong><div class="node-ports"><div>{visual_inputs}</div><div>{visual_outputs}</div></div></div></figure>'
    review='<aside class="review">Technical review needed: the implementation registry has no specific behavioral explanation for this block.</aside>' if n.get("technicalReview") else ''
    return f'''<p class="lead">{esc(n["purpose"])}</p>{review}{visual}
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
    req=[[esc(k),esc(v),esc(p["rails"].get(k,"Signal; board GPIO selected by the project"))] for k,v in p["requirements"].items()]
    pins=[[esc(x),esc(p["rails"].get(x,"Signal or profile-dependent"))] for x in p["pins"]]
    group=p["group"]; pid=p["peripheralId"].split(":",1)[-1]
    caps=[]
    if group=="audio": caps=["Play","Stop"] if "buzzer" in pid else ["Play","Stop","Volume"]
    elif group=="display" and pid=="i2c-oled": caps=["Set text","Clear text"]
    elif group=="storage" and any(x in pid for x in ("microsd","sdmmc","spi-flash","littlefs")): caps=["Select audio file"]
    elif group=="sensor" and "voltage-divider" in pid: caps=["Voltage","Percentage","Low","Critical"]
    elif group=="control" and "relay" in pid: caps=["ON","OFF","Toggle","Set state","State"]
    elif group=="control" and "buzzer" in pid: caps=["Play melody","Stop"]
    elif group=="input" and "joystick" in pid: caps=["Analog value","X axis","Y axis","Button state"]
    elif group=="input" and "potentiometer" in pid: caps=["Analog value"]
    elif group=="input" and any(x in pid for x in ("button","switch","pir","reed")): caps=["State","Rising edge","Falling edge"]
    dedicated=group=="control" and pid=="drv8833-dual-motor-driver"
    if dedicated:
        status='<aside class="support supported"><strong>Runtime support:</strong> the dedicated Motor runtime implements two timed direction channels, optional limit-stop inputs, learned open/closed roles, and MQTT commands. A generic DRV8833 Logics action adapter is not currently supported.</aside>'
    elif caps:
        status=f'<aside class="support supported"><strong>Runtime support:</strong> firmware Logics adapters are implemented for {esc(", ".join(caps))}. The profile also participates in GPIO validation and the wiring diagram.</aside>'
    else:
        status='<aside class="support wiring"><strong>Runtime support: not currently supported.</strong> This is a configuration and wiring profile only. GPIO assignment and diagrams are available, but selecting it does not by itself initialize or control the hardware.</aside>'
    typical={"audio":"audio output module, amplifier, DAC, or buzzer named by this profile","audioIn":"microphone or audio input module named by this profile","display":"display module named by this profile","sensor":"sensor module named by this profile","input":"button, switch, or input module named by this profile","power":"power-conversion module named by this profile","control":"actuator driver named by this profile","expansion":"bus expander or converter named by this profile","storage":"storage module named by this profile","communication":"communications interface named by this profile"}.get(group,"module named by this profile")
    signal_rows=[[esc(k),"GPIO selector","Required",esc(v),esc(p["rails"].get(k,"Board-dependent"))] for k,v in p["requirements"].items()]
    advanced=('<li>Use the device Motor page or documented MQTT channel commands; configure a maximum duration and end switch before increasing movement time.</li>' if dedicated else f'<li>Add the generated capability blocks ({esc(", ".join(caps))}) to a grouped automation and verify live values or actions on the target.</li>' if caps else '<li>Do not build an automation around this profile until a firmware adapter exists; use it as a reviewed wiring plan or implement a custom hardware package.</li>')
    return f'''<p class="lead">The <strong>{esc(p["title"])}</strong> entry is ELMA-IoT’s {esc(group)} profile for a {esc(typical)}.</p>{status}
<h2>What this profile provides</h2><p>It declares the signals, directions, power labels, and GPIO requirements used by automatic assignment, conflict checking, and the Graphic Designer. Runtime support is stated separately above because a wiring profile is not proof that a firmware driver exists.</p>
<h2>Typical hardware</h2><p>Use the exact module named by the profile, or a genuinely compatible module with the same interface and voltage requirements. Similar connector names do not guarantee electrical compatibility.</p>
<h2>Wiring</h2>{table(["Pin or signal","Declared rail / role"],pins)}{table(["Signal","GPIO capability","Declared rail"],req)}
<aside class="safety"><strong>Electrical safety:</strong> ESP GPIO is low-voltage logic and must not directly power motors, pumps, speakers, relay coils, solenoids, heaters, or mains loads. Use the correct driver and external supply, join grounds where the interface requires it, and verify the module datasheet. Never assume an ESP input is 5 V tolerant.</aside>
<h2>Minimal configuration</h2><ol><li>Select the exact ESP board.</li><li>Add <strong>{esc(p["title"])}</strong> under {esc(group)}.</li><li>Accept safe automatic GPIO assignments or choose pins that satisfy every capability below.</li><li>Open the wiring diagram and compare every signal, supply rail, and ground with the physical module before applying power.</li></ol>
<h2>Configuration fields</h2>{table(["Field","Type","Required","Meaning","Default"],signal_rows)}<p>GPIO defaults are board- and project-dependent because ELMA-IoT avoids reserved pins and collisions. The generated value shown in your project is authoritative for that build.</p>
<h2>Runtime behavior and Logics</h2><p>{esc("The dedicated Motor service owns this profile; use its web/MQTT controls. Generic visual Logics actions for DRV8833 are not compiled." if dedicated else "The compiled runtime binds only the listed capabilities to this configured slot. A wired value overrides its inline default; Flow inputs trigger actions." if caps else "No generic Logics execution adapter is compiled for this profile. Its presence in the palette documents wiring and reserves pins only.")}</p>
<h2>Examples</h2><h3>Minimal</h3><p>Add one profile, keep automatic GPIO assignment enabled, compile, and confirm there are no pin conflicts.</p><h3>Practical</h3><p>Give the slot a meaningful project role, such as “Tank high switch” or “Cooling relay,” then verify the generated wiring against the module labels before flashing.</p><h3>Advanced</h3><ol>{advanced}</ol>
<h2>Common mistakes</h2><ul><li>Choosing a similarly named module with a different pinout or voltage.</li><li>Powering a load from GPIO or omitting the required driver and flyback protection.</li><li>Forgetting the common reference ground between logic and an external low-voltage driver.</li><li>Manually overriding a boot, flash, USB, input-only, or already-used GPIO.</li><li>Assuming a configuration-only profile already has a firmware driver.</li></ul>
<h2>Known limits</h2><p>Exact current, voltage, bus address, timing, and library requirements are not present in the profile metadata unless shown above. Check the hardware manufacturer’s documentation. Configuration support and runtime support are deliberately reported separately.</p>'''

def board_body(b):
    pins=[[esc(x.get("label","")),esc(x.get("pin") if x.get("pin") is not None else "Power / ground")] for x in b["pins"]]
    reserved=[[esc(k),esc(v)] for k,v in b["reserved"].items()]
    return f'''<p class="lead">ELMA-IoT target for the {esc(b["chip"].upper())} family. {esc(b["assetAlt"])}</p>
<h2>GPIO map</h2>{table(["Board label","GPIO"],pins)}
<h2>Reserved and boot pins</h2>{table(["GPIO","Reason"],reserved)}<p>Automatic GPIO assignment uses the board metadata. Enable reserved-pin overrides only after verifying boot, USB, flash, PSRAM, and on-board-device restrictions.</p>
<h2>Interfaces and capabilities</h2><p>ADC, DAC, PWM, I2C, SPI, UART, I2S, CAN/TWAI, USB, flash, and PSRAM availability depends on the selected {esc(b["chip"])} target and exposed board pins. The editor validates requested peripheral signals against the maintained board capability metadata.</p>
<h2>Power and compatibility</h2><p>Use the voltage printed on the board and module documentation. A GPIO is a logic signal, not a general power source. Peripheral compatibility also depends on required buses, free pins, and firmware support.</p>
<h2>Minimal setup example</h2><ol><li>Select this exact board profile before adding peripherals.</li><li>Keep automatic GPIO assignment enabled.</li><li>Add one low-voltage peripheral, review every generated signal, VCC, and GND connection, then compile.</li><li>Use Serial Monitor to confirm the reported chip and board profile after flashing.</li></ol>
<h2>Common mistakes</h2><ul><li>Selecting a board with the same chip but a different flash, PSRAM, USB, LED, or header layout.</li><li>Using the printed header position as though it were the GPIO number.</li><li>Overriding boot, flash, USB, or on-board-device pins without checking the schematic.</li><li>Applying 5 V to a non-tolerant GPIO or powering a load from a signal pin.</li></ul>
<aside class="review">Technical review: the source catalog does not yet state complete electrical limits and every silicon capability for this board. Consult the board manufacturer before wiring hardware outside the generated diagram.</aside>'''

def generic_body(t,locale="en"):
    hid=t["helpId"]
    details={
      "getting-started":f'''<h2>Learning path</h2><ol><li><a href="{href(locale,'getting-started.architecture')}">Understand the architecture</a>.</li><li><a href="{href(locale,'getting-started.installation')}">Prepare the application and hardware</a>.</li><li><a href="{href(locale,'getting-started.first-15-minutes')}">Complete the first 15-minute device</a>.</li><li><a href="{href(locale,'tutorials.first-logic')}">Create the first automation</a>.</li><li><a href="{href(locale,'cookbook')}">Build a practical project</a>.</li></ol><h2>Your first successful result</h2><p>The project should save without blocking validation, the wiring view should match the physical low-voltage connections, compilation should name the chosen board, and USB or OTA completion should identify the running device. Open the device web interface and confirm Wi-Fi, firmware version, and configured peripheral state.</p><h2>First checks when it does not work</h2><p>Verify the exact board, power and common ground, data-capable USB cable, 2.4 GHz Wi-Fi credentials, and the first Serial Monitor error. Do not connect mains loads, motors, pumps, heaters, or relay coils directly to GPIO.</p>''',
      "setup.overview":f'''<h2>Setup sequence</h2><ol><li>Select the exact board.</li><li>Add peripheral profiles and read their runtime-support banners.</li><li>Keep automatic GPIO assignment enabled where possible.</li><li>Review the wiring diagram and electrical limits.</li><li>Configure Wi-Fi, optional MQTT, and device identity.</li><li>Save before compiling.</li></ol><p>Use the <a href="{href(locale,'configuration.reference')}">configuration reference</a> for persisted fields and <a href="{href(locale,'safety')}">Safety</a> before connecting loads.</p><h2>What is saved</h2><p>The project stores identity, board, peripheral slots, GPIO bindings, network settings, Logics graph, groups, positions, and supported feature options. Compilation embeds project defaults; device-side settings can persist separately across application-only OTA updates.</p><h2>Before compilation</h2><p>Resolve every pin conflict and unsupported runtime capability. Confirm that wiring-only profiles are not expected to produce live values or actions, and save the configuration so the firmware and recreated web Logics view use the same graph.</p>''',
      "logics.connectors":connector_reference(),
      "logics.overview":f'''<h2>How a workflow runs</h2><p>Data connectors carry current values. White Flow connectors trigger actions. Groups define independently controllable automations with Play, Pause, and Stop. Save and compile to embed the supported graph; the device web interface recreates it and overlays live values.</p><h2>Learn in order</h2><ol><li><a href="{href(locale,'logics.thinking')}">Translate a real requirement into Flow and data</a>.</li><li><a href="{href(locale,'logics.connectors')}">Learn connector colors and compatibility</a>.</li><li><a href="{href(locale,'logics.state-timing')}">Use edges, state, and timing</a>.</li><li><a href="{href(locale,'building-devices')}">Combine several peripherals</a>.</li></ol>''',
      "setup.peripherals":'''<h2>Choose the exact hardware profile</h2><p>A profile declares signals, power rails, pin capabilities, editor fields, and any implemented firmware capabilities. A similarly named module may use another voltage, address, or pinout. Select the part printed on the module or its documented compatible profile.</p><h2>Procedure</h2><ol><li>Select the board first so GPIO validation uses the correct chip.</li><li>Add the peripheral in its Audio, Display, Sensor, Input, Control, Storage, Communication, Expansion, or Power group.</li><li>Read the runtime-support banner. Wiring-only means the editor can reserve and draw pins but firmware does not yet operate that device.</li><li>Review every generated connection and supply rail.</li></ol><h2>Example and mistakes</h2><p>For a relay, select its real profile, assign a safe output GPIO, confirm active-high or active-low behavior, and use an external driver when the board cannot drive the coil. Do not treat a wiring profile as proof of runtime support, substitute a 5 V signal without level shifting, or ignore a GPIO conflict.</p>''',
      "setup.gpio":'''<h2>How assignment works</h2><p>ELMA-IoT combines board metadata with every selected peripheral signal. Automatic assignment excludes reserved, boot, flash, USB, input-only, occupied, and capability-incompatible pins. Manual selection remains project-specific and is validated before compilation.</p><h2>Procedure</h2><ol><li>Keep automatic assignment enabled for the first build.</li><li>Open the wiring diagram and locate each logical signal.</li><li>Change one pin at a time, then resolve every warning.</li><li>Use the safety override only after checking the board schematic and boot requirements.</li></ol><h2>Example and mistakes</h2><p>An I2S amplifier needs compatible BCLK, WS, and data-output pins; a battery divider needs ADC input. Avoid sharing a pin between unrelated peripherals, using a flash pin, driving an input-only pin, or assuming GPIO numbering matches a connector’s physical position.</p>''',
      "graphic-designer":'''<h2>Purpose</h2><p>The Graphic Designer turns the saved board, peripherals, bindings, and GPIO assignments into a wiring view. It is a review tool: positions and labels can change without changing electrical behavior, while pin reassignment changes the compiled configuration.</p><h2>Use it</h2><ol><li>Add peripherals in Configuration.</li><li>Open the diagram, fit all, and inspect every wire from board to module.</li><li>Drag items and labels to remove overlaps; rotate supported board art when useful.</li><li>Compare signal names, VCC, voltage, and ground against the physical module.</li></ol><h2>Common mistakes</h2><p>Do not interpret a clean diagram as electrical approval. Check current, voltage, pull resistors, common ground, motor or relay drivers, and manufacturer pinouts before applying power.</p>''',
      "wifi":'''<h2>Station and fallback access point</h2><p>Station mode joins the configured network. AP fallback can keep the device reachable when station connection fails. Static addressing requires an address, gateway, subnet, and suitable DNS values for that network.</p><h2>Procedure</h2><ol><li>Enter the SSID exactly, including case.</li><li>Enter the password and leave static IP disabled for the first test.</li><li>Compile or apply configuration, then read the reported IP in the completion view or Serial Monitor.</li><li>Enable a static address only after reserving it outside the DHCP pool or in the router.</li></ol><h2>Common mistakes</h2><p>ESP targets commonly require 2.4 GHz Wi-Fi. Wrong credentials, client isolation, captive portals, weak signal, an address conflict, or a phone on another network can make a running device appear unreachable.</p>''',
      "audio.overview":'''<h2>Audio path</h2><p>Audio Out selects an amplifier, DAC, codec, or buzzer profile and its output pins. Audio In selects a microphone or codec input. Logics audio source blocks describe a file, melody, or supported offline TTS source; an action or peripheral Play block receives Flow to start it.</p><h2>Procedure</h2><ol><li>Select the exact Audio Out profile and verify BCLK, WS, DIN/DOUT, or buzzer GPIO roles.</li><li>Add storage when a file source needs it.</li><li>Build the source chain, then connect Flow to Play.</li><li>Test at low volume with a correctly powered amplifier and speaker.</li></ol><h2>Limits and mistakes</h2><p>Offline TTS currently supports its documented English input and sounds synthetic; rate, pitch, and intonation alter delivery but do not turn it into a neural voice. Do not drive a speaker directly from GPIO or assume every codec uses the same I2C address and I2S pin direction.</p>''',
      "flash.ota":"<h2>Before updating</h2><p>The device must be reachable over HTTP, identify as compatible ELMA firmware or pass the explicit migration checks, match the compiled chip, and have an OTA-capable partition layout. Keep power stable until restart completes.</p><h2>Procedure</h2><ol><li>Compile for the exact board and configuration.</li><li>Discover the device or enter its current IP and credentials.</li><li>Review compatibility details before sending.</li><li>Wait for upload, verification, reboot, and reachability checks.</li></ol><h2>Common mistakes</h2><p>Do not send an image for another chip, interrupt power, close the operation during transfer, or assume that a ping alone proves ELMA OTA compatibility. If discovery fails, check HTTP reachability, Wi-Fi isolation, address changes, and the device Info page.</p>",
      "flash.usb":"<h2>Safe sequence</h2><p>Select the correct serial device, enter download mode if requested, write and verify all required regions, then allow the application to restart and acknowledge configuration. A verified image without configuration acknowledgement should be reconnected and checked rather than assumed complete.</p><h2>Procedure</h2><ol><li>Use a data-capable USB cable and select the correct port.</li><li>Compile for the exact board and chip.</li><li>Follow BOOT/RESET instructions if automatic download mode is unavailable.</li><li>Keep the cable attached through MD5 verification, restart, and configuration acknowledgement.</li></ol><h2>Common mistakes</h2><p>Charge-only cables, wrong ports, another program holding serial, unstable hubs, missing drivers, and incorrect boot mode are common causes. A successful write does not confirm that an incompatible pin configuration will boot safely.</p>",
      "mqtt.overview":f'''<h2>Start here</h2><p><strong>Topic</strong> is the destination. <strong>Retained</strong> keeps the latest payload. <strong>QoS 1</strong> requests at-least-once delivery and can duplicate a message. A queued publish is not broker acknowledgement.</p><p>Read the complete <a href="{href(locale,'mqtt.guide')}">MQTT guide</a>, <a href="{href(locale,'home-assistant')}">Home Assistant discovery guide</a>, and <a href="{href(locale,'troubleshooting.mqtt')}">MQTT troubleshooting</a>.</p><h2>Minimal connection</h2><p>Enter broker host and port, optional username/password, a unique client ID, and a base topic. Test from the application, compile or apply the settings, then confirm the device reports MQTT connected. Repeated connect/disconnect usually indicates duplicate client IDs, authentication, broker policy, or unstable networking.</p><h2>Publishing example</h2><p>Use a Flow trigger such as Timer or Rising Edge to execute MQTT Publish. Supply the exact topic, text, optional appended live value, separator, retain flag, and QoS. A sensor value connection alone does not schedule periodic publishing.</p>''',
      "troubleshooting":f'''<h2>Choose the symptom</h2><ul><li><a href="{href(locale,'troubleshooting.wifi')}">Wi-Fi, IP, and reachability</a></li><li><a href="{href(locale,'troubleshooting.mqtt')}">MQTT connection, commands, and discovery</a></li><li><a href="{href(locale,'troubleshooting.hardware')}">Sensors, ADC, relays, I2C, and motors</a></li><li><a href="{href(locale,'troubleshooting.compile')}">Compilation and validation</a></li><li><a href="{href(locale,'troubleshooting.usb')}">USB flashing</a></li><li><a href="{href(locale,'troubleshooting.ota')}">OTA updates</a></li></ul><p>Capture the first error and relevant Serial Monitor lines. Remove passwords, tokens, and private network details before sharing logs.</p><h2>A repeatable diagnostic method</h2><ol><li>State the expected and actual behavior.</li><li>Reduce the project to the smallest failing board, peripheral, or graph.</li><li>Record versions, GPIO assignments, power arrangement, and the first error.</li><li>Change one variable, retest, and keep the result.</li></ol><h2>Safety during diagnosis</h2><p>Disconnect mains and high-current loads before rewiring. Test logic with a safe indicator or meter first, and do not bypass boot-pin, voltage, current, driver, or isolation requirements to make an error disappear.</p>''',
      "compile":'''<h2>What compilation does</h2><p>The compiler validates the board, GPIO assignments, peripheral profiles, Logics graph, and feature selections, then generates the firmware image and embedded project defaults. Unsupported runtime capabilities remain blocking errors rather than silent no-ops.</p><h2>Procedure</h2><ol><li>Save the project and resolve every red validation message.</li><li>Confirm the target board and selected peripherals.</li><li>Compile and keep the complete technical log.</li><li>Flash only the image produced for that target.</li></ol><h2>Common mistakes</h2><p>Do not dismiss the first compiler error, reuse an image after changing boards, or expect configuration-only profiles to gain drivers during compilation. Network downloads may be required only when a toolchain or library is not already cached.</p>''',
      "serial-monitor":'''<h2>What to look for</h2><p>The Serial Monitor shows application boot and runtime output from the selected USB serial interface. Useful lines include reset reason, flash/partition status, settings source, Wi-Fi state and IP, MQTT errors, peripheral initialization, and configuration acknowledgement.</p><h2>Procedure</h2><ol><li>Connect the data USB cable and select the correct port.</li><li>Open the monitor before resetting the board when diagnosing boot.</li><li>Capture the first failure and several lines before and after it.</li><li>Close the monitor before flashing if the serial port cannot be shared.</li></ol><h2>Common mistakes</h2><p>Wrong baud or port produces unreadable or unrelated output. Very early ROM text and the last panic bytes can be missed when the connection opens late. Remove passwords and private addresses before sharing logs.</p>''',
      "web-interface":'''<h2>What runs on the device</h2><p>The responsive web interface reports live device status and exposes only features compiled for that firmware: configuration, Wi-Fi, MQTT, audio, displays, storage, motor controls, logs, firmware actions, and the embedded Logics graph where applicable.</p><h2>Using it</h2><ol><li>Open the current device IP on the same reachable network.</li><li>Use the top instrument icons to select a section.</li><li>Review live values before applying changes.</li><li>Save persistent changes and confirm that the device reports success.</li></ol><h2>Common mistakes</h2><p>A browser form value is not active until the device accepts it. Old saved preferences can intentionally survive an application-only OTA; use the supported configuration apply or erase workflow when replacing them. Online Help links require Internet, but device control remains local.</p>''',
      "troubleshooting.compile":'''<h2>Diagnose from the first error</h2><p>Start at the first validation or compiler error; later lines are often consequences. Identify whether it names a GPIO conflict, unsupported Logic capability, missing toolchain/library, memory overflow, malformed configuration, or filesystem permission.</p><h2>Corrective steps</h2><ol><li>Save the project to a writable local folder.</li><li>Resolve editor validation before retrying.</li><li>Confirm board and chip, then retry once with the complete log.</li><li>Clear only the documented build cache when the log identifies stale artifacts.</li></ol><h2>Do not</h2><p>Do not delete arbitrary compiler bundles, disable GPIO safety, or replace source libraries merely to hide an error. Preserve the first error and version information when reporting a reproducible failure.</p>''',
      "troubleshooting.usb":'''<h2>Symptoms and causes</h2><p>No port usually means cable, permission, driver, connector, or hardware trouble. Failure to enter bootloader points to BOOT/RESET timing or a busy port. Write or verification failures often indicate power, signal integrity, flash mode, or wrong target.</p><h2>Diagnostic steps</h2><ol><li>Try a known data cable and direct USB port.</li><li>Close Serial Monitor and other serial programs.</li><li>Reconnect, rescan, and select the port by its description.</li><li>Follow the board-specific download-mode sequence.</li><li>Keep power stable through verification and reboot.</li></ol><h2>After a successful write</h2><p>If configuration is not acknowledged, reconnect and apply configuration instead of reflashing repeatedly. Read Serial Monitor for reset loops, pin conflicts, or power faults.</p>''',
      "troubleshooting.ota":'''<h2>Separate discovery from compatibility</h2><p>A device can answer ping yet reject OTA, and discovery can fail while manual HTTP access works. Check the device web page, Info version/chip, credentials, OTA partition support, and whether the phone or PC can reach the same subnet.</p><h2>Diagnostic steps</h2><ol><li>Open the device IP in a normal browser.</li><li>Confirm its ELMA identity and chip family.</li><li>Enter the IP manually if multicast discovery is blocked.</li><li>Compile the correct target and retry with stable power.</li></ol><h2>Common causes</h2><p>Client isolation, changed DHCP address, authentication, legacy firmware endpoints, insufficient OTA partition space, an image for another chip, or a reboot during transfer can stop the update. USB recovery may be required for firmware without compatible OTA support.</p>''',
      "faq":'''<h2>Where should a beginner start?</h2><p>Complete the First 15 Minutes guide, then build the first Logics automation. Select hardware profiles by exact module, keep automatic GPIO assignment enabled, and verify the generated wiring before power.</p><h2>Why can two connectors not join?</h2><p>Direction and type must be compatible. Flow triggers actions; Boolean carries true/false; numeric, text, peripheral, path, and audio connectors have distinct meanings. Required ports must be wired.</p><h2>Why did a saved setting not change behavior?</h2><p>Confirm that Save or Apply succeeded, persistence storage was available, and the changed value belongs to the active graph/configuration. Application-only OTA can retain previous preferences by design.</p><h2>How do I request help?</h2><p>Include application and firmware versions, board, exact peripheral profile, first error, relevant sanitized logs, and a small graph or screenshot that reproduces the issue.</p>''',
      "about":'''<h2>What ELMA-IoT provides</h2><p>ELMA-IoT combines board and peripheral configuration, GPIO validation, wiring visualization, visual Logics, firmware compilation, USB and OTA flashing, MQTT, device monitoring, audio, displays, and a responsive device web interface.</p><h2>Documentation contract</h2><p>Applications and firmware keep stable help IDs and open this public online source. Detailed prose and screenshots are not stored in firmware, preserving flash and OTA headroom. Every registered block, peripheral, and board receives a stable route.</p><h2>Accuracy and privacy</h2><p>Reference content is generated from a sanitized feature catalog and reviewed against implementation. Documentation does not contain private repositories, signing material, credentials, user configurations, or compiler artifacts. Report documentation issues from the link at the bottom of each article.</p>''',
      "peripheral.voltage-divider":'''<h2>Purpose</h2><p>A voltage divider scales a measured voltage into the ESP ADC range. ELMA-IoT uses the configured resistor values, ADC pin, calibration multiplier, maximum input, averaging window, and update interval to report battery voltage and percentage where the firmware profile supports it.</p><h2>Wiring and calculation</h2><p>Connect R1 from the measured positive voltage to the ADC junction and R2 from that junction to ground; join grounds. The ideal junction voltage is Vin × R2 ÷ (R1 + R2). It must remain below the board ADC limit at the highest possible Vin.</p><h2>Configuration and test</h2><ol><li>Select the exact board and voltage-divider sensor profile.</li><li>Enter actual resistor values and maximum input voltage.</li><li>Choose an ADC-capable pin.</li><li>Compare the displayed result with a trusted meter and adjust only the calibration multiplier.</li></ol><h2>Common mistakes</h2><p>Never exceed ADC voltage, omit common ground, use resistor labels instead of measured values when precision matters, or expect ADC readings to be perfectly linear and noise-free. Use averaging and safe source impedance appropriate to the board.</p>''',
      "home":'''<h2>Choose a path</h2><p>New users should follow Getting Started and the First 15 Minutes tutorial. Use Setup and Reference for board, GPIO, peripheral, and configuration details; Logics for automation blocks and connectors; Tutorials and the Project Cookbook for complete builds; and Troubleshooting when a result differs from the expected behavior.</p><h2>How the help stays accurate</h2><p>Stable help IDs connect Android, Windows, and device firmware to this site. Generated node, peripheral, and board references come from a sanitized catalog, while tutorials explain verified workflows and clearly mark configuration-only profiles or unsupported runtime behavior.</p>''',
    }
    body=details.get(hid)
    if not body:raise ValueError(f'Missing detailed topic body: {hid}')
    return f'<p class="lead">{esc(t["summary"])}</p>{body}'

def connector_reference():
    descriptions={"execution":"White Flow pulses start actions; they do not carry a sensor value.","boolean":"True/False conditions. Use an edge or branch to turn a condition into Flow.","integer":"Whole numbers.","number":"Floating-point or compatible integer/analog values.","analog":"Measured numeric values from ADC-style inputs.","string":"Text values.","scalar":"Accepts a number, integer, analog, Boolean, or text value.","peripheral":"A configured hardware reference used by generic actions.","path":"A stored file/path source; it can feed compatible audio input.","audio":"An audio source description; a separate Flow trigger starts playback."}
    rows=[[pill(k),f'<span class="swatch" style="--type:{v}"></span>{v}',esc(descriptions[k])] for k,v in TYPE_COLORS.items()]
    return '<h2>Connector colors and meaning</h2>'+table(["Type","Color","Meaning"],rows)+'<h2>Direction and inline values</h2><p>Outputs face away from their block and connect to inputs. Required inputs must be wired. Optional inputs can use stored inline values; after wiring, the connected live value overrides the stored default. EN/Enabled is Boolean gating. Invalid type combinations are rejected.</p>'

def tutorial_body(t):
    prerequisites=t.get("prerequisites",["A saved ELMA-IoT project","The target board and hardware available for verification"])
    checks=t.get("verify",["The project saves without a blocking validation error.","The device performs the intended action using the configured pins and values."])
    return f'''<p class="lead">{esc(t["why"])}</p>
<aside class="tutorial-goal"><strong>Goal:</strong> {esc(t.get("goal",t["why"]))}</aside>
<h2>Before you start</h2><ul>{''.join(f'<li>{esc(x)}</li>' for x in prerequisites)}</ul>
<h2>Step-by-step</h2><ol class="tutorial-steps">{''.join(f'<li><strong>Step {i}</strong><p>{esc(x)}</p></li>' for i,x in enumerate(t["steps"],1))}</ol>
<h2>Why this workflow is arranged this way</h2><p>{esc(t.get("explanation",t["why"]))}</p>
<h2>What to verify</h2><ul>{''.join(f'<li>{esc(x)}</li>' for x in checks)}</ul>
<p>Save the project after verification. The feature articles under Related topics explain connector types, pin restrictions, and flashing requirements in more detail.</p>'''

def guide_body(item,locale):
    def replace(match): return f'<a href="{href(locale,match.group(1))}">{esc(match.group(2))}</a>'
    raw=''.join(item["body"]) if isinstance(item["body"],list) else item["body"]
    return re.sub(r'\[\[([a-z0-9.-]+)\|([^\]]+)\]\]',replace,raw)

def tutorials_index(locale):
    cards=[]
    for i,t in enumerate(TUTORIALS,1):
        features=TUTORIAL_SCREENSHOTS.get(t["id"],[])
        shot=screenshot(locale,features[0]) if features else None
        thumb=f'<img src="{BASE}/{esc(shot["path"])}" alt="{esc(t["title"])} tutorial screenshot" loading="lazy">' if shot else ''
        cards.append(f'''<a class="tutorial-card" href="{href(locale,"tutorials."+t["id"])}">{thumb}<span class="tutorial-card-copy"><small>Tutorial {i}</small><strong>{esc(t["title"])}</strong><span>{esc(t["why"])}</span><b>{len(t["steps"])} guided steps →</b></span></a>''')
    return f'''<h2>How to use these tutorials</h2><p class="lead">Choose a tutorial below. Each guide explains what to do, why the step matters, what to verify, and shows current ELMA-IoT screens where they are relevant.</p>
<div class="tutorial-summary"><strong>{len(TUTORIALS)} tutorials</strong><span>Setup · GPIO · Logics · MQTT · displays · audio · compile · USB · OTA · diagnostics</span></div>
<h2>All step-by-step tutorials</h2><div class="tutorial-list">{''.join(cards)}</div>'''

def nav_tree(locale,active,all_titles):
    def link(help_id,label=None):
        current=' aria-current="page"' if help_id==active else ''
        return f'<a href="{href(locale,help_id)}"{current}>{esc(label or all_titles.get(help_id,help_id))}</a>'
    def branch(label,links,opened=False,extra=''):
        return f'<details {"open" if opened else ""}><summary>{esc(label)}</summary><div class="tree-children">{"".join(link(x,y) for x,y in links)}{extra}</div></details>'
    getting=[("getting-started","Overview"),("getting-started.architecture","How ELMA-IoT works"),("getting-started.installation","Install and prepare"),("getting-started.first-15-minutes","First 15 minutes"),("tutorials.first-esp-project","First ESP project"),("tutorials.select-esp-board","Select a board"),("tutorials.add-peripherals","Add peripherals"),("tutorials.wiring-diagram","Read the wiring diagram")]
    setup=[("setup.overview","Setup overview"),("setup.peripherals","Peripherals"),("setup.gpio","GPIO configuration"),("graphic-designer","Graphic Designer"),("configuration.reference","Configuration reference"),("reference.electronics-basics","Electronics basics"),("safety","Safety"),("wifi","Wi-Fi"),("mqtt.guide","MQTT guide"),("audio.overview","Audio")]
    logics=[("logics.overview","Logics overview"),("logics.thinking","How to think about Logics"),("logics.connectors","Connector types and colors"),("logics.state-timing","State and timing"),("building-devices","Combining peripherals"),("tutorials.first-logic","First automation")]
    tutorials=[("tutorials","All tutorials")]+[("tutorials."+x["id"],x["title"]) for x in TUTORIALS]
    cookbook=[("cookbook","All projects"),("cookbook.basic-patterns","Basic patterns"),("cookbook.control-systems","Lighting, gate, and alarms"),("cookbook.thermostat","Thermostat"),("cookbook.water-system","Water system"),("cookbook.drv8833","DRV8833 motor"),("cookbook.mini-piano","Mini piano"),("faq.practical-projects","Practical FAQ")]
    troubleshooting=[("troubleshooting","All troubleshooting"),("troubleshooting.wifi","Wi-Fi and reachability"),("troubleshooting.mqtt","MQTT"),("troubleshooting.hardware","Sensors and actuators"),("troubleshooting.compile","Compilation"),("troubleshooting.usb","USB flashing"),("troubleshooting.ota","OTA updates"),("tutorials.compile-troubleshooting","Compilation tutorial"),("tutorials.usb-troubleshooting","USB tutorial"),("tutorials.ota-troubleshooting","OTA tutorial")]
    categories={}
    for node in CAT["nodes"]: categories.setdefault(node["category"],[]).append((node["helpId"],node["title"]))
    block_tree='<details class="nested"><summary>All Logics blocks</summary><div class="tree-children">'+''.join(branch(category,items,active in {x for x,_ in items}) for category,items in sorted(categories.items()))+'</div></details>'
    return '<nav class="doc-tree"><strong>Contents</strong>'+branch("Getting started",getting,active.startswith("getting-started"))+branch("Setup and reference",setup,active.startswith("setup.") or active.startswith("configuration.") or active.startswith("reference.") or active in {"graphic-designer","wifi","mqtt.guide","audio.overview","safety"})+branch("Logics",logics,active.startswith("logics.") or active=="building-devices",block_tree)+branch("Tutorials",tutorials,active=="tutorials" or active.startswith("tutorials."))+branch("Project cookbook",cookbook,active=="cookbook" or active.startswith("cookbook."))+branch("Troubleshooting",troubleshooting,active.startswith("troubleshooting."))+"</nav>"

def related_for(item,kind):
    if item.get("related"): return item["related"]
    if kind=="node":
        category=item["category"]
        related=[n["helpId"] for n in CAT["nodes"] if n["category"]==category and n["helpId"]!=item["helpId"]][:4]
        if any(p["type"] in ("execution","boolean","scalar") for p in item["ports"]): related.insert(0,"logics.connectors")
        return related[:5]
    if kind=="peripheral":
        peers=[p["helpId"] for p in CAT["peripherals"] if p["group"]==item["group"] and p["helpId"]!=item["helpId"]][:3]
        return ["setup.peripherals","setup.gpio",*peers]
    if kind=="board": return ["setup.gpio","setup.peripherals","flash.usb","flash.ota"]
    return ["getting-started","tutorials","troubleshooting"]

def page(locale,item,kind,all_titles):
    ui={**UI["en"],**UI.get(locale,{})}; help_id=item["helpId"]; title=item["title"]
    body=node_body(item) if kind=="node" else peripheral_body(item) if kind=="peripheral" else board_body(item) if kind=="board" else tutorial_body(item) if kind=="tutorial" else guide_body(item,locale) if kind=="guide" else tutorials_index(locale) if item["helpId"]=="tutorials" else generic_body(item,locale)
    related=related_for(item,kind)
    selected=[s for s in SCREENSHOTS if s['helpId']==help_id and s.get('locale','en')==locale]
    if kind=="tutorial": selected=[screenshot(locale,x) for x in TUTORIAL_SCREENSHOTS.get(item["id"],[]) if screenshot(locale,x)]
    if kind=="guide": selected=[screenshot(locale,x) for x in GUIDE_SCREENSHOTS.get(help_id,[]) if screenshot(locale,x)]
    if not selected:
        feature="blueprint-logics-canvas" if kind=="node" else "peripheral-selection" if kind=="peripheral" else "board-selection" if kind=="board" else "instrument-panel"
        selected=[screenshot(locale,feature)] if screenshot(locale,feature) else []
    figure_cards=''.join(f'<figure><a href="{BASE}/{esc(s["path"])}" target="_blank" rel="noopener"><img src="{BASE}/{esc(s["path"])}" alt="Current {esc(s["platform"])} {esc(s["feature"].replace("-"," "))} screen" loading="lazy"></a><figcaption>{esc(s["platform"])} {esc(s["applicationVersion"])} · {esc(s["feature"].replace("-"," "))} · captured {esc(s["capturedAt"])} · select to open full size</figcaption></figure>' for s in selected)
    figures=f'<section class="screenshot-section" id="screenshots"><h2>Current application screenshots</h2><div class="screenshot-gallery">{figure_cards}</div></section>' if figure_cards else ''
    rel=''.join(f'<li><a href="{href(locale,x)}">{esc(all_titles.get(x,x))}</a></li>' for x in related if x in all_titles)
    options=''.join(f'<option value="{esc(code)}" {"selected" if code==locale else ""}>{esc(LOCALE_NAMES[code])}</option>' for code in CAT["locales"])
    fallback='' if locale=="en" or TRANSLATIONS.get(locale) else f'<aside class="fallback">{esc(ui["fallback"])}</aside>'
    issue=f'https://github.com/elma-iot/elma-iot-docs/issues/new?title=Documentation%3A%20{help_id}'
    return f'''<!doctype html><html lang="{locale}" dir="{'rtl' if locale in RTL else 'ltr'}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)} · ELMA-IoT Help</title><meta name="description" content="{esc(item.get('summary',item.get('purpose','ELMA-IoT documentation')))}"><link rel="stylesheet" href="{BASE}/assets/site.css"></head><body data-locale="{locale}" data-help-id="{esc(help_id)}"><header><a class="brand" href="{BASE}/{locale}/">ELMA-IoT Help</a><input id="search" type="search" placeholder="{esc(ui['search'])}" autocomplete="off"><select id="locale" aria-label="Language">{options}</select></header><div id="results" hidden></div><main>{nav_tree(locale,help_id,all_titles)}<article>{fallback}<p class="eyebrow">{esc(help_id)}</p><h1>{esc(title)}</h1><p class="version">{esc(ui['applies'])}: Android {CAT['appliesTo']['android']} · Windows {CAT['appliesTo']['windows']} · Firmware {CAT['appliesTo']['firmware']}</p>{body}{figures}<h2>{esc(ui['related'])}</h2><ul>{rel}</ul><footer><strong>{esc(ui['helpful'])}</strong> <a href="{issue}">{esc(ui['report'])}</a>. No usage telemetry is collected.</footer></article></main><script src="{BASE}/assets/site.js"></script></body></html>'''

def home(locale,items):
    source=[*items,*GUIDES]
    cards=''.join(f'<a class="card" href="{href(locale,x["helpId"])}"><strong>{esc(x["title"])}</strong><span>{esc(x.get("summary","Open documentation"))}</span></a>' for x in source if x["helpId"] in ("getting-started.first-15-minutes","getting-started.architecture","setup.overview","graphic-designer","logics.thinking","mqtt.guide","cookbook","flash.usb","tutorials","troubleshooting"))
    return page(locale,{"helpId":"home","title":"ELMA-IoT online documentation","summary":"One public source for ELMA-IoT setup, Logics, hardware, flashing, tutorials, and troubleshooting."},"generic",{"getting-started":"Getting started","tutorials":"Tutorials","troubleshooting":"Troubleshooting"}).replace('<h2>Choose a path</h2>',f'<div class="cards">{cards}</div><h2>Choose a path</h2>')

def main():
    if OUT.exists(): shutil.rmtree(OUT)
    items=[]
    items += [(x,"generic") for x in TOPICS]
    items += [(x,"guide") for x in GUIDES]
    items += [({"helpId":"tutorials."+x["id"],"title":x["title"],"summary":x["why"],**x},"tutorial") for x in TUTORIALS]
    items += [(x,"node") for x in CAT["nodes"]]
    items += [(x,"peripheral") for x in CAT["peripherals"]]
    items += [(x,"board") for x in CAT["boards"]]
    titles={x["helpId"]:x["title"] for x,_ in items}; titles.update({"getting-started":"Getting started","tutorials":"Tutorials","troubleshooting":"Troubleshooting"})
    for locale in CAT["locales"]:
        write(OUT/locale/"index.html",localize_document(home(locale,TOPICS),locale))
        search=[]
        for item,kind in items:
            write(OUT/locale/route(item["helpId"])/"index.html",localize_document(page(locale,item,kind,titles),locale))
            search_values=[item.get("summary",""),item.get("purpose",""),item.get("example",""),*item.get("aliases",[])]
            search.append({"title":localized_text(locale,item["title"]),"helpId":item["helpId"],"url":href(locale,item["helpId"]),"text":" ".join(localized_text(locale,x) for x in search_values if x)})
        write(OUT/"assets"/"search"/(locale+".json"),json.dumps(search,ensure_ascii=False))
    root='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ELMA-IoT Help</title><script>const s=["en","es","zh","hi","ar","pt","bn","ru","ja","de","fr","ko","tr","it","id","pl","uk","vi","th","fa"];let l=(navigator.language||"en").toLowerCase().split("-")[0];location.replace("'''+BASE+'''/"+(s.includes(l)?l:"en")+"/")</script></head><body><a href="'''+BASE+'''/en/">ELMA-IoT Help</a></body></html>'''
    write(OUT/"index.html",root); write(OUT/"404.html",root)
    shutil.copytree(ROOT/"assets",OUT/"assets",dirs_exist_ok=True)
    print(f"Built {len(items)} topics for {len(CAT['locales'])} locales ({len(items)*len(CAT['locales'])} routes)")

if __name__=="__main__": main()
