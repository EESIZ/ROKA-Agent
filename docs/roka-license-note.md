# ROKA License Note

ROKA-Agent is a fork of Hermes Agent. The inherited Hermes Agent source code is
licensed under the upstream MIT license and keeps that license unless a file
explicitly says otherwise.

ROKA-specific project materials should be treated separately from the inherited
codebase:

- ROKA methodology documents, diagrams, names, and project-specific control
  language are intended to be shared for personal, research, and internal use.
- Commercial redistribution of ROKA-specific methodology materials should
  require permission from the ROKA project owner.
- Code that modifies or extends Hermes should stay compatible with the upstream
  MIT license unless it is isolated into a clearly separate module with its own
  license notice.

Recommended practical setup:

1. Keep the repository `LICENSE` file as MIT for upstream-compatible code.
2. Add a separate `docs/ROKA-CONTENT-LICENSE.md` later for ROKA methodology
   content, using a license such as CC BY-NC-SA 4.0 if the project owner wants
   broad non-commercial reuse but does not want commercial extraction.
3. Use `ROKA` as a project name and brand marker for the fork's specific design
   direction, not as a restriction on inherited Hermes code.

This note is not legal advice. It is the working project policy until the owner
chooses a formal license for ROKA-specific non-code materials.
