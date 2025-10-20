# Kartograph Specifications

This directory contains feature specifications following the [spec-kit](https://github.com/github/spec-kit) methodology for intent-driven development.

## Directory Structure

```
.specify/
├── memory/          # Project documentation and foundational guidelines
│   └── constitution.md    # Project governance and coding standards (future)
├── specs/           # Feature specifications
│   ├── 001-operational-changelog/
│   │   └── spec.md
│   └── ...
└── README.md        # This file
```

## Spec-Kit Workflow

When implementing new features, follow this process:

1. **Specify** - Define requirements and user stories in a spec file
2. **Plan** - Develop technical implementation strategy
3. **Tasks** - Generate actionable task lists
4. **Implement** - Execute tasks to build the feature

## Creating a New Specification

```bash
# Create a new spec directory with incrementing number
mkdir -p app/.specify/specs/00X-feature-name

# Create the spec file
touch app/.specify/specs/00X-feature-name/spec.md
```

## Spec Template

A good specification includes:

### 1. Problem Statement

What problem does this solve? Why is it needed?

### 2. User Stories

Who benefits and how? Written as "As a [role], I want [goal] so that [benefit]"

### 3. Requirements

- Functional requirements (what the feature must do)
- Non-functional requirements (performance, security, UX)

### 4. Technical Approach

- High-level architecture
- Database schema
- API design
- UI components
- Integration points

### 5. Success Criteria

Measurable criteria to determine if the feature is complete and successful

## Specification Principles

- **Intent over implementation**: Focus on "what" before "how"
- **Living documents**: Update specs as requirements change or insights emerge
- **Single source of truth**: Keep specs in sync with implementation
- **Comprehensive but concise**: Include necessary detail without overwhelming
- **User-focused**: Start with user needs, not technical solutions

## Current Specifications

- [001-operational-changelog](./specs/001-operational-changelog/spec.md) - Unified changelog system for code and operational updates

## References

- [Spec-Kit GitHub Repository](https://github.com/github/spec-kit)
- [Project AGENTS.md](../../AGENTS.md) - Full development guidelines
