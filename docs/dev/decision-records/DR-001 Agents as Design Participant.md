# Agents as Design Participant

## Status

Accepted

## Context

docs/dev holds design, architecture, and decisions; all content there is optimized for Development Agent consumption and will change as the system's design emerges. We need a clear role for the Development Agent so it uses and maintains that content correctly.

## Decision

The Development Agent's role with docs/dev is that of a **design participant**: it treats docs/dev as the live design specification, updates it when decisions are made or the design evolves (e.g. new DRs, INDEX, supersedes), and keeps it structured and consistent for future Development Agent and human use. It reads AGENTS.md and decision-records rules as binding; it does not only answer from docs but maintains and extends them.

## Consequences

Development Agents will create/update DRs, keep INDEX and supersedes correct, and preserve machine-parseable structure.
