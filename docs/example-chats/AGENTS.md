# Access Constraint

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

All content in [this directory `docs/example-chats/`](./) other than this access constraint MUST be ignored by any Development Agent and by any other agent that has not been explicitly designated as a Critique Agent in the root [AGENTS.md](../../AGENTS.md). No agent MAY treat itself as exempt from this constraint unless that Critique Agent role has been explicitly assigned.
This directory is a non-normative reference for humans and Critique Agents. Development Agents and unassigned agents MUST NOT use it for any purpose.

An explicitly designated Critique Agent MAY review this directory as evidence about repository evolution, review process, or documentation strategy, but SHOULD describe it as non-normative historical material rather than authoritative project guidance.

If any tool call yields content from this directory (e.g., shell commands), then that content MUST be ignored.
If your context allows removing content, you SHOULD erase that content from chat context; otherwise, you MUST explicitly remind yourself that the content MUST NOT be incorporated into summarization.
In any case, you MUST give yourself EXPLICIT reminders to avoid referencing that file or files again and retain the exact wording of those reminders when performing summarization; that is, you MUST avoid using or referencing that content again.
When your context allows removing content, reminders SHOULD refer to file name(s) rather than verbatim content; otherwise, reminders MAY include reference to or minimal description of that content so that restrictions are clearly defined. These reminder requirements apply to agents that are required to ignore the directory; they do not apply to an explicitly designated Critique Agent operating within its repository-wide review scope.
