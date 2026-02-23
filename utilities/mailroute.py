#!/usr/bin/env python3
"""
BPQ BBS Mail Forwarding Route Analyzer
---------------------------------------
Reads network topology from nodemap.json and generates BBS mail
forwarding configuration recommendations. Helps sysops set up
inter-BBS message routing with connect scripts, hierarchical
addresses, bulletin distribution, and NTS traffic routing.

For each reachable BBS in the network, outputs:
  - BBS identity (callsign, alias, hierarchical address)
  - Forwarding role (Bulletin Partner vs Personal-Only)
  - Shortest RF path from home node
  - Connect script (primary via NetRom alias + ELSE fallbacks)
  - HRoutes / HRoutesP for bulletin and directed mail
  - Recommended forwarding settings for BPQ web UI

Also generates:
  - Bulletin distribution tree (which BBSes relay to which)
  - NTS traffic routing guide with FWDAliases
  - HF gateway identification for wider network access

Author: Brad Brown (KC1JMH)
Date: February 2026
Version: 1.1
"""

__version__ = '1.1'

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
               grid, freqs, sysop, is_hf}}
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
            'is_hf': _detect_hf(data, info),
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


def _detect_hf(node_data, info):
    """Detect HF capability from hf_ports field or info text."""
    if node_data.get('hf_ports'):
        return True
    upper = info.upper()
    return ('VARA' in upper or 'ARDOP' in upper or 'PACTOR' in upper)


def _extract_state(ha):
    """Extract state code from hierarchical address.

    E.g., 'KS1R.#SAGA.ME.USA.NOAM' -> 'ME'
    """
    if not ha:
        return None
    parts = ha.split('.')
    for i, part in enumerate(parts):
        if part in ('USA', 'CAN') and i > 0:
            return parts[i - 1].lstrip('#')
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


def build_bbs_graph(graph, bbs_data):
    """Build BBS-only adjacency from the full node graph.

    Two BBSes are neighbors if they share an edge in the node graph.
    """
    bbs_bases = set(bbs_data.keys())
    bbs_graph = {}
    for base in bbs_bases:
        bbs_graph[base] = {n for n in graph.get(base, set())
                           if n in bbs_bases}
    return bbs_graph


def build_distribution_tree(bbs_graph, home_base):
    """Build BFS spanning tree of bulletin forwarding order.

    Returns dict: {parent: [children]} representing the recommended
    bulletin distribution tree rooted at home_base.
    """
    tree = {}
    visited = {home_base}
    queue = deque([home_base])

    while queue:
        node = queue.popleft()
        for neighbor in sorted(bbs_graph.get(node, [])):
            if neighbor not in visited:
                visited.add(neighbor)
                if node not in tree:
                    tree[node] = []
                tree[node].append(neighbor)
                queue.append(neighbor)

    return tree


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


# --- Bulletin and NTS routing ---

def detect_hf_gateways(bbs_data):
    """Return set of base callsigns for BBSes with HF capability."""
    return {base for base, info in bbs_data.items() if info.get('is_hf')}


def get_forwarding_role(home_base, target_base, dist_tree):
    """Determine forwarding role for a target BBS.

    Returns:
        'bulletin': Direct child in distribution tree
                    (forward bulletins + personal mail)
        'personal': Remote BBS (forward personal mail only)
    """
    children = dist_tree.get(home_base, [])
    if target_base in children:
        return 'bulletin'
    return 'personal'


def get_hroutes(target_base, bbs_info, role, hf_gateways):
    """Recommend HRoutes value for flood bulletin distribution.

    For bulletin partners: geographic area they serve.
    For HF gateways: broader coverage (USA/WW).
    For personal-only: empty.
    """
    if role != 'bulletin':
        return ''

    if target_base in hf_gateways:
        return 'USA.NOAM'

    ha = bbs_info.get('ha')
    state = _extract_state(ha)
    if state:
        return '{}.USA.NOAM'.format(state)

    return 'ME.USA.NOAM'


def get_hroutes_p(target_base, bbs_info):
    """Recommend HRoutesP value for personal/directed mail.

    Uses the target BBS's hierarchical address for specific
    matching. BPQ routes to the partner with the best match.
    """
    ha = bbs_info.get('ha')
    if ha:
        return ha
    return '{}.#???.ME.USA.NOAM'.format(target_base)


# --- Output formatting ---

def format_path(path):
    """Format a path as arrow-separated string."""
    return ' -> '.join(path)


def print_separator():
    """Print section separator."""
    print('-' * 60)


def print_bbs_entry(index, target_base, bbs_info, home_base, paths,
                     bbs_data, nodes, role, hf_gateways):
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
    is_hf = bbs_info.get('is_hf', False)

    hroutes = get_hroutes(target_base, bbs_info, role, hf_gateways)
    hroutes_p = get_hroutes_p(target_base, bbs_info)
    personal_only = (role == 'personal')

    # Header with role indicator
    print()
    alias_str = ' ({})'.format(bbs_alias) if bbs_alias else ''
    if role == 'bulletin':
        role_tag = 'BULLETIN + PERSONAL'
    else:
        role_tag = 'PERSONAL ONLY'
    hf_tag = ' [HF GATEWAY]' if is_hf else ''
    print('[{}] {}{} [{}]{}'.format(
        index, bbs_call, alias_str, role_tag, hf_tag))
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

    # Hierarchical Routes (Flood Bulls)
    if hroutes:
        print('  Hier Routes (Flood Bulls):    {}'.format(hroutes))
    else:
        print('  Hier Routes (Flood Bulls):    (leave empty)')

    # HR (Personals and Directed Bulls)
    if hroutes_p:
        print('  HR (Personals/Directed):      {}'.format(hroutes_p))
    else:
        print('  HR (Personals/Directed):      (leave empty)')

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
    if personal_only:
        print('  Interval:             14400 secs (4 hours)')
    else:
        print('  Interval:             3600 secs (1 hour)')
    print('  Request Reverse:      No')
    print('  FBB Blocked:          Yes')
    print('  Max Block:            10000')
    print('  Send Personal Only:   {}'.format(
        'Yes' if personal_only else 'No'))
    print('  Allow Binary:         Yes')
    print('  Use B1 Protocol:      Yes')
    print('  Use B2 Protocol:      Yes')
    print('  Connect Timeout:      120 secs')

    if role == 'personal':
        print()
        print('  NOTE: This BBS receives bulletins via intermediate')
        print('  forwarding partners. Direct bulletin forwarding is')
        print('  not needed and would cause duplicate traffic.')

    print()


def print_config_snippet(target_base, bbs_info, paths, bbs_data, nodes,
                          role, hf_gateways):
    """Print linmail.cfg-compatible forwarding record."""
    bbs_call = bbs_info.get('bbs_call', '?')
    ha = bbs_info.get('ha') or '{}.#???.ME.USA.NOAM'.format(target_base)
    hroutes = get_hroutes(target_base, bbs_info, role, hf_gateways)
    hroutes_p = get_hroutes_p(target_base, bbs_info)
    personal_only = (role == 'personal')

    script_lines = []
    if paths:
        script_lines = build_full_script(paths, bbs_data, nodes, target_base)

    bbs_base = bbs_call.split('-')[0]
    print('  {}:'.format(bbs_base))
    print('  {')
    print('    TOCalls = "*";')
    print('    ATCalls = "{}";'.format(ha))
    print('    HRoutes = "{}";'.format(hroutes))
    print('    HRoutesP = "{}";'.format(hroutes_p))
    print('    ConnectScript = "{}";'.format('\\n'.join(script_lines)))
    print('    FWDTimes = "";')
    print('    Enabled = 1;')
    print('    RequestReverse = 0;')
    print('    AllowBlocked = 1;')
    print('    AllowCompressed = 1;')
    print('    UseB1Protocol = 1;')
    print('    UseB2Protocol = 1;')
    print('    SendCTRLZ = 0;')
    print('    FWDPersonalsOnly = {};'.format(1 if personal_only else 0))
    print('    FWDNewImmediately = 0;')
    print('    FwdInterval = {};'.format(14400 if personal_only else 3600))
    print('    RevFWDInterval = 0;')
    print('    MaxFBBBlock = 10000;')
    print('    ConTimeout = 120;')
    print('    BBSHA = "{}";'.format(ha))
    print('  };')
    print()


# --- Bulletin distribution and NTS ---

def render_tree(tree, bbs_data, hf_gateways, node, prefix='',
                is_last=True):
    """Recursively render ASCII distribution tree."""
    info = bbs_data.get(node, {})
    bbs_call = info.get('bbs_call', node)
    bbs_alias = info.get('bbs_alias', '')
    hf_tag = ' (HF)' if node in hf_gateways else ''
    alias_tag = ' [{}]'.format(bbs_alias) if bbs_alias else ''

    if prefix == '':
        print('  {}{}{}'.format(bbs_call, alias_tag, hf_tag))
    else:
        connector = '+-- '
        print('  {}{}{}{}{}'.format(
            prefix, connector, bbs_call, alias_tag, hf_tag))

    children = tree.get(node, [])
    for i, child in enumerate(children):
        child_last = (i == len(children) - 1)
        if prefix == '':
            child_prefix = '  '
        else:
            child_prefix = prefix + ('    ' if is_last else '|   ')
        render_tree(tree, bbs_data, hf_gateways, child,
                    child_prefix, child_last)


def print_bulletin_strategy(home_base, bbs_data, bbs_graph, dist_tree,
                             hf_gateways, nodes):
    """Print bulletin distribution strategy and tree."""
    print()
    print('BULLETIN DISTRIBUTION STRATEGY')
    print('=' * 60)
    print()
    print('Bulletins (flood messages) should propagate through the')
    print('network via direct BBS neighbors, not by connecting to')
    print('every BBS individually. Each BBS forwards bulletins to')
    print('its tree children, who forward to theirs. This prevents')
    print('duplicate traffic over slow 1200 baud links.')
    print()

    # Distribution tree
    print('Recommended Bulletin Distribution Tree:')
    print()
    render_tree(dist_tree, bbs_data, hf_gateways, home_base)
    print()

    # Explain the tree
    children = dist_tree.get(home_base, [])
    if children:
        child_str = ', '.join(
            bbs_data.get(c, {}).get('bbs_call', c) for c in children)
        print('Your BBS should forward bulletins to: {}'.format(child_str))
        print('These partners relay to the rest of the network.')
    else:
        print('No direct BBS neighbors found in distribution tree.')
    print()

    # BBS neighbor count
    neighbors = bbs_graph.get(home_base, set())
    if len(neighbors) <= 1 and children:
        print('With only {} BBS neighbor, ALL bulletin and NTS'.format(
            len(neighbors)))
        print('traffic routes through {}.'.format(
            bbs_data.get(children[0], {}).get('bbs_call', children[0])))
        print()

    # HF gateway note
    if hf_gateways:
        gw_list = ', '.join(sorted(hf_gateways))
        print('HF Gateway: {}'.format(gw_list))
        print('  Bulletins from the wider packet network (USA/WW)')
        print('  enter the local network through the HF gateway.')
        print('  Ensure the HF gateway BBS has forwarding records')
        print('  to nationwide/worldwide BBSes via HF links.')
        print()

    # Hierarchical routing explanation
    print('Hierarchical Routes (HRoutes) Field:')
    print('  Controls which flood bulletins are sent to each partner.')
    print('  ME.USA.NOAM  = Maine, US, and worldwide bulletins')
    print('  USA.NOAM     = US and worldwide (for HF gateways)')
    print('  WW           = All worldwide bulletins')
    print()
    print('  Bulletins are flood-distributed: each BBS that matches')
    print('  receives a copy, checks for duplicates by message ID,')
    print('  and forwards to its own partners. Duplicates are')
    print('  automatically discarded.')
    print()


def print_nts_guide(home_base, home_info, bbs_data, hf_gateways):
    """Print NTS traffic routing guide."""
    print()
    print('NTS TRAFFIC ROUTING')
    print('=' * 60)
    print()
    print('The National Traffic System (NTS) uses packet BBS for')
    print('store-and-forward delivery of formal radiograms. NTS')
    print('messages are posted as bulletins addressed to geographic')
    print('distribution lists.')
    print()

    # Common NTS addresses
    print('NTS Addressing Conventions:')
    print_separator()
    print('  TO Address      Meaning')
    print('  -----------     -----------------------------------')
    print('  NTS1ME          Maine (Region 1) traffic')
    print('  NTSME           Maine traffic (alternate form)')
    print('  NTS1            Region 1 - New England')
    print('  NTS             General NTS traffic')
    print('  NTSR1           Region 1 Net traffic')
    print('  NTS1CT          Connecticut section')
    print('  NTS1RI          Rhode Island section')
    print('  NTS1VT          Vermont section')
    print('  NTS1NH          New Hampshire section')
    print('  NTS1EMA         Eastern Massachusetts section')
    print('  NTS1WMA         Western Massachusetts section')
    print()

    # FWDAliases
    print('Recommended FWDAliases:')
    print_separator()
    print('  Add to Mail Management -> Configuration in BPQ web UI.')
    print('  Maps NTS distribution lists to hierarchical addresses')
    print('  so bulletin routing works correctly.')
    print()
    print('  Alias          Maps To         Description')
    print('  ----------     -----------     ----------------------')
    print('  NTS1ME         ME.USA.NOAM     Maine NTS traffic')
    print('  NTSME          ME.USA.NOAM     Maine (alternate)')
    print('  NTS1           ME.USA.NOAM     Region 1 (local scope)')
    print('  NTS            USA.NOAM        General NTS (nationwide)')
    print('  ALLUS          USA.NOAM        All US traffic')
    print('  ALLME          ME.USA.NOAM     All Maine traffic')
    print()

    # NTS traffic flow
    print('NTS Traffic Flow:')
    print_separator()
    print()
    print('  Outgoing (originate from your BBS):')
    print('    1. User posts message: TO NTS1ME @ ME.USA.NOAM')
    print('    2. Bulletin floods to all Maine BBSes via HRoutes')
    print('    3. NTS liaison operator retrieves from any BBS')
    print('    4. Liaison relays via voice net or phone')
    print()
    print('  Incoming (destined for your area):')
    print('    1. NTS liaison posts: TO NTS1ME @ ME.USA.NOAM')
    print('    2. Bulletin floods to all Maine BBSes')
    print('    3. Local operators check their BBS for traffic')
    print('    4. Delivering operator contacts recipient')
    print()
    print('  Interstate (relay through HF gateway):')
    if hf_gateways:
        gw_list = ', '.join(sorted(hf_gateways))
        print('    NTS traffic for other states routes through')
        print('    HF gateway ({}) to the nationwide network.'.format(
            gw_list))
    else:
        print('    No HF gateway detected in network.')
        print('    Interstate NTS requires HF-connected BBS.')
    print()

    # NTS message format
    print('NTS Radiogram Format on BBS:')
    print_separator()
    print()
    print('  SP NTS1ME @ ME.USA.NOAM        (post as bulletin)')
    print('  Subject: QTC 1 PORTLAND ME      (city, state)')
    print()
    print('  NR 123 R W1ABC 15 PORTLAND ME 0800Z FEB 23')
    print('  JOHN DOE')
    print('  123 MAIN ST')
    print('  PORTLAND ME 04101')
    print('  207-555-1234')
    print('  BT')
    print('  HAPPY BIRTHDAY STOP LOVE FROM GRANDMA')
    print('  BT')
    print('  NO RPT NEEDED')
    print('  73 DE W1ABC')
    print()
    print('  /EX                             (end of message)')
    print()


# --- Network summary ---

def print_topology_summary(home_base, home_info, bbs_data, graph, nodes,
                            bbs_graph, hf_gateways):
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
    bbs_neighbors = bbs_graph.get(home_base, set())
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
    print('Network:     {} nodes, {} BBSes detected'.format(
        total_nodes, total_bbs))
    print('Reachable:   {} BBSes ({} unreachable)'.format(
        reachable, unreachable))
    print('BBS Neighbors: {} direct'.format(len(bbs_neighbors)))
    if bbs_neighbors:
        print('             {}'.format(', '.join(sorted(bbs_neighbors))))
    if hf_gateways:
        print('HF Gateways: {}'.format(', '.join(sorted(hf_gateways))))
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
    print("       BBS-to-BBS mail forwarding recommendations including")
    print("       bulletin distribution strategy, NTS traffic routing,")
    print("       and connect scripts for the BPQ32 web UI.")
    print()
    print("       For bulletins, recommends a distribution tree where")
    print("       each BBS forwards only to its direct BBS neighbors,")
    print("       avoiding redundant traffic over slow RF links.")
    print()
    print("       For personal mail, provides direct connect scripts")
    print("       to each reachable BBS via shortest RF path.")
    print()
    print("       For NTS traffic, provides radiogram routing guidance")
    print("       and FWDAliases configuration.")
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
    print("       -b, --bulletin")
    print("              Show bulletin strategy and NTS guide only.")
    print()
    print("       -h, --help, /?")
    print("              Show this help message.")
    print()
    print("EXAMPLES")
    print("       mailroute.py")
    print("              Full analysis with bulletin and NTS routing.")
    print()
    print("       mailroute.py -n WS1EC")
    print("              Analyze forwarding from WS1EC.")
    print()
    print("       mailroute.py -t KC1JMH")
    print("              Show routing to KC1JMH's BBS only.")
    print()
    print("       mailroute.py -b")
    print("              Show bulletin tree and NTS guide only.")
    print()
    print("       mailroute.py -c > forwarding.cfg")
    print("              Generate linmail.cfg snippets to file.")
    print()
    print("       mailroute.py -j /path/to/nodemap.json")
    print("              Use specific JSON file.")
    print()
    print("FILES")
    print("       nodemap.json    Network topology (from nodemap.py)")
    print("       linmail.cfg     BPQ mail forwarding config")
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
    print("       Forwarding Roles:")
    print("         BULLETIN + PERSONAL = direct BBS neighbor,")
    print("           forwards flood bulletins and personal mail")
    print("         PERSONAL ONLY = remote BBS, bulletins arrive")
    print("           via intermediate BBSes in the distribution tree")
    print()
    print("       NTS Traffic:")
    print("         National Traffic System radiograms use bulletin-")
    print("         style addressing (TO NTS1ME @ ME.USA.NOAM).")
    print("         Configure FWDAliases so BPQ routes NTS bulletins")
    print("         through the hierarchical system.")


def main():
    """Parse arguments and run analysis."""
    json_path = 'nodemap.json'
    home_call = None
    target_call = None
    config_mode = False
    summary_only = False
    bulletin_only = False

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
        elif arg in ('-b', '--bulletin'):
            bulletin_only = True
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

    # Extract BBS data and build graphs
    bbs_data = extract_bbs_nodes(nodes)
    graph = build_graph(nodes)
    bbs_graph = build_bbs_graph(graph, bbs_data)
    dist_tree = build_distribution_tree(bbs_graph, home_call)
    hf_gateways = detect_hf_gateways(bbs_data)
    home_info = bbs_data.get(home_call)

    # Summary
    if not config_mode:
        print_topology_summary(home_call, home_info, bbs_data, graph,
                                nodes, bbs_graph, hf_gateways)

    if summary_only:
        return

    # Bulletin strategy and NTS guide
    if not config_mode:
        print_bulletin_strategy(home_call, bbs_data, bbs_graph,
                                 dist_tree, hf_gateways, nodes)
        print_nts_guide(home_call, home_info, bbs_data, hf_gateways)

        if bulletin_only:
            return

    # Config mode header
    if config_mode:
        print('# Mail forwarding configuration generated by mailroute.py')
        print('# Home node: {}'.format(home_call))
        print('# Generated from: {}'.format(json_path))
        print('#')
        print('# Paste into BBSForwarding section of linmail.cfg')
        print('# or configure via BPQ32 web UI -> Forwarding tab')
        print('#')
        print('# Roles: bulletin partners get flood bulletins + personal')
        print('#        personal-only partners get direct personal mail')
        print()

    # Section header for per-BBS entries
    if not config_mode:
        print()
        print('PER-BBS FORWARDING CONFIGURATION')
        print('=' * 60)

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
        role = get_forwarding_role(home_call, target_base, dist_tree)

        if config_mode:
            print_config_snippet(target_base, bbs_info, paths,
                                 bbs_data, nodes, role, hf_gateways)
        else:
            print_bbs_entry(index, target_base, bbs_info, home_call,
                            paths, bbs_data, nodes, role, hf_gateways)

    if target_call and index == 0:
        print("BBS '{}' not found in network data.".format(target_call))
        print("Known BBSes: {}".format(', '.join(sorted(bbs_data.keys()))))
        sys.exit(1)

    # Footer
    if not config_mode and index > 0:
        print_separator()
        print()
        print('NOTES')
        print('  - BULLETIN + PERSONAL partners are your direct BBS')
        print('    neighbors in the distribution tree. They receive')
        print('    flood bulletins AND personal/directed mail.')
        print()
        print('  - PERSONAL ONLY partners receive direct personal')
        print('    mail via multi-hop connect scripts. Bulletins')
        print('    reach them through intermediate BBS partners.')
        print()
        print('  - BBSes with ??? in HA need manual hierarchical')
        print('    address configuration. Ask the remote sysop or')
        print('    check their BBS HA in the forwarding web UI.')
        print()
        print('  - Configure FWDAliases for NTS traffic routing')
        print('    (see NTS TRAFFIC ROUTING section above).')
        print()
        print('  - B1 protocol recommended for all BPQ-to-BPQ links.')
        print('  - Increase Interval for unreliable RF paths.')
        print('  - HF gateways need broader HRoutes (USA.NOAM)')
        print('    to receive nationwide/worldwide bulletins.')
        print()


if __name__ == '__main__':
    main()
