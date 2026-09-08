---
name: handoff
description: Compact the current conversation into a handoff document for another agent to pick up.
argument-hint: "What will the next session be used for?"
---

Write a handoff document summarising the current conversation so a fresh agent can continue the work. Use the user's requested destination or the host's designated deliverable directory; otherwise use the OS temporary directory. For a cross-device handoff, use an available user-designated synced location and include the saved path in the reply.

Include a "suggested skills" section naming relevant installed skills and how to locate them. The next agent should load their instructions through its host's available skill-loading or file-reading capability.

Do not duplicate content already captured in other artifacts (specs, plans, ADRs, issues, commits, diffs). Reference them by path or URL instead.

Redact any sensitive information, such as API keys, passwords, or personally identifiable information.

If the user passed arguments, treat them as a description of what the next session will focus on and tailor the doc accordingly.
