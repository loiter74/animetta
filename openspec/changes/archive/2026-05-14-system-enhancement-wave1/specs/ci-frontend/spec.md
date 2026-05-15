## ADDED Requirements

### Requirement: Frontend type check runs in CI
The CI pipeline SHALL run `vue-tsc --noEmit` on the frontend codebase on every push and pull request.

#### Scenario: Type check passes
- **WHEN** GitHub Actions workflow triggers on push
- **THEN** vue-tsc SHALL run on frontend/src/
- **THEN** exit code 0 indicates no type errors

### Requirement: Frontend lint runs in CI
The CI pipeline SHALL run ESLint on the frontend codebase.

#### Scenario: Lint passes
- **WHEN** GitHub Actions workflow triggers
- **THEN** ESLint SHALL run on frontend/src/
- **THEN** exit code 0 indicates no lint errors

### Requirement: Frontend tests run in CI
The CI pipeline SHALL run vitest on the frontend test suite.

#### Scenario: Tests pass
- **WHEN** GitHub Actions workflow triggers
- **THEN** vitest SHALL execute all frontend tests
- **THEN** all tests SHALL pass

### Requirement: Frontend CI workflow is independent
The frontend CI SHALL be a separate GitHub Actions workflow file (frontend.yml) from the backend test workflow.

#### Scenario: Workflow exists
- **WHEN** .github/workflows/frontend.yml is checked
- **THEN** it SHALL exist and contain steps for type check, lint, and test
