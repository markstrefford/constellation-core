---
title: SDLC for Reimagined Industries
purpose: How Claude Code should approach all development work in this repo
version: 3.3
---

# SDLC

This repository follows an AI-native, spec-anchored, compile-on-demand SDLC. The filesystem is the source of truth. Git history is the audit trail. Claude Code is the primary development agent. There is no external tracker (Jira, Notion, etc.) and none should be introduced without an ADR.

The entire SDLC working area lives under `/sdlc/`. Project code lives outside it.

## Principle

Capture is unstructured. Compilation gives material its shape. Execution acts on what's been compiled. The hierarchy — epic, story, task, decision, runbook — is emergent, not imposed. Nothing is pre-classified at capture; nothing is forced into a destination it doesn't fit.

## Glossary

Terms used throughout this document with specific meaning:

- **Operator** — the human in charge of the repo. References to "the operator decides X" mean a human approval is required.
- **Operator approval** — explicit affirmation in the chat session ("yes," "go ahead," "approved"), or an edit to the artefact in question that constitutes the approval. Silence is not approval. A previous session's approval does not carry forward to a new session.
- **Artefact** — any file under `/sdlc/work/` or `/sdlc/docs/` carrying frontmatter. Files under `/sdlc/raw/` are not artefacts; they are raw material.
- **Session** — a single Claude Code invocation, from start until the operator ends it.

## Directory layout

    /sdlc/
      raw/                    unstructured capture, no rules
      work/
        active/               things being worked on, any shape
        done/                 archived
      docs/
        architecture/         long-standing architectural docs
        strategy/             strategy docs
        decisions/            ADRs, point-in-time decisions
        runbooks/             operational guides
      SDLC.md                 this file
      STATE.md                current state, regenerated at session end
    /.claude/
      agents/                 sub-agent definitions (verifier, etc.)
    CLAUDE.md                 repo-level context, points to /sdlc/SDLC.md
    [project code lives at root or in src/, etc.]

`/sdlc/raw/` holds anything captured. `/sdlc/work/` holds compiled artefacts being acted on. `/sdlc/docs/` holds compiled artefacts that explain the system. Items move between these by being compiled, not by being filed.

`.claude/` and `CLAUDE.md` stay at repo root because Claude Code's auto-discovery expects them there. `CLAUDE.md` should contain a one-line pointer to `/sdlc/SDLC.md` so the workflow is discoverable from the root entry point.

**`/sdlc/work/done/` shape.** The default is one file per artefact, matching how it was structured in `/sdlc/work/active/`. For bulk historical imports (pre-SDLC done items, legacy changelog entries), a single consolidated file is acceptable — name it `done-historical.md` or similar. Going forward under the SDLC, new done items get their own files.

**Pre-existing content.** Files that pre-date the SDLC (legacy backlogs, changelogs, scratch docs) are treated as raw material to be compiled. They live where they currently live until compilation moves them. Compilation of legacy content follows the same rules as compilation of `/sdlc/raw/` items: each item becomes a compiled artefact in the right destination, or is discarded, or is parked. Nothing is moved without being compiled.

## File conventions

Files in `/sdlc/raw/` have no required structure. Free-form notes. They have no frontmatter, no id, no status.

Compiled artefacts (anything in `/sdlc/work/` or `/sdlc/docs/`) have YAML frontmatter:

    ---
    id: stable-id
    kind: task | story | epic | decision | runbook | strategy | architecture
    project: constellation | signalstrata | agent-os
    status: active | blocked | done       # for /sdlc/work/ items only
    autonomy: attended | review | auto    # for stories and tasks; see Autonomy section
    parent: optional-parent-id            # when relationships exist
    children: [optional-child-ids]        # when relationships exist
    sources: [paths-to-raw-sources]       # what this was compiled from
    blocker: [text]                       # required when status is blocked
    created: 2026-04-29
    updated: 2026-04-29
    verified-on: 2026-04-29               # for /sdlc/docs/ items
    tags: [optional]
    ---

Filename matches `id`. IDs are stable; never rename once assigned. The `kind` field describes what the artefact *is*, not what folder it sits in. The folder follows the kind.

`status` and `autonomy` are orthogonal. `status` describes lifecycle position (active, blocked, done). `autonomy` describes how much human oversight execution requires. A story can be `status: active, autonomy: review` — being worked on, with operator review required between verifier and done.

**Sequential numbering reflects hierarchy.** Stories under an epic carry a sequential `s<N>-` prefix in their `id` and filename. Tasks under a story carry the parent story's prefix *plus* a sequential `t<M>-` suffix: `s<N>-t<M>-<slug>`. `<N>` is the story's position in the epic's `children:` list (zero-indexed); `<M>` is the task's position under the story (zero-indexed). Examples: `s0-story-cc-audit`, `s1-t0-pin-cc-and-smoke-import`, `s2-t0-galaxy-graph-builder`, `s2-t1-galaxy-facade-on-graph`. The hierarchical encoding makes parentage visible at a glance and stable in `ls` output — tasks group under their story alphabetically. Inserting a story or task mid-list is a deliberate re-numbering operation: `children:` lists, `parent:` fields, and cross-references update together.

**Co-locate active work.** While an epic is in flight in `/sdlc/work/active/`, any new architecture docs, ADRs, runbooks, or strategy notes drafted as part of that epic cluster alongside it in `/sdlc/work/active/` — not in `/sdlc/docs/architecture/`, `/sdlc/docs/decisions/`, etc. They move to their semantic home (`/sdlc/docs/architecture/`, `/sdlc/docs/decisions/`, `/sdlc/docs/runbooks/`, `/sdlc/docs/strategy/`) at the same time the epic moves to `/sdlc/work/done/`. The principle: discoverability during iteration, structure once settled. Existing docs already in `/sdlc/docs/...` are not pulled back — the rule applies to new drafts.

## The verbs

Work is a small set of verbs applied as needed. They are not a sequence. You apply whichever fits.

### Capture
Drop material into `/sdlc/raw/`. Anywhere, anytime, any shape. No structure, no decisions. The only rule: don't lose the thought.

### Compile
Read `/sdlc/raw/` (and any other unstructured sources). For each item, decide what it should become and produce the compiled artefact. Possible outputs:

- a task in `/sdlc/work/active/` (one commit's worth of work)
- a story in `/sdlc/work/active/` (one coherent change worth specifying)
- an epic in `/sdlc/work/active/` (one strategic commitment)
- a decision in `/sdlc/docs/decisions/`
- an entry in `/sdlc/docs/strategy/` or `/sdlc/docs/architecture/`
- an addition to an existing artefact (link the source to it)
- discard

Compilation is a Claude operation. The operator approves the proposed compilation; Claude executes the file moves. The raw source is referenced in the `sources:` field of the compiled artefact and then deleted from `/sdlc/raw/` — once compiled, it's been absorbed.

Compilation replaces what older workflows called triage, strategic planning, and story planning. They were always the same operation at different scales.

**Summarise migrations at the high level.** Where source material describes a migration, the compiled artefact summarises the high-level shape (core logic, phases, modules, functions, methods) and enumerates them with a one-line description each. The operator signs off on the artefact, not the raw source. Faithful reproduction of long source content into the artefact is not required and usually undesirable — it bloats the artefact and creates two sources of truth.

### Plan
For an artefact in `/sdlc/work/active/` whose `kind` is `story` or `epic`, produce a task sequence. Each task entry must include:

- one-line outcome
- acceptance criteria
- test specification (defined before implementation)

Tasks are written as their own files in `/sdlc/work/active/` with `parent:` linking to the story. The plan is committed alongside the story. The operator reviews and edits the plan before execution.

Autonomy is set during planning. The operator assigns `autonomy:` to the story (which tasks inherit) and may override on individual tasks where the risk profile differs from the story.

### Execute
Act on a task. Tests first, then implementation. Claude writes the tests defined in the task spec, confirms they fail, then implements until they pass. No skipping tests. No "I'll add tests later." If the task spec didn't define tests, stop and update the plan.

When the task is complete: update `status: done`, commit with a message referencing the task id (e.g. `task-12: extract simulation engine module`), move the file to `/sdlc/work/done/`.

For tasks with `autonomy: review` or `autonomy: auto`, see the Autonomy section for what "complete" means and where the session pauses.

### Verify
Invoke the `verifier` sub-agent (defined in `.claude/agents/verifier.md`). It reads the spec, the plan, and the diff with no memory of how the implementation was built. It reports alignment, test coverage, architectural drift, and code smells.

The operator reviews the verifier output. Pass → continue. Fail → fix or kick the task back to active.

The verifier is non-negotiable. It is the single highest-leverage step in the loop and the most consistently skipped.

### File
At the end of any session that touches architecture, strategy, or operational behaviour, file the outputs back. Useful sessions don't dissipate, they compound.

- architectural decisions → `/sdlc/docs/decisions/NNNN-title.md` (ADR format)
- operational changes → update relevant runbook in `/sdlc/docs/runbooks/`
- strategy shifts → update or create in `/sdlc/docs/strategy/`
- repo-wide conventions → update `CLAUDE.md`
- spec divergences → update the story spec to match what was actually built

If a session produced a thinking artefact worth keeping (architectural reasoning, a useful framing), file it as a doc with `sources:` pointing to where it came from. The system gets denser over time.

If nothing is worth filing, skip. Don't write filler.

While an epic is in flight, drafts of these documents may co-locate in `/sdlc/work/active/` per the Co-locate active work convention; they move to `/sdlc/docs/...` at epic close.

### Refresh state
The final action of every working session: regenerate `/sdlc/STATE.md`. See the STATE.md section below.

## Autonomy

Autonomy describes how much human oversight a task requires during execution. It is a frontmatter field on stories and tasks; the operator sets it; Claude never escalates it.

Three levels:

- **`attended`** — operator is present in the session. Claude proposes plans and changes; operator approves before execution proceeds. Default.
- **`review`** — Claude executes through to the verifier and pauses. The task does not move to `done` until the operator reviews the verifier output and the diff and approves. Suitable for unattended runs where the operator will review in the morning.
- **`auto`** — Claude executes through to the verifier. If the verifier passes, the task moves to `done` without operator intervention. If the verifier fails, the task pauses for the operator. Suitable for purely mechanical, low-risk work that the operator does not need to see individually.

**Resolution order.** When determining a task's autonomy:

1. The task's own `autonomy:` field, if set.
2. The parent story's `autonomy:` field, if set.
3. The SDLC default: `attended`.

Setting autonomy at the story level is the common case. Per-task override exists for the occasional load-bearing task in an otherwise mechanical story (set the override to `attended`), or the occasional mechanical task in an otherwise risky story (set the override to `review` or `auto`).

**Constraints.** The following must never be `auto`:

- Tasks that introduce or change architectural decisions.
- Tasks that affect public interfaces, module boundaries, or seams between major components.
- Tasks that delete or move existing code outside the immediate task scope.
- Tasks where the verifier itself is being modified.

The operator may set these to `attended` or `review` but not `auto`. If Claude believes a task being executed is one of these and was set to `auto`, it pauses and reports.

**Behaviour at pause.** When a `review` task pauses, Claude updates the task with `status: active` (still active, awaiting review) and writes a short note in the task body summarising what was done and what the verifier reported. The operator's next action — approve and mark done, or kick back to active for changes — moves the task accordingly.

## STATE.md — bridge to thinking sessions

`/sdlc/STATE.md` exists because Claude in the chat app cannot read the repo directly. The operator pastes `STATE.md` at the start of any conversation in the chat app that involves this repo. This is the only sanctioned bridge between repo state and architectural conversations elsewhere; do not introduce others without an ADR.

`/sdlc/STATE.md` is regenerated at the end of every Claude Code session and must contain exactly:

    # State — last updated [ISO date]
    
    **Active focus:** [one line — what's currently being worked on]
    **Last completed:** [id — one line]
    **Next:** [id — one line]
    
    ## Open questions
    - bullet
    - bullet

Rules:

- Keep `STATE.md` under 30 lines. If it grows beyond a screen it stops getting pasted.
- "Active focus" is whatever shape best describes the current work — could be a story, a task, an epic, a doc compilation, anything. Don't force it into a typed slot.
- The "Open questions" field is the highest-value content. If Claude Code hits something during execution that needs architectural judgment, it goes here. Empty is fine; padding is not.
- When `STATE.md` has no open questions, the operator does not need a thinking session — they need to be in Claude Code executing.

When GitHub MCP becomes reliable in the chat app, `STATE.md` and this section can be removed. The workflow does not change.

## Status discipline

- An artefact in `/sdlc/work/active/` is `active` if it's being worked on, `blocked` with a `blocker:` field if it isn't, `done` only when complete.
- A task is `done` only when tests pass, the diff is committed, and the verifier has signed off. For `review` tasks, additionally the operator must have approved.
- A story is `done` when all its child tasks are done and the spec's acceptance criteria are met.
- Done artefacts move from `/sdlc/work/active/` to `/sdlc/work/done/`.
- Doc artefacts in `/sdlc/docs/` carry `verified-on:` rather than status. They're either current (verified recently) or stale (not).

## Hard rules for Claude Code

1. **Read `/sdlc/SDLC.md` and `CLAUDE.md` at the start of every session.** No exceptions.
2. **Never start coding without a task artefact.** If the operator asks for code directly, propose compiling it into a task first.
3. **Never write implementation before tests.** If there's no test spec, update the plan first.
4. **Never mark a task done without verifier sign-off.** For `review` tasks, additionally require operator approval.
5. **Never edit an artefact's `id` field.** IDs are stable.
6. **Never introduce an external tracker.** If the operator suggests it, require an ADR documenting the decision.
7. **Never skip filing for architectural changes.** The next session depends on it.
8. **Never end a working session without regenerating `/sdlc/STATE.md`.**
9. **Never let `/sdlc/raw/` accumulate beyond 20 items without prompting the operator to compile.**
10. **Never delete from `/sdlc/raw/` without first producing a compiled artefact that references it as a source.** Compilation absorbs raw material; it doesn't discard it silently.
11. **Trust the document.** If a question can be answered by reading `/sdlc/SDLC.md`, `CLAUDE.md`, or any artefact already in the repo, read it and proceed. Do not ask the operator. Asking questions the repo answers is a failure mode, not a courtesy.
12. **Trust the operator's instruction.** When the operator gives a clear directive ("do X to all Y"), execute it. Do not ask for re-confirmation of the directive itself. Ask only if a specific item genuinely needs disambiguation, and ask once — not per item.
13. **No re-asking.** If the operator has answered a question once in this session, do not ask it again in any phrasing. Re-asking signals the prior answer wasn't trusted or wasn't retained. If genuinely unsure, state the prior answer back and confirm — do not start over.
14. **Never escalate autonomy.** A task marked `attended` does not become `review` because Claude judges it safe. The operator sets autonomy. If Claude believes the assigned autonomy is wrong, it raises this as an open question, not a unilateral change.
15. **Never run `auto` on constrained categories.** The constraints in the Autonomy section are absolute. If a task in `auto` turns out to fall in a constrained category, pause and report.

## What stays human

The operator (Mark) decides:

- compilation outcomes — Claude proposes, operator approves
- plan approval — Claude proposes, operator edits, operator approves
- autonomy levels — Claude never sets or changes these
- verifier sign-off on `review` tasks — Claude reports, operator decides
- `CLAUDE.md` edits — these encode opinions and must sound like the operator
- ADRs — Claude can draft, operator must approve

## What runs without further approval

Within an approved task spec, Claude executes freely:

- writing tests as specified
- writing implementation against tests
- iterating on test failures
- updating documentation when behaviour changes
- generating runbook updates
- regenerating `/sdlc/STATE.md`
- proposing the next compilation, plan, or task
- on `auto` tasks that pass verification: marking the task done and moving it to `/sdlc/work/done/`

## Scaling note

This SDLC works for a single operator with AI agents. When a second human joins the loop, the substrate may need to change (filesystem → tracker), but the workflow stays identical: capture raw, compile into shape, plan when shape requires it, execute with tests-first, verify with fresh context, file outputs back, refresh state on exit. Migrating substrate is a one-time mechanical change; migrating workflow would be a rebuild.

## References

External thinking that informed this SDLC:

- Spec-Driven Development (arXiv 2602.00180) — spec-anchored is the practical middle between vibe coding and full waterfall.
- Anthropic internal practice — fresh-context PR review by a separate Claude instance.
- Augment Code's Coordinator / Implementor / Verifier pattern.
- Andrej Karpathy's LLM-managed wiki pattern — raw sources compiled by an LLM into structured artefacts; structure emerges from content rather than being imposed upfront. This SDLC adapts that pattern from knowledge management to development work.
- Loose-coupling, shared-edges principle from Reimagined Industries' Agent OS architecture, applied to the workflow itself.