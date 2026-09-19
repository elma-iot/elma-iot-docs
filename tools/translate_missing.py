from __future__ import annotations

import json
import re
import os
import subprocess
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from translate_content import LOCALES, ROOT, TextCollector, polish

PROTECTED = sorted({
    "ELMA-IoT", "Android", "Windows", "Firmware", "ESP", "ESP32", "GPIO7", "GPIO",
    "MQTT", "Wi-Fi", "OTA", "USB", "ADC", "DAC", "PWM", "I2C", "SPI", "UART",
    "I2S", "CAN", "TWAI", "PSRAM", "QoS", "JSON", "HTML", "Home Assistant",
}, key=len, reverse=True)


def protect(text: str):
    values = []
    for token in PROTECTED:
        if token not in text:
            continue
        marker = f"ELMAPROTECTED{len(values)}X"
        text = text.replace(token, marker)
        values.append((marker, token))
    return text, values


def restore(text: str, values):
    for marker, token in values:
        text = re.sub(r"\s*" + re.escape(marker) + r"\s*", f" {token} ", text, flags=re.I)
    return re.sub(r"\s+([.,;:!?])", r"\1", re.sub(r"\s+", " ", text)).strip()


def translate_one(locale: str, source: str):
    prepared, values = protect(source)
    url = (
        "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl="
        + locale + "&q=" + urllib.parse.quote(prepared)
    )
    last_error = None
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "ELMA-IoT documentation builder"})
            result = json.loads(urllib.request.urlopen(request, timeout=30).read().decode("utf-8"))
            translated = result[0] if isinstance(result, list) else ""
            if not translated:
                raise RuntimeError("empty translation")
            return locale, source, polish(restore(translated, values), locale)
        except Exception as error:
            last_error = error
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{locale}: failed to translate {source!r}: {last_error}")


def main():
    collector = TextCollector()
    for page in (ROOT / "_site/en").rglob("*.html"):
        collector.feed(page.read_text(encoding="utf-8"))
    locale_dir = ROOT / "content/locales"
    mappings = {
        locale: json.loads((locale_dir / f"{locale}.json").read_text(encoding="utf-8"))
        for locale in LOCALES
    }
    old_keys = {}
    if os.environ.get("ELMA_REFRESH_NEW_TRANSLATIONS") == "1":
        for locale in LOCALES:
            previous = subprocess.check_output(
                ["git", "show", f"HEAD:content/locales/{locale}.json"], cwd=ROOT
            ).decode("utf-8")
            old_keys[locale] = set(json.loads(previous))
    tasks = [
        (locale, source)
        for locale in LOCALES
        for source in sorted(collector.values)
        if source not in mappings[locale] or (old_keys and source not in old_keys[locale])
    ]
    print(f"Translating {len(tasks)} missing localized strings")
    with ThreadPoolExecutor(max_workers=16) as pool:
        futures = [pool.submit(translate_one, *task) for task in tasks]
        for completed, future in enumerate(as_completed(futures), 1):
            locale, source, translated = future.result()
            mappings[locale][source] = translated
            if completed % 100 == 0:
                print(f"  {completed}/{len(tasks)}")
    for locale, mapping in mappings.items():
        (locale_dir / f"{locale}.json").write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
