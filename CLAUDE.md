# Project-Specific CLAUDE Documentation

## Overview
This file contains notes and instructions specific to the Arabella project.

## Documentation
- For each functional change in the project the README.md file must be reviewed and updated if necesary
- For each update to the test cases the file /docs/TEST_CASES.md must be updated accordingly

## Coding style
**Clean Code (Robert C. Martin)**
- all new code shall be according to Unckle Bob's Clean Code and Clean Architecture principels 
- Meaningful Names: names must reveal intent; no cryptic abbreviations
- Small functions: one responsibility, one level of abstraction
- DRY: eliminate duplication ruthlessly
- Error handling: exceptions over error codes; never swallow silently
- Comments: explain WHY, not WHAT; prefer self-documenting code

**Clean Architecture**
- Dependency Rule: source code dependencies point inward only
- Entities → Use Cases → Interface Adapters → Frameworks (never reversed)
- Business logic must not depend on UI, database, or framework

## Testing
- All code shall haveunit tests covering the functionality
- The project shal have functional test for the functionality
- WEB interfaces are to be tested via Playwright
