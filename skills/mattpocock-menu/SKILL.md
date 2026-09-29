---
name: mattpocock-menu
description: "Router for the mattpocock/skills collection. Lists what each skill does and recommends which to invoke for a given situation. Use when the user is unsure which skill to use, or says 'menu', 'help', 'which skill', or 'what can these skills do'."
disable-model-invocation: true
argument-hint: "What are you trying to do? (optional)"
---

You are a router for the mattpocock/skills collection installed alongside you. Your only job is to help the user pick the right skill.

When invoked (or when the user asks "which skill should I use", "what can these skills do", "menu", or "help with skills"):

1. Present the catalog below.
2. If the user described a situation, recommend the single best skill and tell them it is **user-invoked** (they must invoke it by name with the Skill tool, e.g. `/grill-me`) — except the model-invoked skills, which can fire on their own.
3. Keep it short. Point, don't lecture.

## User-invoked skills (you must name them to run)

- **ask-matt** — get Matt Pocock's opinion/style guidance on a TS/engineering question. Trigger: "ask matt…", "what would Matt say about X".
- **grill-me** — relentlessly interview the user to stress-test an idea, plan, or understanding. Trigger: "grill me", "challenge my plan", "test my understanding".
- **grill-with-docs** — same as grill-me, but also produces ADRs and a glossary as you go. Trigger: "grill and write docs".
- **handoff** — compress the conversation into a handoff doc for another agent. Trigger: "handoff", "write a handoff doc".
- **implement** — implement a piece of work from a spec or tickets. Trigger: "/implement", "implement this spec".
- **improve-codebase-architecture** — scan the codebase for deepening opportunities and present an HTML report. Trigger: "improve architecture", "find shallow modules".
- **setup-matt-pocock-skills** — scaffold the repo config for the engineering skills (issue tracker, triage labels, domain doc layout). Run once first. Trigger: "setup skills", "initialise skill config".
- **teach** — teach the user a skill or concept across multiple sessions. Trigger: "teach me X".
- **to-questionnaire** — turn a decision you can't answer alone into a questionnaire for someone else. Trigger: "make a questionnaire".
- **to-spec** — turn the conversation into a spec and publish it to the issue tracker. Trigger: "to spec", "produce a spec".
- **to-tickets** — break a plan/spec into tracer-bullet tickets. Trigger: "to tickets", "break this into tickets".
- **triage** — triage issues and external PRs (categorise, verify, write agent briefs). Trigger: "triage", "triage #42".
- **wait-what** — re-pitch the last message the user didn't follow, in plain simplified language. Trigger: "wait, what?", "say that again".
- **wayfinder** — plan a huge chunk of work as a map of decision tickets, resolved one at a time. Trigger: "wayfind", "plan this big task".

## Model-invoked skills (auto-trigger by description; also callable by name)

- **code-review** — review a change.
- **codebase-design** — design with the deep/shallow module vocabulary.
- **diagnosing-bugs** — systematic bug diagnosis.
- **domain-modeling** — sharpen the domain glossary and ADRs.
- **grilling** — the interview engine (called inside grill-me / grill-with-docs).
- **prototype** — generate a clickable logic/UI prototype.
- **research** — dispatch a sub-agent for external research.
- **resolving-merge-conflicts** — resolve merge conflicts.
- **tdd** — test-driven development.
- **wizard** — generate an interactive bash wizard for setup steps.
- **writing-for-agents** — how to write docs for agents (reference used by other skills).
