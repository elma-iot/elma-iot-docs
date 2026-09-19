# Custom hardware documentation contract

Future Custom Hardware Constructor packages may reference online documentation with the same small contract used by built-in features:

```json
{
  "hardwareId": "vendor.example-sensor",
  "helpId": "custom.vendor.example-sensor",
  "documentation": {
    "title": "Example sensor",
    "description": "What the hardware does",
    "pins": [],
    "configuration": [],
    "logicCapabilities": [],
    "libraries": [],
    "limitations": [],
    "images": [],
    "examples": []
  }
}
```

The package owns hardware capabilities and the `helpId`; the public documentation build owns the rendered article and URL. Imported prose and metadata are untrusted. Validation rejects executable markup, remote scripts, event-handler attributes, unsafe URL schemes, duplicate IDs, and paths outside an approved asset directory. The renderer treats all prose as text, escapes HTML, permits only an explicit formatting allowlist, and copies images only after MIME, size, and filename checks.

Translations use locale-keyed prose with English as the required fallback. Technical IDs, pin capabilities, and schemas stay language-neutral. A future importer must validate against [the documentation-bundle schema](schema/custom-hardware-documentation.schema.json) before adding a topic to the generated catalog.
