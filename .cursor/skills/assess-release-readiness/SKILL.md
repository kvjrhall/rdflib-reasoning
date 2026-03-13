# Assess Release Readiness

This skill defines release-readiness quality gates for packages and metapackages in this
repository.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be
interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

## How to use this skill

When asked to assess whether a release is ready:

1. Identify the intended release target and which packages are in scope.
2. Evaluate each gate below against the current repository state, CI configuration,
   documentation, and packaging metadata.
3. Report findings grouped as:
   - `Release blockers`: failed MUST gates.
   - `Follow-up recommended`: failed SHOULD gates.
   - `Evidence checked`: commands, files, workflows, or artifacts reviewed.
4. If the assessment reveals a missing workflow, missing documentation, or missing packaging
   metadata, recommend the smallest coherent fix that would satisfy the gate.

## Release Blockers

The following gates MUST pass before a package or metapackage is considered ready to release.

### Packaging and Distribution

- [ ] Does every in-scope package build successfully as both an `sdist` and a wheel from a
      clean checkout?
- [ ] Do built artifacts pass `twine check`?
- [ ] Does the version reported by packaging metadata resolve correctly from the intended git
      tag or release version source?
- [ ] Do package metadata fields include the minimum expected modern packaging information?
  - [ ] Name
  - [ ] Version source
  - [ ] Description
  - [ ] `readme`
  - [ ] `requires-python`
  - [ ] License metadata
  - [ ] Dependencies
  - [ ] Useful project URLs where applicable
- [ ] Can each published artifact be installed into a clean environment from the built
      distribution, not only from an editable workspace checkout?
- [ ] After installation, do the documented top-level imports and at least one quick-start path
      execute successfully?

### CI and Verification

- [ ] Does the primary CI pipeline execute linting, tests, and artifact builds for the in-scope
      packages?
- [ ] Is code coverage produced and surfaced in CI for feature branches and the default branch?
- [ ] Are release workflows configured to build the same artifacts that will be published?
- [ ] Has the release path been exercised against TestPyPI or an equivalent non-production
      target?
- [ ] Are required repository secrets, environments, and permissions configured for publishing?

### Versioning and Release Management

- [ ] Is there a clear release note or changelog entry describing the user-visible contents of
      the release?
- [ ] Are breaking changes, deprecations, or migration steps called out explicitly when they
      exist?
- [ ] Does the release process avoid ambiguous version states such as mismatched tags and
      package metadata?
- [ ] If this repository publishes multiple related packages, is the intended versioning policy
      across those packages documented and followed?

### Security and Supply Chain

- [ ] Are GitHub Actions and other release-critical automation dependencies maintained through a
      documented update path such as Dependabot?
- [ ] Are there any unresolved critical or high-severity security issues in release-critical
      dependencies?
- [ ] Are release-time dependencies and workflows pinned or constrained appropriately to reduce
      accidental drift?

## Recommended Gates

The following gates SHOULD pass before release unless there is an explicit reason to defer them.

### User Experience

- [ ] Does the root `README.md` provide quick-start tutorials for the most important system use
      cases?
- [ ] Do `rdflib-reasoning*/README.md` files provide quick-start tutorials for their subsystem
      use cases?
- [ ] Do all READMEs reflect the current released API rather than only the current development
      branch?
- [ ] Is python documentation generated and published as part of deployment?
- [ ] Are best practices for modern technical documentation being adhered to in all
      human-facing Markdown files?
- [ ] Does the root `README.md` show release-relevant status indicators such as supported Python
      versions, package version, and coverage where appropriate?

### Developer Experience

- [ ] Does `.github/CONTRIBUTING.md` cover everything needed for someone to onboard to
      developing with the system?
  - [ ] `.github/CONTRIBUTING.md` MUST explain how agents are used in the development process
        and what content is aimed at them.
  - [ ] `.github/CONTRIBUTING.md` MUST explain what `.cursor/skills/` exist and when to invoke
        them.
  - [ ] `.github/CONTRIBUTING.md` MUST link to `docs/example-chats/README.md` so that
        contributors can see examples of working with an agent.
- [ ] Are local development, validation, and release rehearsal commands documented and current?
- [ ] Can a new contributor determine how to cut a release without reverse-engineering CI
      workflows?

### Compatibility and Maintenance

- [ ] Does CI exercise the supported Python version matrix and any important operating-system
      combinations?
- [ ] Are dependency ranges compatible with the intended support policy rather than relying on
      unbounded optimism?
- [ ] Are public API stability expectations documented for consumers of the packages?
- [ ] Is there a documented policy for deprecations and removals if the project expects external
      users?

## Evidence Sources

When assessing release readiness, Development Agents SHOULD inspect the following when relevant:

- Root `README.md`
- `rdflib-reasoning*/README.md`
- Root and subproject `pyproject.toml` files
- `Makefile`
- `.github/workflows/*.yml`
- `.github/release-drafter.yml`
- `.github/dependabot.yml`
- `.github/CONTRIBUTING.md`
- Published-package documentation configuration, if any
- Build artifacts produced locally or in CI

## Assessment Output Template

The final assessment SHOULD be structured like this:

### Release blockers

- List every failed MUST gate with a short explanation and evidence.

### Follow-up recommended

- List every failed SHOULD gate with a short explanation and evidence.

### Evidence checked

- List commands run, files inspected, workflows reviewed, and artifacts validated.

### Conclusion

- State whether the release is ready now, ready with caveats, or not ready.
