# Agent Instructions — bpq-apps

This file is the shared memory for any AI assistant working on bpq-apps
(GitHub Copilot, Claude, etc.). It captures rules, gotchas, architecture facts,
and ALWAYS/NEVER directives so that context-window compaction never loses them.

---

## Always / Never Memory Protocol

- If the user says **"always"**, **"never"**, **"remember"**, or **"don't"**,
  treat it as a permanent rule and add it here immediately.
- If a rule is not written down here, assume it will be forgotten next session.
- Remove or update rules that turn out to be wrong rather than letting them stack.

---

## Project Context

Python applications for BPQ32/LinBPQ amateur radio packet nodes. Users connect
at **1200 baud over RF** using plain serial terminals. Output rules are strict:

- **ALWAYS** ASCII-only output — strict 7-bit ASCII. No Unicode, no UTF-8
  characters above 0x7F, no ANSI color/escape codes, no box-drawing characters,
  no emoji, no smart quotes, no em-dashes. Serial terminals cannot render them.
- **ALWAYS** assume a terminal width of 80 columns maximum.
- **ALWAYS** minimize output at startup — every printed line costs air time at
  1200 baud. Silence is golden.
- **NEVER** print redundant headers, logos, or banners when navigating within
  an app (e.g., loading a form after the menu).
- **ALWAYS** design for resilience — internet may be down during the exact
  emergency the operator needs the app. Graceful offline fallback is required.
- **NEVER** crash on a network timeout. Catch exceptions silently and continue
  with local data.

### Target Audience
Amateur radio operators, ARES/SKYWARN emergency communicators, and NTS traffic
handlers. Many users are elderly or operating under stress. UI must be simple,
linear, and forgiving. No assumed familiarity with computers beyond typing.

### Runtime Environment
- Python 3.5+ (some nodes run older Debian/Raspbian — no f-strings until 3.6,
  use `.format()`)
- BPQ32/LinBPQ on Linux (Raspberry Pi or similar low-power hardware)
- No pip, no virtualenv — stdlib only unless explicitly vendored
- `COLUMNS` env var may be set by BPQ for terminal width

---

## Architecture

```
apps/           Python applications (one file per app, self-contained)
apps/forms/     Form templates (*.frm JSON) + arl_messages.json data file
apps/forms/manifest.json   Single-file version index for all form templates
../linbpq/infile           BPQ message import target (written by forms.py)
```

### Self-Update Mechanism (all apps)
Each app fetches its own raw GitHub URL on startup, compares `VERSION`, and
does an atomic replace + `os.execv` restart. Form templates use `manifest.json`
(one HTTP request) to check all form versions instead of fetching each file.

- `GITHUB_RAW_URL` — raw.githubusercontent.com base path for forms
- `GITHUB_FORMS_URL` — GitHub Contents API (rate-limited, avoid for version checks)
- **ALWAYS** use `manifest.json` for form version checks, never the Contents API.

---

## ALWAYS / NEVER Rules

### Output & UX
- **ALWAYS** `clear_screen()` when entering a new view (form, menu).
- **NEVER** reprint the app header/logo when navigating within the app.
- **ALWAYS** show a separator line before and after the form title when entering
  a form (already implemented in `fill_form()` and `fill_strip_form()`).
- **NEVER** ask the user for the same piece of information twice in one form
  (e.g., state is already in City/State — don't add a separate State field).

### Form Templates (apps/forms/*.frm)
- **NEVER** put real-world examples in `description` fields — no real callsigns,
  email addresses, phone numbers, ZIP codes, GPS coordinates, event IDs, grid
  squares, BBS addresses, or exercise names. Use generic prose only.
- **ALWAYS** keep descriptions short — they are printed to a 1200-baud terminal.
- **ALWAYS** bump the form `version` field on every edit to that form.
- **ALWAYS** update `manifest.json` to match the new form version immediately.
- **NEVER** add a field that duplicates information already captured by another
  field in the same form.
- Field order must follow the natural paper form order (e.g., NTS address block:
  name → street → city/state → ZIP → phone → email).

### Python Code (apps/*.py)
- **ALWAYS** use `.format()` for string interpolation (not f-strings — 3.5 compat).
- **ALWAYS** use `urllib.request` — no `requests` library (stdlib only).
- **NEVER** store or transmit API keys, tokens, or credentials in source code.
- **ALWAYS** keep `VERSION = "x.y"` in the assignment and the module docstring in sync.
- **NEVER** use `time.sleep()` in the main interactive loop — packet users will disconnect.
- **ALWAYS** validate JSON form files with `python3 -m py_compile` + `json.load()`
  before committing.

### Security
- All GitHub fetches are unauthenticated (60 req/hr rate limit). Don't make
  N-per-form requests — use `manifest.json` for bulk version checks.
- **NEVER** write user input directly to the BPQ import file without sanitization.
- **NEVER** expose node filesystem paths in output visible to the end user.

---

## html-theme/ (nginx proxy theme)

Files in `html-theme/` are served to web browsers via the nginx reverse proxy.
Different rules from the Python apps — these target modern browsers, not serial terminals.

- **ALWAYS** use vanilla JS and CSS — no frameworks, no bundler, no `npm`. The
  deploy script does a plain `scp`; there is no build step.
- **NEVER** add external CDN dependencies. Everything must work from `/bpq-theme/`
  on the local host.
- **ALWAYS** keep all colours as CSS custom properties in the `:root { }` block
  at the top of `bpq-modern.css`. Never hardcode colours anywhere else in the file.
- **ALWAYS** add `[data-theme="dark"]` overrides alongside any new `@media
  (prefers-color-scheme: dark)` block so the manual toggle works too.
- **ALWAYS** update `NAV_GROUPS` in `bpq-terminal.js` if LinBPQ adds or renames
  nav links (match by `textContent`, case-insensitive).
- **NEVER** use `innerHTML` with unsanitised user data in `files-browser.html`.
  All filename/path values must pass through the `esc()` helper.
- **ALWAYS** test `sub_filter` injection by verifying the deployed page source
  contains `bpq-modern.css` after running `deploy-theme.sh`.
- When LinBPQ terminal selectors change, update `TERM_OUTPUT_SELECTORS` and
  `TERM_INPUT_SELECTORS` at the top of `bpq-terminal.js` — never bury selectors
  inside functions.

---

## Release Checklist

Every change to `forms.py` or any `.frm` file must follow this sequence:

1. Edit form(s) or `forms.py`
2. `python3 -m py_compile apps/forms.py` — must exit 0
3. `python3 -c "import json; json.load(open('apps/forms/<file>.frm'))"` — validate JSON
4. If `forms.py` changed: bump `VERSION = "x.y"` and the docstring `Version:` line
5. If a `.frm` changed: bump its `"version"` field
6. Update `apps/forms/manifest.json` to match all changed form versions
7. `git add` all changed files → `git commit` → `git push`
8. The node self-updates on the next user connection (VERSION comparison triggers it)

### Regenerating manifest.json from scratch

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
