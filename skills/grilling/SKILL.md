---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Stress-test the user's plan until you share enough understanding to make the decisions in scope. Infer that scope from the request; clarify only when it materially changes the interview. Map dependencies as a **design tree**, keeping unrelated decisions outside the session.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask now without guessing at answers you haven't heard yet. Ask a small, coherent batch of the most consequential questions, sized to the user's answers and the host's question interface. Number each question and offer a recommendation when there is enough evidence, with its reason and trade-off. Wait for the user's answers before asking dependent questions; a recommendation is not a user decision.

Use the host's question interface when appropriate; otherwise a round can look like this:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Find accessible environmental facts yourself. Delegate an independent lookup only when sub-agents are available and parallel work materially helps; handle small or coupled lookups directly. While a lookup runs, continue questions that do not depend on it. Ask for missing facts only when they matter and cannot be obtained through authorized access. Decisions remain the user's unless they explicitly delegate a choice within stated bounds.

## When the user cannot answer

Treat "I don't know" as information. Work out whether the obstacle is abstract wording, missing experience or facts, a difficult trade-off, or no meaningful preference. Use the conversation to choose the next approach rather than requiring another diagnostic questionnaire.

- Lower the abstraction: use a concrete situation, comparable examples, a counterexample, or a small optional trial. Ask what appeals to the user and why; vary one relevant dimension where practical.
- Keep proxy answers as tentative clues. Liking apples over bananas does not establish a preference for red over yellow: taste or convenience may explain it. Check the actual design choice using comparable alternatives before relying on the inference.
- Distinguish explicit user decisions, tentative inferences, and unresolved questions. Test important inferences with a different example or counterexample; surface contradictory evidence and revise the hypothesis. Avoid leading questions that merely confirm your recommendation.
- Allow "no preference", deferral, or an explicitly delegated default. For a low-cost reversible choice, propose a trial and a way to evaluate it; proceed only within existing authorization. For consequential unresolved choices, explain what evidence or experience is missing and pause only the dependent decision.
- If reframing adds no useful evidence, summarize the uncertainty and offer a concrete next step. Repetition or elapsed time does not turn uncertainty into agreement.

## Completion

Finish when the important decisions within the agreed scope are resolved or explicitly deferred, and remaining assumptions and their consequences are visible. Aim for enough precision to support the next action; do not require certainty about every possible branch. Summarize decisions separately from hypotheses and open questions, and have the user confirm the shared understanding before implementing the plan. If they already approved that plan or delegated a bounded choice, reuse that authorization without asking again; substantive changes still need their decision. A user request to stop or narrow the interview takes priority.
