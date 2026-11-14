#!/usr/bin/env python3
"""Genere translations/harbour-audiobook-<langue>.ts a partir des fichiers QML
et de tools/catalog.py, puis les compile en .qm avec lrelease."""
import re, subprocess, sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from catalog import LANGS, T, BACKEND

pat = re.compile(r'qsTr\("((?:[^"\\]|\\.)*)"\)')
contexts = {}
for f in sorted((ROOT / "qml").rglob("*.qml")):
    for m in pat.finditer(f.read_text(encoding="utf-8")):
        contexts.setdefault(f.stem, [])
        if m.group(1) not in contexts[f.stem]:
            contexts[f.stem].append(m.group(1))
contexts["backend"] = list(BACKEND)
table = dict(T, **BACKEND)

missing = sorted({s for ss in contexts.values() for s in ss if s not in table})
if missing:
    sys.exit("Sans traduction : " + repr(missing))

out = ROOT / "translations"
out.mkdir(exist_ok=True)
for i, lang in enumerate(LANGS):
    xml = ['<?xml version="1.0" encoding="utf-8"?>', '<!DOCTYPE TS>',
           f'<TS version="2.1" language="{lang}" sourcelanguage="en">']
    for ctx, sources in contexts.items():
        xml.append(f"<context>\n    <name>{ctx}</name>")
        for s in sources:
            xml.append("    <message>\n"
                       f"        <source>{escape(s)}</source>\n"
                       f"        <translation>{escape(table[s][i])}</translation>\n"
                       "    </message>")
        xml.append("</context>")
    xml.append("</TS>\n")
    ts = out / f"harbour-audiobook-{lang}.ts"
    ts.write_text("\n".join(xml), encoding="utf-8")
    subprocess.run(["/usr/lib/qt5/bin/lrelease", "-silent", str(ts)], check=True)
print("contextes :", {k: len(v) for k, v in contexts.items()})
