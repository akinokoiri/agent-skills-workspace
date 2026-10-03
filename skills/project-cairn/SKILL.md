---
name: project-cairn
description: Maintain useful project knowledge and current handoffs; distill, prune, or audit lessons, decisions, and reusable references in AGENTS/CLAUDE/cairn docs. Also use to initialize Cairn or move validated experience to a configured knowledge base.
---

# Project Cairn

Help the next task find the right starting point, make better decisions, and avoid rediscovering non-obvious facts. Existing project formats and the user's scope take precedence. A completed task need not produce a new lesson.

## Choose the relevant route

- Record progress, summarize experience, or clean up project knowledge: [maintenance](references/maintenance.md). It defines what earns retention and where it belongs.
- Audit usefulness, stale conclusions, duplication, or navigation: [audit](references/audit.md).
- Initialize or retrofit Cairn: [init](references/init.md); update an existing installation's schema only when requested: [upgrade](references/upgrade.md).
- Reuse configured external knowledge: [consume](references/consume.md).
- Publish reusable knowledge to a provider: [graduation](references/graduation.md), then only that provider's reference.
- Close an exploration branch: [branch closure](references/branch-closure.md).
- Resolve actual schema questions: [frontmatter](references/frontmatter.md). Chinese terminology: [glossary](references/zh-glossary.md).

Read the route needed for the task; do not load the entire reference set.

## Boundaries

This is a documentation workflow, not a CLI or automatic chat-end hook. Update local records within the user's authorization; discussion and read-only review do not authorize writes. External provider writes require human confirmation under the graduation route.

Keep current state in one maintained entry, reusable knowledge in its owning topic, and detailed runs in task artifacts. Use existing files before creating another topic or process. Changes to a method should replace its obsolete guidance and retain a short revision pointer, rather than accumulate competing “current” sections.

Templates are optional starting shapes, not a requirement to fill every section. Preserve existing human provenance and project conventions; source artifacts and runnable deliverables stay in the project, outside cairn.

Scripts: shell helpers need bash (Windows: WSL/Git Bash); Python helpers run directly, with PyYAML needed by notion-graduate-batch.py. Use them only for the applicable route.
