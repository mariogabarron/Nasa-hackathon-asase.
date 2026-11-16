"""Regenerate the browser data bundle after editing the canonical reference JSON."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'frontend/data'
data=json.loads((root/'economic-references.json').read_text())
(root/'economic-references.js').write_text(
    '// Generated from economic-references.json; see Sources for provenance.\n'
    + 'const ECONOMIC_DATA = ' + json.dumps(data,ensure_ascii=False,indent=2) + ';\n'
)
