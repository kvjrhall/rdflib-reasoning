# Contradiction Diagnostics

Contradiction diagnostics are rule outputs that report an inconsistent pattern
without adding an ordinary inferred triple to the graph. They are modeled as
diagnostic events so callers can choose a handling policy.

The default construction path raises when a contradiction is recorded. Other
recorders can retain contradiction records without raising, warn while
continuing, or drop retained records when only immediate signaling matters.

Contradiction rules are useful when a ruleset should flag bad states while
leaving application policy to the caller. The engine can say which rule fired
and which facts witnessed the diagnostic; it does not decide whether the
application should repair the graph, reject the update, or continue collecting
evidence.

Contradiction records can also be reconstructed into proof-shaped explanations.
That gives users and review tools the same inspection path used for positive
inferences, while preserving the distinction between inferred facts and
diagnostic findings.

Related guides:

- [Enable contradiction diagnostics](../how-to/enable-contradiction-diagnostics.md)
- [Contradiction rules tutorial](../tutorials/notebooks/demo-contradiction-rules.ipynb)
- [Generated contradiction rule API](../autoapi/engine/rulesets/owl2_rl_contradictions/index)
