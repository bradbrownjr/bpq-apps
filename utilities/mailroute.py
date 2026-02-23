#!/usr/bin/env python3
"""
BPQ BBS Mail Forwarding Route Analyzer
---------------------------------------
Reads network topology from nodemap.json and generates BBS mail
forwarding configuration recommendations. Helps sysops set up
inter-BBS message routing with connect scripts, hierarchical
addresses, and forwarding settings.

For each reachable BBS in the network, outputs:
  - BBS identity (callsign, alias, hierarchical address)
  - Shortest RF path from home node
  - Connect script (primary via NetRom alias + ELSE fallbacks)
  - Recommended forwarding settings for BPQ web UI

Author: Brad Brown (KC1JMH)
Date: February 2026
Version: 1.0
"""

__version__ = '1.0'

import json
import sys
import os
import re
from collections import deque


# --- Data extraction ---

def load_nodemap(filepath):
    """Load and parse nodemap.json."""
    with open(filepath) as f:
        return json.load(f)


def extract_bbs_nodes(nodes):
    """Identify BBS nodes from alias data.

    Scans own_aliases for entries containing 'BBS'. Extracts
    hierarchical addresses, locations, grids from info text.

    Returns:
        dict: {base_call: {node_call, node_alias, bbs_call,
               bbs_alias, rms_call, rms_alias, ha, location,
               grid, freqs, sysop}}
    """
    bbs_data = {}

    for node_call, data in nodes.items():
        aliases = data.get('own_aliases', {})
        info = data.get('info', '') or ''
        base = node_call.split('-')[0]

        bbs_alias = bbs_call = None
        rms_alias = rms_call = None
        node_alias = None

        for alias, call in aliases.items():
            upper = alias.upper()
            if 'BBS' in upper:
                bbs_alias = alias.upper()
                bbs_call = call
            elif 'RMS' in upper:
                rms_alias = alias.upper()
                rms_call = call
            elif call == node_call:
                node_alias = alias.upper()

        if not bbs_call:
            continue

        bbs_data[base] = {
            'node_call': node_call,
            'node_alias': node_alias,
            'bbs_call': bbs_call,
            'bbs_alias': bbs_alias,
            'rms_call': rms_call,
            'rms_alias': rms_alias,
            'ha': _extract_ha(info),
            'location': _extract_location(info),
            'grid': _extract_grid(info),
            'freqs': re.findall(r'(\d{2,3}\.\d{2,3})\s*MHz', info),
            'sysop': _extract_sysop(info),
        }

    return bbs_data


def _extract_ha(info):
    """Extract BBS hierarchical address from info text.

    Looks for patterns like:
        BBS  @  KS1R.#SAGA.ME.USA.NOAM
        BBS @  N1REX.ME.USA.NA
    """
    m = re.search(
        r'BBS\s+@\s+(\S+\.\S+\.\w+\.\w+)',
        info, re.IGNORECASE
    )
    if m:
        return m.group(1).upper()
    return None


def _extract_location(info):
    """Extract location from info text."""
    patterns = [
        r'AT\s+([A-Z][A-Za-z. ]+,\s*[A-Z]{2})\s',
        r'(?:at|in)\s+([A-Za-z. ]+,\s*[A-Z]{2})\b',
        r'-\s+([A-Za-z. ]+,\s*[A-Z]{2})\s',
        r'on\s+([A-Za-z ]+(?:Hill|Mountain)),\s*([A-Z]{2})\s',
    ]
    for pat in patterns:
        m = re.search(pat, info)
        if m:
            if m.lastindex == 2:
                return '{}, {}'.format(m.group(1), m.group(2))
            return m.group(1).strip()
    return None


def _extract_grid(info):
    """Extract Maidenhead grid square from info text."""
    m = re.search(r'\b([A-R]{2}\d{2}[a-x]{2})\b', info)
    if m:
        return m.group(1)
    m = re.search(r'\b([A-R]{2}\d{2})\b', info)
    if m:
        return m.group(1)
    return None


def _extract_sysop(info):
    """Extract sysop callsign/email from info text."""
    m = re.search(r'[Ss]ysop[:\s]+(\S+)', info)
    if m:
        return m.group(1)
    return None


# --- Graph and pathfinding ---

def build_graph(nodes):
    """Build bidirectional adjacency graph from direct_routes.

    Uses direct_routes (preferred) or routes as fallback.
    Returns dict mapping base_call -> set of neighbor base_calls.
    """
    graph = {}

    for node_call, data in nodes.items():
        base = node_call.split('-')[0]
        if base not in graph:
            graph[base] = set()

        routes = data.get('direct_routes') or data.get('routes', {})
        for neighbor in routes:
            nb = neighbor.split('-')[0]
            graph[base].add(nb)
            if nb not in graph:
                graph[nb] = set()
            graph[nb].add(base)

    return graph


def find_paths(graph, start, end, max_paths=3):
    """Find up to max_paths shortest paths via BFS.

    Returns list of paths, each a list of base callsigns.
    """
    if start == end:
        return [[start]]

    dist = {start: 0}
    parents = {start: []}
    queue = deque([start])

    while queue:
        node = queue.popleft()
        for neighbor in sorted(graph.get(node, [])):
            if neighbor not in dist:
                dist[neighbor] = dist[node] + 1
                parents[neighbor] = [node]
                queue.append(neighbor)
            elif dist[neighbor] == dist[node] + 1:
                parents[neighbor].append(node)

    if end not in dist:
        return []

    def _build(node):
        if node == start:
            return [[start]]
        result = []
        for p in parents.get(node, []):
            for path in _build(p):
                result.append(path + [node])
                if len(result) >= max_paths:
                    return result
        return result

    return _build(end)[:max_paths]


# --- Connect script generation ---

def get_node_alias(base_call, nodes):
    """Get the NetRom node alias for a base callsign."""
    for node_call, data in nodes.items():
        if node_call.split('-')[0] == base_call:
            aliases = data.get('own_aliases', {})
            for alias, call in aliases.items():
                if call == node_call:
                    return alias.upper()
    return None


def get_node_call(base_call, nodes):
    """Get the full node callsign (with SSID) for a base callsign."""
    for node_call in nodes:
        if node_call.split('-')[0] == base_call:
            return node_call
    return base_call


def make_connect_script(path, bbs_data, nodes, target_base, use_alias=True):
    """Generate BPQ connect script lines for a path.

    Args:
        path: list of base callsigns from home to target
        bbs_data: dict of extracted BBS info
        nodes: raw nodes dict from JSON
        target_base: target BBS base callsign
        use_alias: if True, use BBS NetRom alias (single hop via NetRom)
                   if False, use explicit hop-by-hop path

    Returns:
        list of connect script lines
    """
    target = bbs_data.get(target_base, {})
    bbs_call = target.get('bbs_call', '{}-2'.format(target_base))
    bbs_alias = target.get('bbs_alias')

    if len(path) <= 1:
        return ['C {}'.format(bbs_call)]

    # Primary: use BBS alias (NetRom routes transparently)
    if use_alias and bbs_alias:
        return ['C {}'.format(bbs_alias)]

    # Explicit path: hop through intermediate nodes
    lines = []
    for i in range(1, len(path) - 1):
        intermediate = path[i]
        alias = get_node_alias(intermediate, nodes)
        if alias:
            lines.append('C {}'.format(alias))
        else:
            lines.append('C {}'.format(get_node_call(intermediate, nodes)))

    lines.append('C {}'.format(bbs_call))
    return lines


def build_full_script(paths, bbs_data, nodes, target_base):
    """Build complete connect script with ELSE fallbacks.

    Primary path uses BBS NetRom alias. ELSE paths use explicit
    hop-by-hop routing through intermediate nodes.

    Returns:
        list of script lines including ELSE blocks
    """
    if not paths:
        return ['; NO PATH FOUND']

    lines = []

    # Primary: via BBS alias (NetRom routes the path)
    primary = make_connect_script(paths[0], bbs_data, nodes, target_base,
                                  use_alias=True)
    lines.extend(primary)

    # ELSE: explicit hop path (same route but with intermediate hops)
    explicit = make_connect_script(paths[0], bbs_data, nodes, target_base,
                                   use_alias=False)
    if explicit != primary:
        lines.append('ELSE')
        lines.extend(explicit)

    # Additional ELSE blocks for alternate routes
    for alt_path in paths[1:]:
        alt = make_connect_script(alt_path, bbs_data, nodes, target_base,
                                  use_alias=False)
        if alt != explicit:
            lines.append('ELSE')
            lines.extend(alt)

    return lines


# --- Output formatting ---

def format_path(path):
    """Format a path as arrow-separated string."""
    return ' -> '.join(path)


def print_separator():
    """Print section separator."""
    print('-' * 60)


def print_bbs_entry(index, target_base, bbs_info, home_base, paths,
                     bbs_data, nodes):
    """Print forwarding recommendation for one BBS.

    Output maps directly to BPQ32 web UI forwarding fields.
    """
    bbs_call = bbs_info.get('bbs_call', '?')
    bbs_alias = bbs_info.get('bbs_alias', '')
    node_alias = bbs_info.get('node_alias', '')
    ha = bbs_info.get('ha')
    location = bbs_info.get('location', '')
    grid = bbs_info.get('grid', '')
    sysop = bbs_info.get('sysop', '')
    rms_call = bbs_info.get('rms_call', '')
    freqs = bbs_info.get('freqs', [])

    # Header
    print()
    alias_str = ' ({})'.format(bbs_alias) if bbs_alias else ''
    print('[{}] {}{}'.format(index, bbs_call, alias_str))
    print_separator()

    # Identity
    if location:
        loc_str = location
        if grid:
            loc_str += ' ({})'.format(grid)
        print('  Location:       {}'.format(loc_str))
    elif grid:
        print('  Grid:           {}'.format(grid))

    if node_alias:
        print('  Node Alias:     {}'.format(node_alias))

    if rms_call:
        print('  RMS Gateway:    {}'.format(rms_call))

    if freqs:
        print('  Frequencies:    {} MHz'.format(', '.join(freqs)))

    if sysop:
        print('  Sysop:          {}'.format(sysop))

    # Path
    if paths:
        hops = len(paths[0]) - 1
        print('  Hops:           {}'.format(hops))
        print('  Path:           {}'.format(format_path(paths[0])))
        if len(paths) > 1:
            for alt in paths[1:]:
                print('  Alt Path:       {}'.format(format_path(alt)))
    else:
        print('  Hops:           UNREACHABLE')

    print()

    # BPQ Web UI fields
    print('  --- BPQ Forwarding Config ---')

    # BBS HA
    if ha:
        print('  BBS HA:         {}'.format(ha))
    else:
        # Suggest format
        print('  BBS HA:         {}.#???.ME.USA.NOAM'.format(target_base))
        print('                  ^ configure manually (HA not advertised)')

    # TO / AT
    print('  TO:             *')
    if ha:
        print('  AT:             {}'.format(ha))
    else:
        print('  AT:             {}.#???.ME.USA.NOAM'.format(target_base))

    # Connect script
    if paths:
        script = build_full_script(paths, bbs_data, nodes, target_base)
        print('  Connect Script:')
        for line in script:
            print('    {}'.format(line))
    else:
        print('  Connect Script: ; no RF path found')

    # Settings
    print()
    print('  --- Recommended Settings ---')
    print('  Enable Forwarding:    Yes')
    print('  Interval:             3600 secs (1 hour)')
    print('  Request Reverse:      No')
    print('  FBB Blocked:          Yes')
    print('  Max Block:            10000')
    print('  Allow Binary:         Yes')
    print('  Use B1 Protocol:      Yes')
    print('  Use B2 Protocol:      Yes')
    print('  Send Personal Only:   Yes')
    print('  Connect Timeout:      120 secs')

    print()


def print_config_snippet(target_base, bbs_info, paths, bbs_data, nodes):
    """Print linmail.cfg-compatible forwarding record."""
    bbs_call = bbs_info.get('bbs_call', '?')
    ha = bbs_info.get('ha') or '{}.#???.ME.USA.NOAM'.format(target_base)

    script_lines = []
    if paths:
        script_lines = build_full_script(paths, bbs_data, nodes, target_base)

    bbs_base = bbs_call.split('-')[0]
    print('  {}:'.format(bbs_base))
    print('  {')
    print('    TOCalls = "*";')
    print('    ATCalls = "{}";'.format(ha))
    print('    HRoutes = "";')
    print('    HRoutesP = "";')
    print('    ConnectScript = "{}";'.format('\\n'.join(script_lines)))
    print('    FWDTimes = "";')
    print('    Enabled = 1;')
    print('    RequestReverse = 0;')
    print('    AllowBlocked = 1;')
    print('    AllowCompressed = 1;')
    print('    UseB1Protocol = 1;')
    print('    UseB2Protocol = 1;')
    print('    SendCTRLZ = 0;')
    print('    FWDPersonalsOnly = 1;')
    print('    FWDNewImmediately = 0;')
    print('    FwdInterval = 3600;')
    print('    RevFWDInterval = 0;')
    print('    MaxFBBBlock = 10000;')
    print('    ConTimeout = 120;')
    print('    BBSHA = "{}";'.format(ha))
    print('  };')
    print()


# --- Network summary ---

def print_topology_summary(home_base, home_info, bbs_data, graph, nodes):
    """Print network topology summary."""
    print()
    print('MAIL ROUTE ANALYSIS')
    print('=' * 60)
    print()

    # Home node info
    if home_info:
        ha = home_info.get('ha') or '(not set)'
        loc = home_info.get('location', '')
        grid = home_info.get('grid', '')
        print('Home BBS:    {} ({})'.format(
            home_info.get('bbs_call', home_base),
            home_info.get('bbs_alias', '')))
        if loc:
            print('Location:    {}'.format(loc))
        if grid:
            print('Grid:        {}'.format(grid))
        print('BBS HA:      {}'.format(ha))
    else:
        print('Home Node:   {} (no BBS detected)'.format(home_base))

    # Network stats
    total_nodes = len(nodes)
    total_bbs = len(bbs_data)
    reachable = 0
    unreachable = 0
    for base in bbs_data:
        if base == home_base:
            continue
        paths = find_paths(graph, home_base, base, max_paths=1)
        if paths:
            reachable += 1
        else:
            unreachable += 1

    print()
    print('Network:     {} nodes crawled'.format(total_nodes))
    print('BBSes:       {} detected ({} reachable, {} unreachable)'.format(
        total_bbs, reachable, unreachable))
    print()


# --- Main ---

def detect_home_node(data):
    """Auto-detect home node from crawl_info or first node."""
    crawl_info = data.get('crawl_info', {})
    start = crawl_info.get('start_node', '')
    if start:
        return start.split('-')[0]

    # Fall back to first node
    nodes = data.get('nodes', {})
    if nodes:
        first = sorted(nodes.keys())[0]
        return first.split('-')[0]
    return None


def show_help():
    """Display help text."""
    print("NAME")
    print("       mailroute - BPQ BBS mail forwarding route analyzer")
    print()
    print("SYNOPSIS")
    print("       mailroute.py [OPTIONS]")
    print()
    print("VERSION")
    print("       {}".format(__version__))
    print()
    print("DESCRIPTION")
    print("       Reads network topology from nodemap.json and generates")
    print("       BBS-to-BBS mail forwarding recommendations. For each")
    print("       reachable BBS, outputs connect scripts, hierarchical")
    print("       addresses, and settings for the BPQ32 web UI.")
    print()
    print("       Primary connect scripts use BBS NetRom aliases which let")
    print("       BPQ route transparently. ELSE fallbacks provide explicit")
    print("       hop-by-hop paths through intermediate nodes.")
    print()
    print("OPTIONS")
    print("   Input:")
    print("       -j, --json FILE")
    print("              Path to nodemap.json. Default: nodemap.json")
    print()
    print("   Filtering:")
    print("       -n, --node CALL")
    print("              Home node base callsign. Default: auto-detect")
    print("              from crawl_info.start_node in JSON.")
    print()
    print("       -t, --target CALL")
    print("              Show routing for one specific BBS only.")
    print()
    print("   Output:")
    print("       -c, --config")
    print("              Output linmail.cfg format snippets instead of")
    print("              human-readable recommendations.")
    print()
    print("       -s, --summary")
    print("              Show network summary only (no per-BBS detail).")
    print()
    print("       -h, --help, /?")
    print("              Show this help message.")
    print()
    print("EXAMPLES")
    print("       mailroute.py")
    print("              Analyze from auto-detected home node.")
    print()
    print("       mailroute.py -n WS1EC")
    print("              Analyze forwarding from WS1EC.")
    print()
    print("       mailroute.py -t KC1JMH")
    print("              Show routing to KC1JMH's BBS only.")
    print()
    print("       mailroute.py -c > forwarding.cfg")
    print("              Generate linmail.cfg snippets to file.")
    print()
    print("       mailroute.py -j /path/to/nodemap.json")
    print("              Use specific JSON file.")
    print()
    print("FILES")
    print("       nodemap.json    Network topology (from nodemap.py)")
    print("       linmail.cfg     BPQ mail forwarding config (auto-generated)")
    print()
    print("SEE ALSO")
    print("       nodemap.py      - Network topology crawler")
    print("       nodemap-html.py - Map generator")
    print()
    print("NOTES")
    print("       Hierarchical Address (HA) Format:")
    print("         CALL.#COUNTY.STATE.COUNTRY.CONTINENT")
    print("         Example: WS1EC.#CUMB.ME.USA.NOAM")
    print()
    print("       BBSes that don't advertise their HA in node info text")
    print("       are marked with ??? placeholders. Configure these")
    print("       manually in the BPQ web UI.")
    print()
    print("       Connect scripts use the BBS NetRom alias as the primary")
    print("       path (e.g., C BBSWDB). NetRom routes transparently")
    print("       through intermediate nodes. ELSE blocks provide explicit")
    print("       hop-by-hop fallbacks if the alias is unreachable.")


def main():
    """Parse arguments and run analysis."""
    json_path = 'nodemap.json'
    home_call = None
    target_call = None
    config_mode = False
    summary_only = False

    # Parse arguments
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ('-h', '--help', '/?'):
            show_help()
            return
        elif arg in ('-j', '--json') and i + 1 < len(args):
            i += 1
            json_path = args[i]
        elif arg in ('-n', '--node') and i + 1 < len(args):
            i += 1
            home_call = args[i].upper().split('-')[0]
        elif arg in ('-t', '--target') and i + 1 < len(args):
            i += 1
            target_call = args[i].upper().split('-')[0]
        elif arg in ('-c', '--config'):
            config_mode = True
        elif arg in ('-s', '--summary'):
            summary_only = True
        else:
            print("Unknown option: {}".format(arg))
            print("Use -h for help.")
            sys.exit(1)
        i += 1

    # Load data
    if not os.path.exists(json_path):
        print("Error: {} not found".format(json_path))
        print("Run nodemap.py first to generate topology data.")
        sys.exit(1)

    data = load_nodemap(json_path)
    nodes = data.get('nodes', {})

    if not nodes:
        print("Error: no nodes in {}".format(json_path))
        sys.exit(1)

    # Auto-detect home node
    if not home_call:
        home_call = detect_home_node(data)
    if not home_call:
        print("Error: cannot determine home node. Use -n CALL.")
        sys.exit(1)

    # Extract BBS data and build graph
    bbs_data = extract_bbs_nodes(nodes)
    graph = build_graph(nodes)
    home_info = bbs_data.get(home_call)

    # Summary
    if not config_mode:
        print_topology_summary(home_call, home_info, bbs_data, graph, nodes)

    if summary_only:
        return

    # Config mode header
    if config_mode:
        print('# Mail forwarding configuration generated by mailroute.py')
        print('# Home node: {}'.format(home_call))
        print('# Generated from: {}'.format(json_path))
        print('#')
        print('# Paste into BBSForwarding section of linmail.cfg')
        print('# or configure via BPQ32 web UI -> Forwarding tab')
        print()

    # Generate recommendations for each BBS
    targets = sorted(bbs_data.keys())
    index = 0

    for target_base in targets:
        if target_base == home_call:
            continue

        if target_call and target_base != target_call:
            continue

        index += 1
        bbs_info = bbs_data[target_base]
        paths = find_paths(graph, home_call, target_base, max_paths=3)

        if config_mode:
            print_config_snippet(target_base, bbs_info, paths,
                                 bbs_data, nodes)
        else:
            print_bbs_entry(index, target_base, bbs_info, home_call,
                            paths, bbs_data, nodes)

    if target_call and index == 0:
        print("BBS '{}' not found in network data.".format(target_call))
        print("Known BBSes: {}".format(', '.join(sorted(bbs_data.keys()))))
        sys.exit(1)

    # Footer
    if not config_mode and index > 0:
        print_separator()
        print()
        print('NOTES')
        print('  - BBSes with ??? in HA need manual hierarchical address')
        print('    configuration. Ask the remote sysop or check their')
        print('    BBS HA field in the forwarding web UI.')
        print('  - Primary connect scripts use BBS NetRom aliases.')
        print('    ELSE paths route explicitly through intermediate nodes.')
        print('  - B1 protocol recommended for all BPQ-to-BPQ links.')
        print('  - Increase interval for unreliable RF paths.')
        print('  - Set FWDPersonalsOnly=Yes to avoid flooding bulletins')
        print('    until hierarchical routing is fully configured.')
        print()


if __name__ == '__main__':
    main()
