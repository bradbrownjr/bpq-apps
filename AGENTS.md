# Agent Instructions — bpq-apps

## Project Context
Text-based packet radio applications for BPQ32/LinBPQ nodes. All output is
plaintext over 1200-baud serial links — no color, no Unicode, no ANSI. Every
byte costs air time.

## Form Template Rules (apps/forms/*.frm)

- **NEVER use real-world examples** in `description` fields. No real callsigns,
  email addresses, phone numbers, ZIP codes, GPS coordinates, event IDs, grid
  squares, BBS addresses, or exercise names. Use generic placeholders or plain
  prose descriptions only.
- Keep descriptions short — they are printed to a 1200-baud terminal.
- Bump the form `version` field on every edit, and update `manifest.json` to match.

## Release Checklist

1. Edit form(s) or `forms.py`
2. `python3 -m py_compile apps/forms.py` — must exit 0
3. `python3 -c "import json; json.load(open('apps/forms/<file>.frm'))"` — validate JSON
4. Bump `VERSION` in `forms.py` (and docstring) if `forms.py` changed
5. Bump form `version` in `.frm` file if form changed
6. Update `apps/forms/manifest.json` to match new form version(s)
7. `git add` all changed files, `git commit`, `git push`

## Regenerating manifest.json

```bash
python3 -c "
import json, os
d = {f: json.load(open('apps/forms/'+f)).get('version','1.0')
     for f in sorted(os.listdir('apps/forms')) if f.endswith('.frm')}
d['arl_messages.json'] = 'data'
json.dump(d, open('apps/forms/manifest.json','w'), indent=2)
open('apps/forms/manifest.json','a').write('\n')
"
```
