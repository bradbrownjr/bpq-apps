#!/usr/bin/env python3
"""
Node Map TUI - a front end for nodemap.py
------------------------------------------
Full-screen menu for building a crawl and reviewing its results, so the
options can be picked from a list instead of assembled on a command line.

Built on stdlib curses. Nothing to install, and it runs on the Python 3.5
that ships with older Raspbian, which is what the packet nodes actually have.

This is a front end, not a replacement: every screen shows the equivalent
nodemap.py command, and anything done here can still be done from the shell.

Requires nodemap.py in the same directory.

Author: Brad Brown, KC1JMH
Version: 1.1
"""

__version__ = '1.1'

import curses
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NODEMAP = os.path.join(HERE, 'nodemap.py')
NODEMAP_JSON = os.path.join(HERE, 'nodemap.json')
OVERRIDES_JSON = os.path.join(HERE, 'nodemap-overrides.json')

MIN_WIDTH = 60
MIN_HEIGHT = 16


# ---------------------------------------------------------------------------
# curses helpers
# ---------------------------------------------------------------------------

def safe_addstr(win, y, x, text, attr=0):
    """Write text, clipped to the window.

    curses raises if anything reaches the bottom-right cell, and a sysop on a
    narrow SSH window is exactly the person who would hit that. Clipping here
    keeps every screen from having to think about it.
    """
    height, width = win.getmaxyx()
    if y < 0 or y >= height or x < 0 or x >= width:
        return
    space = width - x
    if space <= 0:
        return
    text = str(text)[:space]
    # The final cell of the final row cannot be written portably.
    if y == height - 1 and x + len(text) >= width:
        text = text[:width - x - 1]
    if not text:
        return
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass


class Theme(object):
    """Colour pairs, degrading to plain attributes on a mono terminal."""

    def __init__(self):
        self.ok = curses.A_NORMAL
        self.warn = curses.A_NORMAL
        self.bad = curses.A_NORMAL
        self.dim = curses.A_NORMAL
        self.title = curses.A_BOLD
        self.sel = curses.A_REVERSE
        if not curses.has_colors():
            return
        curses.start_color()
        try:
            curses.use_default_colors()
            background = -1
        except curses.error:
            background = curses.COLOR_BLACK
        curses.init_pair(1, curses.COLOR_GREEN, background)
        curses.init_pair(2, curses.COLOR_YELLOW, background)
        curses.init_pair(3, curses.COLOR_RED, background)
        curses.init_pair(4, curses.COLOR_CYAN, background)
        self.ok = curses.color_pair(1)
        self.warn = curses.color_pair(2)
        self.bad = curses.color_pair(3)
        self.dim = curses.color_pair(4)
        self.title = curses.color_pair(4) | curses.A_BOLD


def draw_chrome(win, theme, title, hint):
    """Title bar across the top, key hints across the bottom."""
    height, width = win.getmaxyx()
    win.erase()
    heading = ' nodemap {} '.format(title)
    safe_addstr(win, 0, 0, heading.ljust(width - 1), theme.title)
    safe_addstr(win, height - 1, 0, ' ' + hint, theme.dim)


def prompt_line(win, theme, label, initial=''):
    """Read a line of text on the bottom row. Returns None if cancelled.

    Hand-rolled rather than using curses.textpad so that Escape reliably
    cancels; textpad swallows it.
    """
    height, width = win.getmaxyx()
    buffer = list(initial)
    curses.curs_set(1)
    try:
        while True:
            shown = ''.join(buffer)
            field = '{} {}'.format(label, shown)
            safe_addstr(win, height - 1, 0, ' ' * (width - 1))
            safe_addstr(win, height - 1, 0, ' ' + field[:width - 2])
            win.move(height - 1, min(len(field) + 1, width - 2))
            win.refresh()
            key = win.getch()
            if key in (27,):                      # Escape
                return None
            if key in (10, 13, curses.KEY_ENTER):
                return ''.join(buffer).strip()
            if key in (curses.KEY_BACKSPACE, 127, 8):
                if buffer:
                    buffer.pop()
                continue
            if key == curses.KEY_RESIZE:
                continue
            if 32 <= key <= 126:
                buffer.append(chr(key))
    finally:
        curses.curs_set(0)


def confirm(win, theme, question):
    answer = prompt_line(win, theme, question + ' (y/N)')
    return bool(answer) and answer.strip().lower() in ('y', 'yes')


def show_message(win, theme, lines, title='Notice'):
    """Blocking message box drawn over the current screen."""
    while True:
        draw_chrome(win, theme, title, 'any key to continue')
        for index, line in enumerate(lines):
            safe_addstr(win, 2 + index, 2, line)
        win.refresh()
        key = win.getch()
        if key != curses.KEY_RESIZE:
            return


def pick_from_list(win, theme, title, rows, hint, empty_message):
    """Scrollable selector. Returns the chosen index, or None on quit.

    rows is a list of (text, attribute) pairs.
    """
    selected = 0
    top = 0
    while True:
        height, width = win.getmaxyx()
        body = max(1, height - 4)
        draw_chrome(win, theme, title, hint)
        if not rows:
            safe_addstr(win, 2, 2, empty_message, theme.dim)
            win.refresh()
            key = win.getch()
            if key in (ord('q'), 27):
                return None
            continue

        if selected < top:
            top = selected
        elif selected >= top + body:
            top = selected - body + 1

        for offset in range(body):
            index = top + offset
            if index >= len(rows):
                break
            text, attr = rows[index]
            marker = '>' if index == selected else ' '
            line = '{} {}'.format(marker, text)
            safe_addstr(win, 2 + offset, 1, line.ljust(width - 3),
                        theme.sel if index == selected else attr)
        if len(rows) > body:
            safe_addstr(win, height - 2, 2,
                        '{}-{} of {}'.format(top + 1, min(top + body, len(rows)),
                                             len(rows)), theme.dim)
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(rows) - 1, selected + 1)
        elif key == curses.KEY_NPAGE:
            selected = min(len(rows) - 1, selected + body)
        elif key == curses.KEY_PPAGE:
            selected = max(0, selected - body)
        elif key == curses.KEY_HOME:
            selected = 0
        elif key == curses.KEY_END:
            selected = len(rows) - 1
        elif key in (10, 13, curses.KEY_ENTER):
            return selected
        elif key in (ord('q'), 27):
            return None
        elif key == curses.KEY_RESIZE:
            continue
        else:
            return ('key', key, selected)


# ---------------------------------------------------------------------------
# data access
# ---------------------------------------------------------------------------

def load_json(path):
    try:
        with open(path, 'r') as handle:
            return json.load(handle)
    except (IOError, ValueError):
        return {}


def save_overrides(data):
    tmp = OVERRIDES_JSON + '.tmp'
    with open(tmp, 'w') as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write('\n')
    os.rename(tmp, OVERRIDES_JSON)


def run_command(win, argv, pause=True):
    """Drop out of curses, run nodemap.py, then come back.

    A crawl prints continuously for minutes and expects to prompt; trying to
    render that inside curses would be worse than simply handing the terminal
    over for the duration.
    """
    curses.endwin()
    print('')
    print('$ {}'.format(' '.join(argv)))
    print('')
    try:
        code = subprocess.call(argv)
    except OSError as exc:
        code = -1
        print('Failed to run: {}'.format(exc))
    if pause:
        print('')
        try:
            input('Press Enter to return to the menu... ')
        except (EOFError, KeyboardInterrupt):
            pass
    win.clear()
    win.refresh()
    return code


# ---------------------------------------------------------------------------
# crawl option form
# ---------------------------------------------------------------------------

class Option(object):
    """One configurable crawl option.

    kind is 'toggle', 'choice', 'number' or 'text'. Each knows how to render
    itself and how to turn itself into command-line arguments, which keeps the
    command preview honest - it is generated from the same objects the form
    edits, not written out separately and left to drift.
    """

    def __init__(self, key, label, kind, value=None, choices=None,
                 flag=None, help_text='', positional=False, colon_choice=False):
        self.key = key
        self.label = label
        self.kind = kind
        self.value = value
        self.choices = choices or []
        self.flag = flag
        self.help_text = help_text
        self.positional = positional
        # A 'choice' option normally renders as two argv tokens ("--mode
        # reaudit"). Some flags - --hf and --ip - take their mode as a colon
        # suffix on one token ("--hf:crawl") instead, so the choice needs to
        # know which shape to emit.
        self.colon_choice = colon_choice

    def display(self):
        if self.kind == 'toggle':
            return 'yes' if self.value else 'no'
        if self.value in (None, ''):
            return '(default)'
        return str(self.value)

    def args(self):
        if self.positional:
            return [str(self.value)] if self.value not in (None, '') else []
        if self.kind == 'toggle':
            return [self.flag] if self.value else []
        if self.value in (None, ''):
            return []
        if self.kind == 'choice' and self.value == self.choices[0]:
            return []                      # first choice is the default
        if self.kind == 'choice' and self.colon_choice:
            return ['{}:{}'.format(self.flag, self.value)]
        return [self.flag, str(self.value)]

    def cycle(self, step=1):
        if self.kind == 'toggle':
            self.value = not self.value
        elif self.kind == 'choice':
            index = self.choices.index(self.value) if self.value in self.choices else 0
            self.value = self.choices[(index + step) % len(self.choices)]
        elif self.kind == 'number':
            # Same left/right convention as every other option, so hop
            # count (and any other number field, e.g. timeout) doesn't need
            # the enter-to-type prompt just to bump the value by one.
            current = self.value if self.value is not None else 0
            self.value = max(0, current + step)

    def edit(self, win, theme):
        if self.kind in ('toggle', 'choice'):
            self.cycle()
            return
        entered = prompt_line(win, theme, '{}:'.format(self.label),
                              '' if self.value is None else str(self.value))
        if entered is None:
            return
        if entered == '':
            self.value = None
            return
        if self.kind == 'number':
            try:
                self.value = int(entered)
            except ValueError:
                show_message(win, theme, ['"{}" is not a number.'.format(entered)],
                             'Invalid')
            return
        self.value = entered


def build_options():
    """The crawl options, in the order a sysop actually decides them."""
    return [
        Option('hops', 'Max RF hops', 'number', 4, positional=True,
               help_text='0=local only, 1=direct neighbours, 4 is a sensible default'),
        Option('start', 'Start node', 'text', None, positional=True,
               help_text='Callsign to crawl from. Blank means this node.'),
        Option('mode', 'Crawl mode', 'choice', 'update',
               choices=['update', 'reaudit', 'new-only'], flag='--mode',
               help_text='update=skip known (fast), reaudit=refresh all, new-only=discover'),
        Option('resume', 'Resume unexplored', 'toggle', False, flag='--resume',
               help_text='Pick up the nodes an interrupted crawl never reached'),
        Option('overwrite', 'Overwrite (not merge)', 'toggle', False, flag='--overwrite',
               help_text='DANGER: discards existing map instead of merging into it'),
        Option('exclude', 'Exclusions file', 'text', None, flag='--exclude',
               help_text='Callsigns or a filename. Blank uses exclusions.txt if present.'),
        Option('timeout', 'Per-node timeout', 'number', None, flag='--timeout',
               help_text='Seconds. Blank = 360 + 240 per hop. Raise for slow paths.'),
        Option('hf', 'HF ports', 'choice', 'off', choices=['off', 'audit', 'crawl'],
               flag='--hf', colon_choice=True,
               help_text='off=skip; audit=list VARA/ARDOP/PACTOR contacts without '
                         'connecting; crawl=connect and fully crawl (slow, 300 baud)'),
        Option('ip', 'IP ports', 'choice', 'off', choices=['off', 'audit', 'crawl'],
               flag='--ip', colon_choice=True,
               help_text='off=skip; audit=list AXIP/Telnet contacts without connecting; '
                         'crawl=connect and fully crawl over IP'),
        Option('nolookup', 'Skip internet lookups', 'toggle', False, flag='--no-lookup',
               help_text='Do not geocode or look up callsigns to fill in locations'),
        Option('noignore', 'Keep retrying bad calls', 'toggle', False,
               flag='--no-auto-ignore',
               help_text='Flag corrupt callsigns but do not add them to the ignore list'),
        Option('verbose', 'Verbose output', 'toggle', False, flag='--verbose',
               help_text='Show every command and response'),
        Option('log', 'Log telnet traffic', 'toggle', False, flag='--log',
               help_text='Write telnet.log for troubleshooting'),
        Option('yes', 'Unattended', 'toggle', False, flag='--yes',
               help_text='Answer yes to everything. For cron. Needs user/pass set.'),
    ]


def command_for(options):
    argv = [sys.executable, NODEMAP]
    for option in options:
        if option.positional:
            argv.extend(option.args())
    for option in options:
        if not option.positional:
            argv.extend(option.args())
    return argv


def screen_crawl(win, theme):
    options = build_options()
    selected = 0
    while True:
        height, width = win.getmaxyx()
        draw_chrome(win, theme, 'crawl',
                    'up/down move  enter/space change  r run  q back')
        label_width = max(len(o.label) for o in options) + 2

        body = max(1, height - 8)
        top = max(0, min(selected - body + 1, len(options) - body))
        top = max(0, top)
        for offset in range(min(body, len(options))):
            index = top + offset
            option = options[index]
            marker = '>' if index == selected else ' '
            line = '{} {}{}'.format(marker, option.label.ljust(label_width),
                                    option.display())
            attr = theme.sel if index == selected else 0
            if option.key == 'overwrite' and option.value:
                attr = theme.bad if index != selected else attr
            safe_addstr(win, 2 + offset, 1, line.ljust(width - 3), attr)

        # Help for the highlighted option, then the command it all adds up to.
        safe_addstr(win, height - 5, 2, options[selected].help_text[:width - 4],
                    theme.dim)
        argv = command_for(options)
        preview = ' '.join(['nodemap.py'] + argv[2:])
        safe_addstr(win, height - 3, 2, 'Command:', theme.title)
        safe_addstr(win, height - 2, 2, preview[:width - 4], theme.ok)
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(options) - 1, selected + 1)
        elif key in (curses.KEY_LEFT, ord('h')):
            options[selected].cycle(-1)
        elif key in (curses.KEY_RIGHT, ord('l')):
            options[selected].cycle(1)
        elif key in (10, 13, curses.KEY_ENTER, ord(' ')):
            options[selected].edit(win, theme)
        elif key in (ord('r'), ord('R')):
            overwrite = [o for o in options if o.key == 'overwrite'][0]
            if overwrite.value and not confirm(
                    win, theme, 'Overwrite discards the existing map. Continue?'):
                continue
            run_command(win, argv)
        elif key in (ord('q'), 27):
            return
        elif key == curses.KEY_RESIZE:
            continue


# ---------------------------------------------------------------------------
# gridsquares
# ---------------------------------------------------------------------------

GRID_HELP = 'enter set grid  d clear  q back'


def screen_grids(win, theme):
    while True:
        data = load_json(NODEMAP_JSON)
        nodes = data.get('nodes', {})
        if not nodes:
            show_message(win, theme,
                         ['No nodemap.json yet.',
                          'Run a crawl first.'], 'gridsquares')
            return
        overrides = load_json(OVERRIDES_JSON)
        grids = overrides.get('grids', {})

        rows = []
        keys = []
        for callsign in sorted(nodes):
            node = nodes[callsign]
            grid = node.get('gridsquare') or (node.get('location') or {}).get('grid')
            source = node.get('location_source', '')
            manual = any(k.split('-')[0].upper() == callsign.split('-')[0].upper()
                         for k in grids)
            if grid:
                attr = theme.ok if manual else 0
                mark = 'manual' if manual else source
            else:
                attr = theme.warn
                mark = 'MISSING'
            city = (node.get('location') or {}).get('city') or ''
            rows.append(('{:<12} {:<8} {:<14} {}'.format(
                callsign, grid or '-', mark[:14], city), attr))
            keys.append(callsign)

        missing = sum(1 for c in keys
                      if not (nodes[c].get('gridsquare')
                              or (nodes[c].get('location') or {}).get('grid')))
        title = 'gridsquares ({} missing)'.format(missing) if missing else 'gridsquares'
        result = pick_from_list(win, theme, title, rows, GRID_HELP, 'No nodes.')
        if result is None:
            return
        if isinstance(result, tuple):
            _tag, key, index = result
            if key in (ord('d'), ord('D')):
                callsign = keys[index]
                if confirm(win, theme, 'Clear manual grid for {}?'.format(callsign)):
                    run_command(win, [sys.executable, NODEMAP, '--confirm-call', callsign],
                                pause=False)
                    # Remove the override directly; nodemap.py has no flag for it.
                    overrides = load_json(OVERRIDES_JSON)
                    for stored in list(overrides.get('grids', {})):
                        if stored.split('-')[0].upper() == callsign.split('-')[0].upper():
                            del overrides['grids'][stored]
                    save_overrides(overrides)
            continue

        callsign = keys[result]
        current = (nodes[callsign].get('gridsquare')
                   or (nodes[callsign].get('location') or {}).get('grid') or '')
        entered = prompt_line(win, theme,
                              'Gridsquare for {} (e.g. FN43vp):'.format(callsign),
                              current)
        if entered:
            code = run_command(win, [sys.executable, NODEMAP, '--set-grid', callsign, entered],
                               pause=False)
            if code != 0:
                show_message(win, theme,
                             ['nodemap.py rejected that gridsquare.'], 'Error')


# ---------------------------------------------------------------------------
# ignore list
# ---------------------------------------------------------------------------

IGNORE_HELP = 'enter restore as real  i ignore a call  q back'


def screen_ignored(win, theme):
    while True:
        overrides = load_json(OVERRIDES_JSON)
        ignore = overrides.get('ignore', {})
        data = load_json(NODEMAP_JSON)
        suspects = data.get('suspect_callsigns', {})

        rows = []
        keys = []
        for callsign in sorted(ignore):
            detail = ignore[callsign]
            extra = suspects.get(callsign, {})
            heard = extra.get('heard_by', '')
            rows.append(('{:<10} {:<22} {:<10} heard by {}'.format(
                callsign, str(detail.get('reason', ''))[:21],
                str(detail.get('source', ''))[:9], heard or '?'), theme.warn))
            keys.append(callsign)

        result = pick_from_list(
            win, theme, 'ignored callsigns ({})'.format(len(keys)), rows,
            IGNORE_HELP,
            'Nothing is being ignored. Corrupt callsigns land here after a crawl.')
        if result is None:
            return
        if isinstance(result, tuple):
            _tag, key, _index = result
            if key in (ord('i'), ord('I')):
                entered = prompt_line(win, theme, 'Callsign to ignore:')
                if entered:
                    run_command(win, [sys.executable, NODEMAP, '--ignore-call', entered.upper()],
                                pause=False)
            continue

        callsign = keys[result]
        if confirm(win, theme,
                   '{} is a real station and should be crawled?'.format(callsign)):
            run_command(win, [sys.executable, NODEMAP, '--confirm-call', callsign], pause=False)


# ---------------------------------------------------------------------------
# network overview
# ---------------------------------------------------------------------------

STATUS_ORDER = ['online', 'recent', 'stale', 'unreachable', 'offline', 'unknown']


def screen_nodes(win, theme):
    data = load_json(NODEMAP_JSON)
    nodes = data.get('nodes', {})
    if not nodes:
        show_message(win, theme, ['No nodemap.json yet.', 'Run a crawl first.'],
                     'nodes')
        return

    def rank(item):
        status = item[1].get('status', 'unknown')
        return (STATUS_ORDER.index(status) if status in STATUS_ORDER else 99,
                item[0])

    colours = {'online': theme.ok, 'recent': 0, 'stale': theme.warn,
               'offline': theme.bad, 'unreachable': theme.bad}
    rows = []
    keys = []
    for callsign, node in sorted(nodes.items(), key=rank):
        status = node.get('status', 'unknown')
        age = node.get('days_since_seen')
        grid = node.get('gridsquare') or (node.get('location') or {}).get('grid') or '-'
        rows.append(('{:<12} {:<11} {:<8} {:>5} d  {} nbrs'.format(
            callsign, status, grid,
            '{:.1f}'.format(age) if isinstance(age, (int, float)) else '-',
            len(node.get('neighbors') or [])), colours.get(status, 0)))
        keys.append(callsign)

    while True:
        result = pick_from_list(win, theme, 'nodes ({})'.format(len(keys)), rows,
                                'enter query node  q back', 'No nodes.')
        if result is None:
            return
        if isinstance(result, tuple):
            continue
        run_command(win, [sys.executable, NODEMAP, '--query', keys[result]])


# ---------------------------------------------------------------------------
# main menu
# ---------------------------------------------------------------------------

def summary_lines():
    """A few facts about the current map, for the menu screen."""
    data = load_json(NODEMAP_JSON)
    if not data.get('nodes'):
        return ['No nodemap.json yet - start with Crawl.']
    nodes = data['nodes']
    info = data.get('crawl_info', {})
    counts = info.get('status_counts') or {}
    missing = sum(1 for n in nodes.values()
                  if not (n.get('gridsquare') or (n.get('location') or {}).get('grid')))
    lines = ['{} nodes, {} links, last crawl {}'.format(
        len(nodes), len(data.get('connections', [])),
        info.get('timestamp', 'unknown'))]
    if counts:
        lines.append('status: ' + ', '.join(
            '{} {}'.format(v, k) for k, v in sorted(counts.items())))
    tail = []
    if missing:
        tail.append('{} without a gridsquare'.format(missing))
    ignored = len(load_json(OVERRIDES_JSON).get('ignore', {}))
    if ignored:
        tail.append('{} callsigns ignored'.format(ignored))
    if tail:
        lines.append(', '.join(tail))
    return lines


MENU = [
    ('Crawl the network', screen_crawl),
    ('Nodes and status', screen_nodes),
    ('Gridsquares', screen_grids),
    ('Ignored callsigns', screen_ignored),
]


def screen_main(win, theme):
    selected = 0
    while True:
        height, width = win.getmaxyx()
        draw_chrome(win, theme, 'v{}'.format(__version__),
                    'up/down move  enter select  g generate maps  q quit')
        for index, (label, _handler) in enumerate(MENU):
            marker = '>' if index == selected else ' '
            safe_addstr(win, 2 + index, 2, '{} {}'.format(marker, label).ljust(width - 4),
                        theme.sel if index == selected else 0)
        row = 3 + len(MENU)
        for line in summary_lines():
            safe_addstr(win, row, 2, line[:width - 4], theme.dim)
            row += 1
        win.refresh()

        key = win.getch()
        if key in (curses.KEY_UP, ord('k')):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            selected = min(len(MENU) - 1, selected + 1)
        elif key in (10, 13, curses.KEY_ENTER):
            MENU[selected][1](win, theme)
        elif key in (ord('g'), ord('G')):
            html = os.path.join(HERE, 'nodemap-html.py')
            if os.path.isfile(html):
                run_command(win, [sys.executable, html, '--all'])
            else:
                show_message(win, theme, ['nodemap-html.py is not installed.'],
                             'Maps')
        elif key in (ord('q'), 27):
            return
        elif key == curses.KEY_RESIZE:
            continue


def run(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    theme = Theme()
    height, width = stdscr.getmaxyx()
    if height < MIN_HEIGHT or width < MIN_WIDTH:
        show_message(stdscr, theme,
                     ['Terminal is {}x{}.'.format(width, height),
                      'This needs at least {}x{}.'.format(MIN_WIDTH, MIN_HEIGHT)],
                     'Too small')
        return
    screen_main(stdscr, theme)


def main():
    if '--help' in sys.argv or '-h' in sys.argv:
        print('nodemap-tui {} - full-screen front end for nodemap.py'.format(__version__))
        print('')
        print('Usage: nodemap-tui.py')
        print('')
        print('Builds a crawl command from a menu, reviews node status and')
        print('gridsquares, and manages the ignored-callsign list. Every action')
        print('shells out to nodemap.py, which must be in the same directory.')
        return 0
    if not os.path.isfile(NODEMAP):
        sys.stderr.write('Error: nodemap.py not found next to this script.\n')
        sys.stderr.write('Expected: {}\n'.format(NODEMAP))
        return 1
    try:
        curses.wrapper(run)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == '__main__':
    sys.exit(main())
