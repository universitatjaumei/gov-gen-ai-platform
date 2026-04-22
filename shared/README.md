# automatia-shared

Shared DTOs, enums, validators and pure utilities for AutomatIA platform.

## Contents

- **dtos/**: Pydantic models for data transfer between server and client
- **enums/**: Canonical enums used across the platform
- **validators/**: Pure validation functions
- **utils/**: Pure utility functions (no I/O)

## Installation

```bash
uv add automatia-shared
```

## Usage

```python
from automatia_shared.enums import TaskStatus, LicenseStatus
from automatia_shared.dtos import FlowSpec, TaskSpec
from automatia_shared.validators import validate_license_key
```

## Important

This package should NEVER contain:
- Database access code
- Network/HTTP calls
- File system operations
- Secrets or credentials
- Playwright/browser automation
- Any volatile code that changes frequently on one side only
