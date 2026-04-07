# Project-Specific CLAUDE Documentation

## Overview
This file contains notes and instructions specific to the Arabella project.

## Documentation
- For each functional change in the project the README.md file must be reviewed and updated if necesary
- For each update to the test cases the file /docs/TEST_CASES.md must be updated accordingly

## Coding style
**Clean Code (Robert C. Martin)**
- all code shall be according to Unckle Bob's Clean Code and Clean Architecture principels 
- Meaningful Names: names must reveal intent; no cryptic abbreviations
- Small functions: one responsibility, one level of abstraction
- DRY: eliminate duplication ruthlessly
- Error handling: exceptions over error codes; never swallow silently
- Comments: explain WHY, not WHAT; prefer self-documenting code

**Clean Architecture**
- Dependency Rule: source code dependencies point inward only
- Entities → Use Cases → Interface Adapters → Frameworks (never reversed)
- Business logic must not depend on UI, database, or framework

## Code quality
- all data/parameters that is input to the application or the API shall have input validation
- client side validation is good. Server side validation is necesary

## Code execution
- Require python 3.11 or later for the project
- Use python3 as base for executing commands on Mac.
- Use latest available pyton as base for executing commandfs on Linux and Windows

## Testing
- All code shall have unit tests covering the functionality
- The project shall have functional tests for the functionality
- WEB interfaces are to be tested via Playwright

**When to run tests**
- Before every commit — ensure nothing is broken before checking in
- After pulling remote changes — verify incoming code does not break existing functionality
- After merging or rebasing — confirm the merge did not introduce regressions
