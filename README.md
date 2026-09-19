# ELMA-IoT Documentation

This is the public, online-only user documentation for ELMA-IoT. Android, Windows, and the ESP web interface store only stable `helpId` references and open these pages in the default browser.

- [Getting Started](https://elma-iot.github.io/elma-iot-docs/en/getting-started/)
- [Visual Logics](https://elma-iot.github.io/elma-iot-docs/en/logics/overview/)
- [Tutorials](https://elma-iot.github.io/elma-iot-docs/en/tutorials/)
- [Troubleshooting](https://elma-iot.github.io/elma-iot-docs/en/troubleshooting/)

ELMA-IoT supports ESP32, ESP32-S3, and ESP32-C3 families, visual peripheral configuration, automatic GPIO assignment, firmware compilation, USB and OTA flashing, MQTT, audio, displays, device monitoring, and a visual automation runtime.

Documentation is generated from a sanitized feature catalog. It contains no application source, credentials, signing material, private configuration, or compiler artifacts.

## Development

```text
python tools/build_site.py
python tools/validate.py
```

CI validates help IDs, routes, internal links, locale fallbacks, screenshot metadata, and coverage before publishing GitHub Pages.

## Versions

Current documentation applies to ELMA-IoT Android 1.0.12+, Windows 0.1.56+, and firmware 0.1.53+, unless an article says otherwise.
