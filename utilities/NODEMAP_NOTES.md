# nodemap.py / nodemap-html.py — working notes

Running log of in-progress work, deferred features, and diagnosed-but-not-yet-fixed
issues for the nodemap toolchain. Not user documentation (see `README.md` for that) —
this is context for whoever picks the work back up, including a future session of
whichever AI assistant is helping maintain this.

---

## In progress: dashed lines for unconfirmed / unstable paths (2026-08-25)

**Origin:** while reviewing the 2026-08-24/25 `--resume` crawl, KC1JMH observed that
N1EP-1 (a home station running a bare Kantronics TNC, not a full BPQ node) sits
isolated on the map whenever nothing can currently reach him, even though AB1KI-15's
ROUTES table clearly lists him as a neighbor. Proposal: instead of the node vanishing
entirely, draw the connection to it as a dashed line.

**Design decided with KC1JMH:** a link is "confirmed" (solid) only if **both** ends
have themselves been successfully connected to at some point AND are currently in
good standing (`status` in `online`/`recent`). This is deliberately *not* the same as
raw ROUTES bidirectionality: a bare TNC like N1EP's can never publish a ROUTES entry
of its own, so a link to him would be permanently flagged by bidirectionality alone no
matter how reliably he answers. "Confirmed" asks "have we ourselves gotten in,
recently" instead — which is what actually distinguishes "reliable" from "claims to
be reliable" for a station that runs hardware that can't corroborate itself.

### Done (nodemap.py side — implemented and tested, not yet deployed)

- `_annotate_connections()` now takes `nodes_data` and stamps a `confirmed: bool` on
  every connection record, computed from each end's `crawl_successes` and `status`
  (both already stamped by `_apply_temporal_fields()`, which now runs before this).
- **Phantom-node stubs**: a connection can point at a node nobody has ever actually
  reached (only some other node's ROUTES vouches for it). Previously such a node had
  no record at all — no location, couldn't be placed on the map, the edge just
  silently disappeared. `export_json()` now scans `connections_data` for any
  `to`/`from` base callsign not already in `nodes_data`, and creates a minimal stub:
  best-effort callsign-only location lookup (`self.resolver.lookup_callsign()`, no RF
  involved), nothing invented if the lookup fails. Matched against `nodes_data.keys()`
  by **base callsign**, not exact string — connections store base-call-only endpoints
  but `nodes_data` keys remote nodes with their SSID once crawled, so a naive exact-key
  check would have spawned a bogus duplicate stub for every already-known SSID-qualified
  node. (Caught by `test_merge_history.py` failing after the first draft — see the
  `known_bases` set in the phantom-stub loop.)
- Stub gets `'partial': True` — `nodemap-html.py`'s existing reciprocity check already
  treats a partial node's routes as incomplete data rather than demanding bidirectional
  agreement, which is exactly the tolerance an empty-routes stub needs (it was never
  crawled at all, not even a normal timed-out partial, so it could never satisfy that
  check on its own).
- **Bug found and fixed along the way**: `_apply_temporal_fields()`'s bootstrap
  fallback (`last_seen = last_seen or bootstrap`) was designed to avoid claiming "seen
  right now" for a node with no fresh data — but a genuinely evidence-free phantom stub
  has *nothing* behind it at all, not even the previous export's context, so it would
  borrow the whole crawl's freshness and read as `online`/`recent` despite never once
  being verified. Fixed: `bootstrap` is now only applied when there's *some* real
  evidence (prior history, having been heard, or freshly crawled this run) — otherwise
  `last_seen` stays `None` and `_node_status()`'s existing `age is None` branch
  correctly reports `unknown`.
- Full test suite passes, including a replay of the actual N1EP-1 scenario from
  tonight's log (`test_confirmed_realistic.py`, `test_phantom_never_attempted.py`,
  `test_confirmed_and_phantom.py` in the scratchpad — not checked in, ad-hoc).

### Not started: nodemap-html.py rendering

Turned out to be more tangled than a one-line hookup:

- `nodemap-html.py` **does not read the top-level `connections` array at all.** Both
  generator functions (`generate_html_map` and `generate_svg_map`) independently
  reconstruct edges from each node's own `direct_routes`/`routes` dict.
- It already has its own separate, ad-hoc "reciprocity check" (search for
  `source_is_partial` / `neighbor_is_partial`) that requires bidirectional ROUTES
  agreement between two fully-crawled nodes — but instead of dashing a one-sided link,
  it **drops it from the map entirely**. Different mechanism, different data source,
  similar rough goal to what `confirmed`/`asymmetric` already capture in the JSON.
- Two full, independently-duplicated copies of the connection-building logic (one per
  generator function) — same duplication pattern already seen with `hf_ports`
  detection and the SSID-consensus code before v1.8.5 factored that one out.
- `intermittent` and `asymmetric` (computed in `_annotate_connections` for a while
  now, before this session even started touching it) are *also* never read by the
  renderer. All three signals (`confirmed`, `intermittent`, `asymmetric`) are sitting
  in the exported JSON unused.

**Recommended approach for whoever picks this up:** don't layer a fourth mechanism on
top. Replace the ad-hoc reciprocity check with the `confirmed` field (computed at
export time, with full context) rather than re-deriving a similar answer from raw
routes at render time. Needs a decision on how a dashed line composes with the
existing HF (`stroke-dasharray="10,5"`) and IP (`"5,5"`) dash styles when a link is
*both* e.g. HF and unconfirmed — a different pattern per state is the natural answer.
Update the legend in both the SVG and HTML generators either way (see the earlier
`v1.4.20` fix for the "Unknown (not yet crawled)" node-marker legend entry — same
kind of change, same two places to touch).

---

## Diagnosed, not a bug: N1EP-1 alternate-path retry (2026-08-25)

KC1JMH asked whether N1EP's crawl was wrongly blocked by the v1.8.6 "skip a path
through an already-known-failed relay" logic, after seeing N1EP attempted via
`AB1KI-15` fail, then attempted again shortly after via `W1LH-6`.

Traced through both attempts in `telnet.log`:

- First attempt (`KC1JMH > N1QFY > AB1KI-15`, target N1EP-1): all three intermediate
  hops connected fine; the failure was at the **final** hop, connecting to N1EP-1
  itself. `self.last_failed_relay` therefore gets set to `N1EP` (not any intermediate),
  so `self.failed_relays.add('N1EP')` blames N1EP itself, not AB1KI-15 or anything
  upstream of it.
- Second attempt (`KC1JMH > N1QFY > AB1KI-15 > W1LH-6`, target N1EP-1): v1.8.6's skip
  check only looks at whether any element of `path` (the intermediate hops) is in
  `failed_relays`. N1EP-1 is the *target*, not in path, on both attempts — so it was
  never eligible to be skipped by that logic. This attempt genuinely ran (four hops
  connected, confirmed in the log), and genuinely failed on its own at the final hop
  again.

**Conclusion:** working as intended. A leaf/end-station target failing once does not
block a later attempt via a different last-hop relay - only an *intermediate* relay
that's already failed blocks paths that would route *through* it again. N1EP is a
leaf, so he can never accidentally end up in that intermediate-blocking set from his
own failures. No fix needed here.

---

## Diagnosed, mostly self-healing: W1BKW-3 phantom SSID (2026-08-25)

KC1JMH flagged `W1BKW-3` showing up as a distinct crawl target, suspecting it might be
a non-node (user/BBS) SSID that should have been filtered.

Traced it fully:

- `W1BKW-3` **does not appear anywhere in tonight's actual received NODES/ROUTES/MHEARD
  text** - every fresh mention tonight (from both WS1EC's and KC1JMH-15's own ROUTES,
  independently) is consistently `W1BKW-15` (node), `-6` (BBS), `-5` (CHAT), `-10`
  (RMS). No line anywhere ever said `-3`.
- It comes from **stale data already sitting in `nodemap.json` before tonight's run
  started**: `AB1KI-15`'s own record (last actually crawled in January) has
  `netrom_ssids['W1BKW'] = 'W1BKW-3'`, and `W1BKW-3` sat in its `unexplored_neighbors`
  list from that same old crawl. `_load_unexplored_nodes()` correctly carried that
  forward at the start of tonight's run, before any fresh data existed to contradict
  it.
- `_resolve_ssid_consensus()` (the v1.8.5 code) saw exactly **one** vote for W1BKW's
  SSID across the whole file - AB1KI-15's stale `-3` - and a single vote is (correctly,
  by design) accepted as a clear consensus, since there's nothing to tie against. This
  isn't a bug in that logic; it's the intended behavior for a genuinely single-source
  node, just fed a stale single source here.
- W1BKW has **never** been successfully crawled in any session (no `W1BKW-15` key
  anywhere in `nodes_data`), so the v1.8.5 self-report override - which would have
  overridden this instantly, the same way it fixed KC1JMH-15 - had nothing to work
  with either.
- The actual **connect command self-corrected anyway**: `full_callsign` resolution
  inside `_connect_to_node()` used `netrom_ssid_map['W1BKW']`, which - hold on, this is
  still `'W1BKW-3'` from the stale vote at this point in the run, EXCEPT the log shows
  `Connection to W1BKW-3 (via 1 W1BKW-15 (port 1, direct))` - the port/SSID actually
  issued was `W1BKW-15`. That resolution came from `route_ssids`/ROUTES data read live
  at connect time from AB1KI-15's *current* session ROUTES answer while routing through
  it, which does show `-15` - so the live connect path is authoritative and correct;
  only the upfront queue label (`callsign`, used for `self.visited`, print statements,
  and the alternate-path requeue after failure) stayed stuck on the stale `W1BKW-3`
  spelling picked at queue-build time.

**Net effect:** the actual RF attempt correctly targeted `W1BKW-15` and failed on its
own genuine merits (unreachable this session, for whatever real reason - AB1KI-15's
own port 8 IP/AXIP path, same one WA1ZDA and KC1UIX-3 sit on, may simply be down or
congested). Nothing was mis-targeted on the wire. The cosmetic problem is real, though:
the *queue identity* used for display, `self.visited`, `self.freshly_crawled`, and the
post-failure requeue never gets normalized to the resolved SSID the way the connect
command itself does, so the same physical node can appear to be crawled under two
different spellings, print confusingly, and in principle dodge the `queued_paths`
dedup if some other parent's unexplored list separately lists `W1BKW-15` too.

**Self-healing note:** `AB1KI-15` itself was only ever used as an *intermediate relay*
tonight, not re-crawled as a top-level target, so its own stale `netrom_ssids['W1BKW']`
entry does not get corrected this run. But WS1EC and KC1JMH-15 were both freshly
re-crawled tonight and both independently show `-15` - once tonight's export merges,
the *next* run's consensus tally becomes 2 votes for `-15` vs. AB1KI-15's stale 1 vote
for `-3`, and resolves correctly without any code change.

**Recommended fix, not yet implemented (deploy freeze while the current crawl is
live):** after `full_callsign` is resolved in `_connect_to_node()`'s per-hop loop
(or right before `crawl_node()` records the queue attempt), normalize the tracking
`callsign` itself to the resolved SSID before using it for `self.visited`,
`self.freshly_crawled`, print statements, and the failure-requeue path - not just the
literal `C PORT CALLSIGN-SSID` command text. Would need care not to disturb the
existing SSID-mismatch handling in `crawl_node()`'s prompt-extraction block (which
already updates `netrom_ssid_map` from a *successful* connect's own banner - this is
about the *pre-connect, still-queued* identity instead).

---

## Deployment status as of 2026-08-25

`nodemap.py` on WS1EC is still at **v1.8.8**. Local `nodemap.py` has since gained the
`confirmed`/phantom-stub work above (untested against a real live crawl end-to-end,
only against replayed/synthetic scenarios) - **not deployed**, per KC1JMH's standing
instruction not to touch the node while a crawl is actively running. `nodemap-tui.py`
locally is at v1.1 (left/right arrow support for number fields) - committed and
pushed, also **not deployed** for the same reason.

Once the current `--resume` run is confirmed clean:
1. Deploy the queued `nodemap.py` (confirmed/phantom-stub work) and `nodemap-tui.py`
   (v1.1) changes together.
2. Decide on and implement the `nodemap-html.py` renderer wiring described above.
3. Decide whether the W1BKW-3-style queue-identity normalization is worth doing now
   or is low-priority enough to fold into a future pass (it's cosmetic/cache-hygiene,
   not currently costing incorrect RF behavior - the actual connect command already
   self-corrects).
