# Skill mechanics

The skill-specific branch of [writing-for-agents](SKILL.md): frontmatter, invocation, and router skills. Shared writing principles remain in `SKILL.md`.

## Frontmatter and invocation

Keep a non-empty `name` and `description` in every `SKILL.md`. The description identifies the task and when the skill applies; it is not an execution or approval policy. Removing the description is not a supported way to make a skill explicit-only.

Use the current host's skill schema. In Codex, normal automatic selection is the default. Preserve the existing invocation policy; change it to explicit-only only when the user explicitly requests that behavior. Codex stores this choice in `agents/openai.yaml`:

```yaml
policy:
  allow_implicit_invocation: false
```

This keeps the skill available through explicit `$skill-name` invocation without injecting it into the model context by default. Read the installed Codex `skill-creator` reference `references/openai_yaml.md` when editing UI metadata, dependencies, or invocation policy. Preserve unrelated fields.

Other hosts have their own controls. Claude Code and Grok may use `disable-model-invocation: true` in skill frontmatter; consult the installed host's documentation before changing such fields. Keep required descriptions and do not treat a host-specific flag as a portable substitute for another host's policy.

Authorization is separate from discovery. A discoverable skill can prepare a local draft and request any missing authorization immediately before an external mutation. An explicit-only skill does not itself grant permission to mutate external state.

## Dependencies and routers

Use a router when users benefit from one entry point for distinct workflows. Keep its routes short and give an existing target and a condition for loading it. A skill is text guidance, not necessarily a tool named `Skill`: use the host's available loading or file-reading capability.

Keep dependencies that the selected workflow actually needs available with the installation. Prefer resolvable skill-relative links for sibling references, and validate them after packaging. If a dependency is absent, report the missing capability and continue independent work within scope; do not invent an unavailable tool or silently install something.

Explicit-only policy controls automatic selection. Do not infer that a referenced file becomes unreadable to an authorized workflow. Shared guidance can live in a normal reference file with a clear pointer; it does not need its own discoverable skill.

## Splitting by invocation

Create another discoverable skill when it has a distinct task that needs independent selection. Each additional description has a context cost, so keep branches precise. Split substantial mode-specific details into references when that makes the entry point easier to follow. For splitting a sequence, use the completion-criterion guidance in `SKILL.md`.
