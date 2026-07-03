# Graph Report - Project_1_LLM  (2026-07-03)

## Corpus Check
- 7 files · ~6,231 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 84 nodes · 143 edges · 13 communities (7 shown, 6 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bb676b72`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]

## God Nodes (most connected - your core abstractions)
1. `Agent` - 23 edges
2. `Home Robot Language Agent Plan` - 12 edges
3. `Result` - 10 edges
4. `_pretty()` - 9 edges
5. `Robot` - 8 edges
6. `_normalize_text()` - 7 edges
7. `Implementation plan for [`agent.py`](agent.py)` - 7 edges
8. `Home robot language control` - 6 edges
9. `_words()` - 5 edges
10. `_contains_phrase()` - 5 edges

## Surprising Connections (you probably didn't know these)
- `Agent` --uses--> `Result`  [INFERRED]
  agent.py → home_robot_sim.py
- `interactive()` --calls--> `Agent`  [EXTRACTED]
  run.py → agent.py
- `run_suite()` --calls--> `Agent`  [EXTRACTED]
  run.py → agent.py

## Import Cycles
- None detected.

## Communities (13 total, 6 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.20
Nodes (4): _astar(), Result, Robot, WorldObject

### Community 2 - "Community 2"
Cohesion: 0.22
Nodes (8): Current state (the gap), Deliverable: [`WRITEUP.md`](WRITEUP.md) (~1 page), File change summary, Home Robot Language Agent Plan, Recommended architecture: observe-act loop (ReAct-style), Risk mitigations, Testing strategy, What the assignment requires

### Community 3 - "Community 3"
Cohesion: 0.60
Nodes (3): build_robot(), interactive(), run_suite()

### Community 4 - "Community 4"
Cohesion: 0.29
Nodes (7): 1. Gemini client setup, 2. System prompt (general, not test-specific), 3. Rewrite `Agent.handle`, 4. Multi-turn clarification (interactive mode, object choice only), 5. Safety and grounding guardrails (code as backstop, not primary defense), 6. Error handling, Implementation plan for [`agent.py`](agent.py)

### Community 5 - "Community 5"
Cohesion: 0.29
Nodes (6): Home robot language control, Running, Scoring, Submission, What to edit, What we expect

### Community 7 - "Community 7"
Cohesion: 0.33
Nodes (5): call_llm(), _contains_phrase(), Word-boundary phrase match so 'pill' does not match 'pillow'., Ask Gemini for the next action. Returns the raw model text, which should     be, _safe_json_loads()

### Community 9 - "Community 9"
Cohesion: 0.40
Nodes (4): Approach and design choices, Home Robot Agent Writeup, Tradeoffs, What can break and what I would improve with more time

## Knowledge Gaps
- **25 isolated node(s):** `WorldObject`, `Approach and design choices`, `Tradeoffs`, `What can break and what I would improve with more time`, `What to edit` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Agent` connect `Community 8` to `Community 0`, `Community 1`, `Community 3`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.154) - this node is a cross-community bridge._
- **Why does `Result` connect `Community 1` to `Community 8`, `Community 6`, `Community 7`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `Home Robot Language Agent Plan` connect `Community 2` to `Community 10`, `Community 11`, `Community 12`, `Community 4`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **What connects `Ask Gemini for the next action. Returns the raw model text, which should     be`, `Word-boundary phrase match so 'pill' does not match 'pillow'.`, `WorldObject` to the rest of the system?**
  _27 weakly-connected nodes found - possible documentation gaps or missing edges._