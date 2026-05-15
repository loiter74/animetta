## ADDED Requirements

### Requirement: Frontend testing framework installed
The system SHALL install vitest, @vue/test-utils, happy-dom, and @testing-library/vue as dev dependencies.

#### Scenario: vitest configuration exists
- **WHEN** developer runs `npx vitest --version`
- **THEN** it SHALL print a valid version number

#### Scenario: Test script is available
- **WHEN** developer runs `pnpm test`
- **THEN** vitest SHALL execute and report results

### Requirement: Vitest config shares Vite config
The vitest.config.ts SHALL extend the existing vite.config.ts to reuse resolve aliases and plugins.

#### Scenario: Vitest resolves @ alias
- **WHEN** a test imports from `@/components/...`
- **THEN** vitest SHALL resolve to `frontend/src/components/...`

### Requirement: happy-dom provides browser API mocks
The test environment SHALL use happy-dom to provide DOM APIs (document, window, HTMLElement) without a real browser.

#### Scenario: DOM API available in tests
- **WHEN** a test runs `document.createElement('div')`
- **THEN** it SHALL return a valid HTMLElement

### Requirement: Playwright is installed for E2E
The system SHALL install playwright as a dev dependency.

#### Scenario: Playwright binary available
- **WHEN** developer runs `npx playwright --version`
- **THEN** it SHALL print a valid version number

### Requirement: Test files follow naming convention
All test files SHALL be named `*.test.ts` and located co-located with the source or in `__tests__/` directories.

#### Scenario: Test discovery works
- **WHEN** vitest discovers tests recursively from frontend/src/
- **THEN** it SHALL find all `*.test.ts` files
