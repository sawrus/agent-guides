# AGENTS

## Dynamic loading of guidance

The set of loaded guidance is configurable by the user and may change per project.
Do not assume only statically listed files are available.

In addition to built-in guidance, discover and load custom files from the target project directory when present.

## Expected project tree

```text
project_dir/
└── .agent/
    ├── rules/
    ├── skills/
    ├── workflows/
    └── prompts/
```

## Discovery patterns

- `project_dir/.agent/rules/*`
- `project_dir/.agent/skills/*`
- `project_dir/.agent/workflows/*`
- `project_dir/.agent/prompts/*`

Prefer relative paths in references inside markdown files.

## General Development Practices

This section covers foundational software development practices applicable to any project.

### Git Workflow

- Use feature branches with task IDs in branch names
- Commit with descriptive messages including context
- Require code review before merging to main

### Makefile Conventions

- Use Makefile for common development tasks
- Include help target describing available commands
- Standard targets: install, dev, test, lint, fmt, clean

### Docker Compose Basics

- Use docker-compose for local multi-service development
- Configure health checks for dependent services
- Use environment variables for configuration

### Linting and Formatting

- Configure language-appropriate linters
- Use pre-commit hooks to enforce standards
- Run consistent formatting across all files

### SDLC Methodology

- Follow standard phases: Requirements → Design → Implementation → Testing → Deployment → Maintenance
- Document requirements before implementation
- Conduct design reviews for significant features

### Code Style Guidelines

- Write self-documenting code with meaningful names
- Apply DRY principles - avoid duplication
- Keep functions focused on single responsibility

### Repository Exploration

Before executing the workflow, spawn a subagent to explore the repository.

#### Role resolution

- Use the role defined in `execution.initiator` of the current workflow
- If `execution.initiator` is not defined, use the role assigned to the first workflow step
- Resolve roles only from the current workflow (`roles` section)
- Do not invent or substitute roles

#### Purpose

- Understand current architecture
- Identify key modules and entrypoints
- Detect configuration (env, Docker, Makefile, etc.)
- Identify impacted components
- Validate feasibility of the feature

#### Responsibilities

The subagent must:

- analyze repository structure and dependencies
- locate relevant services, modules, and data flows
- identify constraints, risks, and integration points
- prepare context for the next workflow step

#### Output

- High-level system overview
- List of affected modules and files
- Detected risks and constraints

#### Constraint

This step is mandatory and must be completed before starting "Solution Design & Risk Plan"
