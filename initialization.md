# Project Initialization Instructions

## Purpose

Initialize a new software project with a clean, maintainable, and AI-friendly structure.

The goal is to establish the project's foundations before implementing application features.

Do not write application code until the initial structure and development approach have been reviewed and approved by the human.

---

## 1. Inspect Before Creating

Before creating or modifying files:

1. Inspect the current repository.
2. Determine whether the repository is empty, partially initialized, or already contains a project.
3. Identify the language, framework, package manager, build system, and existing tooling when applicable.
4. Identify existing configuration files.
5. Check whether Git is already initialized.
6. Check whether a `.gitignore` already exists.
7. Do not overwrite existing project configuration without understanding it.

If important information is missing, state the uncertainty rather than making assumptions.

---

## 2. Determine the Technology Stack

Before establishing the project structure, identify the technologies that will be used by the project.

The technology stack should be documented in:

`docs/ARCHITECTURE.md`

The stack may include:

* programming languages
* frameworks
* major libraries
* databases
* infrastructure technologies
* build systems
* package managers
* other technologies that materially affect development

Distinguish between:

* technologies that are confirmed by the human;
* technologies inferred from an existing repository;
* technologies proposed by the AI.

Do not silently choose significant technologies when multiple reasonable alternatives exist.

Technology choices that materially affect the architecture or long-term design require human approval.

---

## 3. Technology Guidelines

The AI may have access to a separate, reusable technology knowledge base containing guidelines for languages and frameworks.

These guidelines are organized under:

```text
ai/
├── languages/
└── frameworks/
```

The `ai/` knowledge base is maintained by the human and is not part of the project's repository structure unless explicitly included by the human.

When initializing or working on a project:

1. Identify the languages used by the project.
2. Identify the frameworks used by the project.
3. Identify other technologies that have relevant guidelines when applicable.
4. Use the corresponding guidelines from the `ai/` knowledge base when they are available.
5. Do not create, modify, or extend files under `ai/` during project initialization unless explicitly instructed by the human.
6. If a relevant guideline is not available, state that clearly rather than inventing or silently creating one.

Technology guidelines provide language- and framework-specific engineering practices, idioms, patterns, and relevant technical considerations.

Project-specific requirements and architectural decisions take precedence over generic technology guidelines.

The relevant technology guidelines should be treated as part of the technical context used by the AI during implementation.

---

## 4. Propose the Initial Structure

For a new project, propose an appropriate repository structure.

A typical structure may be:

```text
project/
├── AGENTS.md
├── README.md
├── .gitignore
│
├── docs/
│   ├── ARCHITECTURE.md
│
│
├── src/
├── tests/
│
└── .github/
    └── workflows/
```

Adapt the structure to the language, framework, project size, and actual requirements.

Do not create directories merely because they appear in the example above.

---

## 5. Repository Documentation

Create only documentation that has a clear purpose.

### README.md

Should contain:

* project name
* concise project description
* goals
* current status
* basic setup instructions
* basic usage
* testing instructions when available

Do not turn the README into a complete technical manual.

### docs/ARCHITECTURE.md

Should describe:

* technology stack
* major components
* responsibilities
* boundaries
* important dependencies
* major data/control flows
* architectural constraints

The Technology Stack section should identify the technologies actually used by the project.

For example:

```markdown
## Technology Stack

### Languages
- Python 3.13

### Frameworks
- FastAPI
- SQLAlchemy

### Database
- PostgreSQL
```

Keep the architecture focused on the current system.

Do not duplicate detailed language or framework guidelines here.

### docs/DEVELOPMENT.md

Should describe:

* required tools
* environment setup
* dependency installation
* running the project
* running tests
* linting
* type checking
* building
* other important development commands

Only document commands that actually exist.

### docs/DECISIONS.md

Record important architectural decisions and their rationale.

Do not create decision records for trivial implementation choices.

### plans/

Use this directory for non-trivial work that is planned or currently being implemented.

Do not create placeholder plans merely to populate the directory.

---

## 6. AGENTS.md

`AGENTS.md` defines the permanent collaboration rules for AI agents working in the repository.

It should describe:

* human ownership and approval
* how the AI should analyze tasks
* when plans are required
* implementation rules
* testing and verification
* code review expectations
* engineering and performance principles
* how relevant language and framework guidelines are selected and used

Do not duplicate project architecture, technology-specific guidelines, or development documentation inside `AGENTS.md`.

---

## 7. .gitignore

Create a `.gitignore` appropriate for the actual technology stack.

Before creating it:

1. Identify the language.
2. Identify the framework.
3. Identify the package manager.
4. Identify the build system.
5. Identify the development tools.
6. Identify common generated files and caches.
7. Identify local environment files and secrets.

The `.gitignore` should normally account for:

* operating-system files
* editor-specific files when appropriate
* dependency directories
* build artifacts
* caches
* test artifacts
* local environment files
* temporary files
* generated files that should not be versioned

### Official Template

When an official GitHub gitignore template exists for the detected language, framework, or tooling, use it as the starting point.

Prefer retrieving the template with GitHub CLI:

```bash
gh repo gitignore view <TEMPLATE>
```

For example:

```bash
gh repo gitignore view Python
```

The command is used to inspect the official template. Review the template before using it as the project's `.gitignore`.

If GitHub CLI is available, prefer it over manually copying a template from an arbitrary source.

If GitHub CLI is unavailable, use the official GitHub `gitignore` repository or another appropriate official source.

### Template Adaptation

Never blindly copy a generic `.gitignore` template.

After retrieving the template:

1. Review every relevant rule.
2. Remove rules that do not apply to the project.
3. Add rules required by the project's actual tooling.
4. Add project-specific generated files or directories when necessary.
5. Check that important source files are not accidentally ignored.
6. Check that required configuration files remain versioned.

The final `.gitignore` must reflect the actual project rather than being a generic language template.

Start with universal rules only when the technology stack is not yet known. Finalize the `.gitignore` after the project's language, framework, package manager, and development tooling have been identified.

---

## 8. Secrets and Environment Variables

Never commit:

* API keys
* passwords
* tokens
* private certificates
* credentials
* production secrets
* local `.env` files containing secrets

When environment variables are required, prefer:

```text
.env.example
```

containing variable names but no real secret values.

For example:

```text
DATABASE_URL=

API_KEY=

SECRET_KEY=
```

The actual `.env` file should normally be ignored by Git.

Do not add sensitive file patterns to the global Git ignore configuration unless they are genuinely machine-wide files that should never be versioned in any repository.

---

## 9. Git Initialization

If Git is not already initialized:

```bash
git init
```

Before the first commit, inspect the repository status and verify that no secrets or unwanted generated files are included.

The initial commit should contain the project foundation, not unfinished application functionality.

A suitable initial commit message may be:

```text
chore: initialize project structure
```

Adapt the commit message to the project's conventions.

---

## 10. GitHub Configuration

Do not create GitHub Actions workflows unless they provide immediate value.

When automated verification becomes useful, add:

```text
.github/
└── workflows/
    └── ci.yml
```

The CI workflow should run the project's relevant automated checks, such as:

* tests
* linting
* type checking
* build
* other required validation

Do not add CI steps that are not actually supported by the project.

---

## 11. Initial Verification

Before considering initialization complete, verify:

* the repository structure is coherent
* Git is configured correctly
* `.gitignore` works as intended
* no secrets are tracked
* documentation reflects reality
* the technology stack is correctly documented
* relevant technology guidelines were identified
* development commands actually work when applicable
* the project can be opened and understood by another developer

For `.gitignore`, when useful, verify individual rules with:

```bash
git check-ignore -v <path>
```

Do not claim that a command works unless it has actually been tested.

---

## 12. Human Approval

Before implementing application functionality:

1. Present the proposed project structure.
2. Explain important technology choices.
3. Explain the relevant technology guidelines that will be used.
4. Explain relevant tooling.
5. Explain the `.gitignore` strategy.
6. Identify important assumptions.
7. Identify open questions.
8. Wait for human approval.

Only after approval should the initial project structure be created or modified.

---

## Initialization Output

When asked to initialize a project, first provide:

### Understanding

What was found in the repository.

### Proposed Structure

The proposed directory and file structure.

### Technology

The detected or proposed language, framework, package manager, and tooling.

### Technology Guidelines

The languages and frameworks used by the project and the corresponding guidelines available in the `ai/` knowledge base.

Clearly identify any relevant guideline that is unavailable.

Do not modify the `ai/` knowledge base unless explicitly instructed by the human.

### Documentation

Which documentation files should exist and why.

### Git Strategy

Git initialization and initial commit strategy.

### .gitignore

The proposed ignore rules, the official template used as a starting point when applicable, and the rationale for any project-specific modifications.

### Verification

How the initialized project will be validated.

Do not implement application functionality during initialization unless explicitly requested.
