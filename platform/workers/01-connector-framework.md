# Connector Framework

> Status: **Foundational** · Owner: Platform / Data Engineering · Cycle: 6
> Implements [ADR-0011](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md).
> Companion to [00-ingestion-architecture.md](00-ingestion-architecture.md) (the generic
> pipeline). This document specifies the **source-specific boundary**: the single interface
> every source must satisfy, so that adding SharePoint, SAP, Exchange, a file share, or a
> future source is **"write a connector + pass the conformance suite," not re-architect the
> platform.** It consumes the ACL-mapping obligations from
> [Permissions §5, §9, §11](../permissions/00-authorization-model.md) and the versioned-write
> rules from [Storage §3, §8](../storage/00-storage-architecture.md) — it does not re-open them.

The connector is the **only** place the platform knows a source exists. Everything above it
(chunking, embedding, retrieval, authorization decision, isolation) is source-agnostic by
design. The whole "new domain = pack, not redesign" bet
([Vision §3](../architecture/00-vision-and-principles.md)) rests on this boundary being
**narrow, uniform, and conformance-gated**. Get the interface right and the platform grows by
addition; get it leaky and every new source becomes a special case that erodes the core.

It co-owns risk **R6** (connector fragility → source API changes break ingestion/permissions)
and is the **implementation** side of **R1** (permission-model mismatch), whose *design*
mitigation ([Permissions](../permissions/00-authorization-model.md)) is only as good as each
connector's `map_acl`.

---

## 1. The connector contract (one interface, six methods)

Every source implements the **same** interface behind a narrow **`Connector` port**. The
ingestion DAG ([ingestion §2](00-ingestion-architecture.md)) calls only these methods; it
never contains source-specific branches.

```
Connector (port):
  # --- discovery & fetch (DAG stage 1) ---
  list_items(scope, since=None) -> [ItemRef]        # full crawl (since=None) or delta
  fetch(item_ref)              -> RawItem            # bytes + native metadata + source version
  # --- authorization mapping (DAG stage 3) — the hardest job ---
  map_acl(raw_item)            -> CanonicalACL       # {allow[], deny[], labels, acl_confidence}
  # --- freshness (Workers §7) ---
  subscribe_changes(scope)     -> ChangeFeed         # webhook/change-doc/audit registration
  list_principal_changes(since)-> [PrincipalDelta]   # group/role membership deltas → identity graph
  # --- lifecycle ---
  capabilities()               -> Capabilities       # declared max acl_confidence, content types, freshness mode
```

- `map_acl` and `list_principal_changes` are the two methods
  [Permissions §5.5](../permissions/00-authorization-model.md) named as the mapping contract;
  this document is where they get their full shape and their **fixtures**.
- `capabilities()` is a **declaration the platform verifies, never trusts** (§5): a connector
  may *declare* it can achieve `exact` confidence for SharePoint item-level perms — the
  conformance suite proves it, and a failed proof quarantines the source.
- Everything the connector returns is **version-stamped** (`source_item_version` — etag,
  mtime, change-doc number) so the DAG's writes are idempotent and version-keyed
  ([Storage §3](../storage/00-storage-architecture.md), W1).

### 1.1 What the contract deliberately does NOT expose

- **No "search the source" method.** The platform never queries the source at retrieval time
  on the shared path — that is the native-per-source-authz anti-pattern
  [Permissions §1](../permissions/00-authorization-model.md) rejects. (The [§6](#6-delegatedon-behalf-of-connectors-the-quarantine-escape-hatch)
  OBO escape hatch is the narrow, opt-in exception.)
- **No "write to the source" method.** Ingestion is **read-only** toward sources. A connector
  never mutates the customer's system; least privilege (§7) enforces read-only credentials.
- **No way to emit a chunk to the shared index below `exact` confidence.** The type system /
  persist stage routes sub-`exact` output to quarantine ([ingestion §7.3](00-ingestion-architecture.md));
  the connector cannot bypass it.

---

## 2. `map_acl` — the correctness heart (R1 implementation)

`map_acl` lowers a source's native, rich, subtly-incompatible access model into the canonical
`{allow[], deny[], labels, acl_confidence}` ([Permissions §2.2](../permissions/00-authorization-model.md)).
This is where a leak is won or lost. The framework gives every connector the **same
scaffolding** so the hard judgment is concentrated and reviewable:

### 2.1 Per-source mapping obligations (from Permissions §5, restated as connector duties)

| Source | Must do | `acl_confidence = exact` only when |
|--------|---------|-----------------------------------|
| **SharePoint / M365** | Resolve **item-level** perms (respect broken inheritance); map Entra users/groups → CPI by **objectId**; sharing links → explicit grants; sensitivity labels → `labels.sensitivity` | Item-level permissions were fully read (not inherited-assumed) |
| **SAP** | Emit **role/authorization/org-unit principals** (`role:FI_AP_DISPLAY`, `orgunit:CC1000`) — SAP has no document ACL | The requirement is fully expressible as principal set-membership |
| **Exchange / Email** | Grant to **mailbox owner + explicit delegates**; per-**message** ACL (not per-thread); shared-mailbox delegate set | Ownership + delegation fully resolved |
| **File share (NTFS/POSIX)** | Map SIDs/UIDs/GIDs → CPI; **honor deny ACEs** → `acl.deny`; expand inheritance to the *effective* ACL | Effective ACL fully computed |

### 2.2 The three rules that keep `map_acl` honest

1. **Stable IDs only** ([Permissions §2.1](../permissions/00-authorization-model.md)): map by
   the source's non-reusable identifier (Entra objectId, AD SID, SAP role name) — **never**
   display name or email. Reused names silently transfer access; this is the single most
   common normalization leak. The framework provides a `to_cpi(source, type, stable_id)`
   helper so a connector cannot accidentally CPI a display name.
2. **Deny is never dropped.** NTFS/explicit denies map to `acl.deny` and win at decision time
   ([Permissions §3.1](../permissions/00-authorization-model.md)). A connector that cannot
   read denies must declare lower confidence, not omit them.
3. **Confidence is a floor, computed per item, and monotonic-down.** If any part of an item's
   ACL is unresolvable, the *item's* confidence drops to `approximate`/`unknown` →
   [Permissions §3](../permissions/00-authorization-model.md) **denies** it on the shared path
   → [ingestion §7.3](00-ingestion-architecture.md) quarantines it. A connector may **never**
   raise confidence to make an item ingestible (§5 blocks it).

### 2.3 Why the framework, not the connector, owns the CPI + predicate shape

The connector produces `{allow[], deny[], labels, acl_confidence}` and **nothing more** — it
never builds the query predicate, never expands nested groups (the identity graph does that at
query time, [Permissions §4.2](../permissions/00-authorization-model.md)), never decides
tenancy. This keeps the connector's surface small (easier to review for the R1 leak) and means
a change to the decision predicate or the storage filter never touches connector code.

---

## 3. Versioning & fault isolation (R6)

Sources change their APIs; that must degrade *one* connector, never the platform.

- **Connectors are independently versioned and deployed.** Each ships as a versioned unit
  (semver) with its fixture corpus and conformance suite (§5). A SharePoint API change is a
  new SharePoint-connector version; SAP/Exchange/file-share ingestion is untouched.
- **Schema-validated boundary.** Everything a connector returns (`RawItem`, `CanonicalACL`,
  `PrincipalDelta`) is schema-validated at the port (validate-at-system-boundaries: never
  trust external data). A connector returning a malformed ACL fails the item to
  the DLQ ([ingestion §8](00-ingestion-architecture.md)) — it can **never** write a malformed
  ACL into the store.
- **Capability negotiation.** `capabilities()` lets the platform adapt: a source without a
  webhook facility falls back to poll + reconciliation crawl ([ingestion §7.4](00-ingestion-architecture.md));
  a source that can't read denies is capped at lower confidence. Degradation is **declared and
  handled**, never a silent gap.
- **The conformance canary (§5) catches drift.** When a source API change quietly alters ACL
  semantics, the periodic production canary fails and **auto-quarantines** the source before it
  can serve a wrong answer — R6 turned from "silent leak" into "loud, contained alarm."

---

## 4. Change detection — feeding freshness (R3 write half)

Each connector implements change detection in its source's native idiom, normalized to two
platform-level signals ([ingestion §7](00-ingestion-architecture.md) consumes both):

| Source | Content/ACL change signal | Principal change signal |
|--------|---------------------------|-------------------------|
| SharePoint / M365 | Microsoft Graph **change notifications / delta query** | Entra group-membership deltas (SCIM + Graph) |
| SAP | **Change documents** (CDHDR/CDPOS), IDoc/event | Role-assignment change docs |
| Exchange | Graph mail **delta / subscriptions** | Mailbox-delegate changes |
| File share | File-system **audit / USN journal / inotify** | Directory-group (AD) deltas |

- **Webhook-primary, reconcile-backstop.** Push signals meet the P0/P1 SLA
  ([ingestion §4.2](00-ingestion-architecture.md)); the periodic reconciliation crawl
  ([ingestion §7.4](00-ingestion-architecture.md)) guarantees convergence when a feed drops
  events. Neither alone is sufficient — together they are.
- **`list_principal_changes` updates the identity graph, not chunks** — a membership change is
  one small graph write + decision-cache invalidation, not a chunk-ACL re-tag storm
  ([ingestion §7.2](00-ingestion-architecture.md), [Permissions §8](../permissions/00-authorization-model.md)).
- **Restriction changes are P0.** A connector classifies a delta as *restricting* (deny added,
  sharing revoked, item newly restricted) → P0, vs. *widening/neutral* → P1
  ([ingestion §4.2](00-ingestion-architecture.md)), so the safety-critical change is fastest.

---

## 5. The conformance suite is the production gate (R1/R6 primary control)

**No connector serves shared-path retrieval until it passes the permission-conformance suite**
([Permissions §11](../permissions/00-authorization-model.md)). This document makes that gate a
**concrete deliverable of every connector** and wires it into CI + a production canary.

Each connector ships a **fixture corpus** in its source, with a known ground-truth permission
matrix; the suite asserts the platform reproduces it **exactly**:

| Test | Asserts | Owning risk |
|------|---------|-------------|
| Positive | User with access retrieves the item | correctness |
| Negative | User **without** access gets **zero** chunks (no snippet/citation leak) | R1 |
| Deny-precedence | Explicit deny beats an allow-granting group | R1 |
| Nested group | Access via a group-of-groups resolves | R1 |
| Broken inheritance | Unique-perm item ignores parent ACL | R1 |
| Revocation freshness | User removed from a group loses access **within SLA** | R3 |
| Re-share freshness | Newly restricted item stops being served **within SLA** | R3 |
| Ambiguity → deny | An `approximate` item is never served on the shared path | R1 |
| Cross-tenant | No chunk of tenant A ever returned to tenant B | R4 |
| Label gate | A `confidential`, ACL-permitted item honors label policy | §7 Permissions |

- **Runs in CI** (gate on merge — no connector version ships red) **and as a periodic
  production canary** (synthetic users vs. a synthetic corpus per source) to catch source-API
  drift (R6). A canary failure **auto-quarantines** the source ([ingestion §10](00-ingestion-architecture.md)).
- **Declared confidence is verified, not trusted** (§1, §2.2): the "Ambiguity → deny" and
  "Negative" tests together prove the connector cannot leak a sub-`exact` item.
- The suite is **versioned with the connector**, so a connector change and its proof move
  together — the executable form of "faithfully normalized."

---

## 6. Delegated / on-behalf-of connectors (the quarantine escape hatch)

For the narrow, highest-sensitivity classes the canonical model can't express *exactly*
([Permissions §9, §10](../permissions/00-authorization-model.md)) — SAP field-level authz,
attribute/row-level rules — a connector may run in **on-behalf-of** mode: it reads **as the
user** at query time (Graph OBO, SAP principal propagation), so the **source itself** is the
authority.

- **Strongest correctness, worst latency/availability.** It reintroduces the live source call
  normalization was chosen to avoid, so it is **opt-in per class**, routed through the
  [Storage §5.3](../storage/00-storage-architecture.md) Isolated/quarantine tier — never the
  default shared path.
- This is where [Permissions §9 tier-3](../permissions/00-authorization-model.md) and
  [Storage §5.3](../storage/00-storage-architecture.md) quarantine physically land: a
  dedicated, per-user or per-class path, accepting latency to keep the platform honest instead
  of faking a mapping.

---

## 7. Connector security posture (least privilege, W6)

- **Read-only source credentials, per tenant, per connector** ([Security §5](../security/00-security-architecture.md)):
  fetched from the secret manager at task time, never in an image or config
  ([Security §7](../security/00-security-architecture.md) secrets management). A connector
  cannot write to a source (§1.1).
- **Scoped to its stage's worker pool** ([ingestion §9](00-ingestion-architecture.md),
  `WorkerRegistry`): the fetch credential and the store-write credential are in different
  pools — a compromised connector can read a source but cannot rewrite an ACL, or vice versa.
- **Egress-controlled**: a connector talks to its one source + the platform's stores/Model
  Gateway, nothing else (Principle 1, in-boundary). Embeddings of source content never leave
  the boundary.
- **Every fetch + `map_acl` result is audited** with the connector version + trace_id
  ([ingestion §9](00-ingestion-architecture.md)), so a later "why was this ACL wrong?"
  investigation is answerable.

---

## 8. Trade-offs

- **Uniform narrow interface vs. per-source richness.** Six methods can't express every source
  nuance as ergonomically as a bespoke integration — but a uniform boundary is what makes the
  platform grow by addition and keeps the R1 leak surface small and reviewable. (§1.)
- **Normalize-at-ingest vs. native-at-query.** The connector bears the full burden of proving
  `map_acl` faithful (the §5 suite) to buy filter-during-retrieval and freedom from hot-path
  source calls; the OBO escape hatch (§6) pays the latency where exactness demands it. (§2, §6.)
- **Conformance gate cost vs. safety.** Requiring a fixture corpus + passing suite per
  connector slows a new source's onboarding — deliberately. A source that can't prove its ACL
  mapping is a source that shouldn't serve regulated content. (§5.)
- **Webhook + reconcile vs. one mechanism.** Running both push and periodic crawl doubles the
  change-detection machinery, bought because each alone has a gap (feeds drop; polling is too
  slow for P0). (§4.)
- **Confidence-floor quarantine vs. recall.** Refusing sub-`exact` items on the shared path
  costs recall for hard sources (SAP field-level), but a leaked document costs far more than a
  "no accessible information." (§2.2, §6.)

## 9. Alternatives considered

| Alternative | Verdict |
|-------------|---------|
| **Bespoke integration per source** (no uniform contract) | Rejected: every source becomes a special case; the source-agnostic core erodes; R1 leak surface multiplies. (§1) |
| **Connector builds the query predicate / expands groups** | Rejected: bloats the connector surface and couples it to the decision model; the identity graph expands groups at query time, the connector only emits `{allow,deny,labels,confidence}`. (§2.3) |
| **Trust `capabilities()` declared confidence** | Rejected: declared ≠ proven; the conformance suite verifies it and quarantines on failure. (§1, §5) |
| **Map ACLs by email/display name** | Rejected: reused/reassigned names silently transfer access; stable IDs only. (§2.2) |
| **Native per-source authz at query time as the default** | Rejected: N live source calls per query, availability coupled to sources; kept only as the §6 OBO escape hatch. |
| **Skip the conformance gate for "trusted" sources** | Rejected: source-API drift (R6) makes yesterday's trust today's leak; the canary re-proves continuously. (§5) |
| **Write-back to sources** (bidirectional) | Rejected for the platform's read/retrieval mission: ingestion is read-only; write-back is a different product with a different risk model. (§1.1) |

## 10. Future scalability

- **New source** = implement the six-method `Connector` port + ship a fixture corpus that
  passes the §5 suite. **Zero** change to the DAG, queue, decision predicate, storage schema,
  or retrieval. This is the concrete proof of "new domain = pack, not redesign."
- **Source changes its API** = a new connector version + its suite; other connectors and the
  core are untouched; the canary catches semantic drift. (§3.)
- **New identity provider** = a new `list_principal_changes` feed into the identity graph; CPI
  namespace and predicate unchanged ([Permissions §14](../permissions/00-authorization-model.md)). (§4.)
- **New freshness mechanism** (a source ships a better change feed) = swap the connector's
  `subscribe_changes`; the P0/P1 classification and the SLA machinery are unchanged. (§4.)
- **Community / third-party connectors** = the narrow, schema-validated, conformance-gated
  contract makes a third-party connector safe to admit: it **cannot** leak past the §5 gate or
  write a malformed ACL past the §3 schema boundary, regardless of who wrote it.

## Related

- [Ingestion Architecture §2 (DAG), §4 (priority), §7 (change detection), §9 (security), §10 (canary)](00-ingestion-architecture.md).
- [Permissions §5 (per-source mapping), §9 (quarantine), §10 (OBO), §11 (conformance suite)](../permissions/00-authorization-model.md).
- [Storage §3 (versioned upsert), §5.3 (quarantine tier), §8 (migration)](../storage/00-storage-architecture.md).
- [Security §5 (isolation), §6 (secrets)](../security/00-security-architecture.md).
- [ADR-0011 — Ingestion workers & connector framework](../architecture/adr/ADR-0011-ingestion-workers-and-connector-framework.md).
- [ADR-0005 — WorkerRegistry least-privilege](../architecture/adr/ADR-0005-template-consolidation-council.md) (the runtime the connector's stages run on).
- Downstream: [Governance](../governance/) (per-connector cost, conformance-audit policy),
  [Deployment](../deployment/) (connector deployment/versioning, secret provisioning).
