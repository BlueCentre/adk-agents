# Contributing to the DevOps Agent

We welcome contributions to the DevOps Agent! To ensure a smooth and collaborative process, please follow these guidelines.

## Code of Conduct

This project and everyone participating in it is governed by the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Development Process

1.  **Fork the repository** and create your branch from `main`.
2.  **Install dependencies** using the instructions in the main `README.md`.
3.  **Make your changes** and ensure that all tests pass.
4.  **Update the documentation** as described in the policy below.
5.  **Submit a pull request** with a clear description of your changes.

## Documentation Policy

To ensure our documentation remains accurate, up-to-date, and valuable to the community, we have adopted the following policy:

**All pull requests that introduce, modify, or remove user-facing features or configuration variables MUST include corresponding updates to the documentation in the `/docs` directory.**

### What This Means

-   **New Feature?** Add a section to `docs/features.md` and, if necessary, a detailed guide in `docs/usage/`.
-   **Changing a Configuration Variable?** Update the table in `docs/configuration.md`.
-   **Changing an Existing Feature?** Update the relevant sections in `docs/features.md` and any related usage guides.
-   **Fixing a Bug?** If the bug fix changes user-facing behavior, the documentation should be updated to reflect the correct behavior.

By including documentation updates in the same pull request as the code changes, we ensure that our documentation is never out of sync with the codebase. This is a critical part of the definition of "done" for any change.
