# Python Coding Guide

## Purpose

This guide defines how Python code should be written in this project.

It is intended for AI coding agents and human developers.

The goal is to produce Python code that is:

* readable;
* unsurprising;
* maintainable;
* explicit about important behavior;
* consistent with modern Python;
* easy to test;
* efficient where efficiency matters;
* proportionate to the problem being solved.

This guide complements, rather than replaces, established Python conventions such as PEP 8 and PEP 257.

Project-specific conventions take precedence when explicitly defined elsewhere.

---

# 1. General Principles

## 1.1 Prefer readability

Write code for the person who will read and maintain it later.

Prefer:

```python
active_users = [user for user in users if user.is_active]
```

over code that is shorter but harder to understand.

Do not optimize for minimum line count.

## 1.2 Prefer explicit intent

Code should make important decisions visible.

Prefer:

```python
if user is None:
    return None
```

over relying on truthiness when `None` has a specific semantic meaning.

## 1.3 Prefer simple solutions

Use the simplest design that correctly solves the problem.

Do not introduce:

* unnecessary abstractions;
* unnecessary classes;
* unnecessary design patterns;
* speculative extension points;
* frameworks or dependencies without a clear benefit.

Complexity should be justified by a real requirement.

## 1.4 Consistency matters

Follow existing project conventions when they are clear and reasonable.

When modifying existing code, preserve local conventions unless there is a good reason to change them.

Do not perform unrelated style rewrites while implementing a feature.

---

# 2. Formatting

Use standard Python formatting conventions.

Use:

* 4 spaces for indentation;
* spaces around operators;
* one statement per line;
* blank lines to separate logical sections;
* parentheses for multiline expressions rather than backslashes.

Prefer:

```python
result = (
    first_value
    + second_value
    + third_value
)
```

Avoid:

```python
result = first_value + \
    second_value + \
    third_value
```

Use an automatic formatter when the project provides one.

Formatting should normally be delegated to tooling rather than manually enforced by the AI.

---

# 3. Naming

Names should communicate meaning, not implementation details.

## 3.1 Variables

Use `snake_case`.

Prefer:

```python
user_count = 10
active_users = []
earliest_timestamp = None
```

Avoid:

```python
userCount = 10
au = []
ts = None
```

Use abbreviations only when they are well established and unambiguous in the context.

## 3.2 Functions and methods

Use `snake_case`.

Function names should normally describe an action.

Prefer:

```python
load_metadata()
parse_record()
find_oldest_record()
validate_config()
calculate_total()
```

Avoid vague names such as:

```python
process()
handle()
manage()
do_stuff()
```

unless the surrounding abstraction gives the name a precise meaning.

## 3.3 Classes

Use `PascalCase`.

Prefer:

```python
MetadataParser
UserRepository
ConfigurationError
```

## 3.4 Constants

Use `UPPER_SNAKE_CASE`.

Prefer:

```python
MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 30
MAX_BATCH_SIZE = 1000
```

Do not create constants for every literal.

Introduce a named constant when a value:

* has semantic meaning;
* is reused;
* represents configuration;
* is likely to change;
* would otherwise obscure the intent of the code.

## 3.5 Boolean names

Boolean names should communicate state or capability.

Prefer:

```python
is_active
is_valid
has_permission
has_items
can_retry
should_retry
```

Avoid:

```python
active_flag
valid_bool
permission
```

## 3.6 Names should describe semantics

Do not encode the implementation type into a name when the semantic meaning is more useful.

Prefer:

```python
users: list[User]
metadata: dict[str, Any]
```

over:

```python
user_list: list[User]
metadata_dict: dict[str, Any]
```

The type annotation already communicates the implementation type.

---

# 4. Modules and Packages

Module names should be short, descriptive, lowercase, and use underscores when necessary.

Prefer:

```text
metadata.py
user_repository.py
configuration.py
```

Avoid:

```text
MetadataParser.py
userRepository.py
misc.py
stuff.py
```

Avoid generic module names unless the module genuinely represents a generic concept.

Prefer several focused modules over one large `utils.py` when the functions have different responsibilities.

---

# 5. Imports

Organize imports into logical groups:

1. standard library;
2. third-party dependencies;
3. local project imports.

Example:

```python
import json
from pathlib import Path

import httpx

from project.metadata import records
from project.models import User
```

Do not use wildcard imports:

```python
from module import *
```

Prefer explicit imports.

Avoid imports that exist only to shorten names unless they materially improve readability.

---

# 6. Module Structure

A typical module should have a predictable structure:

```python
"""Module description."""

from __future__ import annotations

import ...

CONSTANT = ...

class SomeClass:
    ...


def some_function() -> ...:
    ...


def main() -> None:
    ...


if __name__ == "__main__":
    main()
```

Do not force every module to follow this structure mechanically.

Use the structure appropriate to the module's purpose.

---

# 7. Comments and Docstrings

Comments should explain information that is not obvious from the code.

Good comments explain:

* why something is done;
* an important constraint;
* a non-obvious assumption;
* compatibility requirements;
* a subtle algorithmic decision;
* a known limitation.

Avoid comments that simply restate the code.

Bad:

```python
# Increment counter
counter += 1
```

Good:

```python
# The archive may contain duplicate records, so count physical records
# rather than unique subreddit IDs.
records_scanned += 1
```

Keep comments synchronized with the implementation.

Outdated comments are worse than no comments.

## 7.1 Docstrings

Use docstrings for public modules, classes, functions, and methods where documentation provides useful information.

Follow PEP 257 conventions.

Prefer:

```python
def find_oldest_record(records: Iterable[Record]) -> Record | None:
    """Return the record with the earliest known activity."""
```

For non-obvious behavior, document:

* important arguments;
* return semantics;
* side effects;
* raised exceptions;
* important restrictions;
* assumptions.

Do not write docstrings that merely repeat an obvious function name or type signature.

---

# 8. Functions

Functions should have a clear responsibility.

Prefer:

```python
def parse_timestamp(value: object) -> float | None:
    ...
```

over a function that parses timestamps, writes files, logs errors, and updates global state.

However, do not split code into tiny functions mechanically.

This:

```python
def get_user_name(user):
    return user.name
```

does not become better merely because it is a function.

Extract a function when it provides meaningful:

* abstraction;
* reuse;
* testability;
* readability;
* separation of responsibility.

---

# 9. Function Arguments

Prefer clear function interfaces.

When a function has several optional or configuration-like arguments, consider keyword-only arguments.

Prefer:

```python
def load_records(
    path: Path,
    *,
    strict: bool = False,
    limit: int | None = None,
) -> list[Record]:
    ...
```

over:

```python
def load_records(path, strict=False, limit=None):
    ...
```

when positional use would make calls ambiguous.

Avoid functions with excessive numbers of parameters.

When several parameters form a coherent concept, consider a dedicated data structure such as a dataclass.

---

# 10. Return Values

Return values should have clear and consistent semantics.

Use `None` when absence is a valid and meaningful result.

Use exceptions when an operation cannot fulfill its contract.

Do not use a mixture of:

```python
None
False
[]
```

to represent the same conceptual failure or absence.

For example, prefer:

```python
user = find_user(user_id)

if user is None:
    ...
```

when "user does not exist" is a valid result.

Use an exception when failure indicates that the operation could not perform its intended job:

```python
config = load_config(path)
```

If the file is required but cannot be read, raising an appropriate exception is generally clearer than returning `None`.

---

# 11. Control Flow

Prefer straightforward control flow.

Use guard clauses when they make the main path easier to read.

Prefer:

```python
if record is None:
    return None

if not record.is_valid:
    return None

return process(record)
```

over deeply nested conditionals.

Avoid clever boolean expressions when they obscure intent.

Prefer explicit conditions when `None`, empty values, and false values have different meanings.

---

# 12. Collections and Data Structures

Choose data structures based on how the data is used.

Consider:

* lookup complexity;
* insertion/removal complexity;
* ordering requirements;
* uniqueness requirements;
* memory usage;
* mutability;
* serialization requirements.

Use:

* `list` for ordered sequences;
* `set` for uniqueness and membership;
* `dict` for key/value lookup;
* `tuple` for fixed immutable sequences;
* specialized structures when their semantics provide a real benefit.

Do not use a list when the dominant operation is repeated membership testing.

Prefer:

```python
known_ids = set(ids)

if user_id in known_ids:
    ...
```

over repeatedly searching a list when membership performance matters.

---

# 13. Comprehensions

Use comprehensions for simple transformations and filtering.

Prefer:

```python
active_users = [user for user in users if user.is_active]
```

Avoid comprehensions containing complicated business logic.

If a comprehension requires nested conditions, side effects, multiple statements, or difficult reasoning, use a normal loop.

Readability takes precedence over compactness.

---

# 14. Iteration and Generators

Prefer direct iteration.

Prefer:

```python
for user in users:
    process(user)
```

over indexing:

```python
for index in range(len(users)):
    process(users[index])
```

Use `enumerate()` when the index is required:

```python
for index, user in enumerate(users):
    ...
```

Use `zip()` when iterating over related sequences:

```python
for user, score in zip(users, scores):
    ...
```

Use generators when data can be processed incrementally.

Prefer streaming when the complete dataset does not need to exist in memory simultaneously.

---

# 15. Algorithms and Complexity

Choose algorithms based on the actual access pattern and expected data size.

Do not automatically choose the most sophisticated algorithm.

Prefer a simple `O(n)` single-pass solution when it solves the problem:

```python
oldest = None

for record in records:
    if oldest is None or record.timestamp < oldest.timestamp:
        oldest = record
```

Avoid sorting merely to find a minimum:

```python
oldest = sorted(records, key=lambda record: record.timestamp)[0]
```

when only the minimum is required.

Understand the complexity of important operations.

When implementing non-trivial algorithms, consider:

* time complexity;
* space complexity;
* input size;
* worst-case behavior;
* streaming possibilities;
* batching;
* caching;
* I/O cost.

Do not optimize without a reason.

---

# 16. Type Hints

Use type hints for public APIs and wherever they materially improve clarity.

Prefer modern Python syntax when supported by the project's Python version:

```python
def parse_timestamp(value: object) -> float | None:
    ...
```

over older forms when the project targets a modern Python version.

Use types to communicate contracts, not to decorate code mechanically.

Avoid overly complex type expressions when a simpler design is clearer.

If the type system becomes difficult to understand, reconsider the API design.

---

# 17. Data Modeling

Choose the data representation according to the role of the data.

Use a plain `dict` for genuinely dynamic or loosely structured data.

Use `TypedDict` when a dictionary has a known structure but dictionary semantics are desirable.

Use `dataclass` for structured application data with explicit fields.

Use a regular class when behavior, invariants, lifecycle, or encapsulation justify it.

Do not introduce a class merely because several values exist together.

Prefer:

```python
@dataclass
class User:
    id: str
    name: str
    active: bool
```

when the application has a meaningful `User` concept.

Avoid wrapping simple data in unnecessary abstractions.

---

# 18. Mutability

Avoid unnecessary mutation.

Do not mutate arguments unless mutation is explicitly part of the function's contract.

Prefer returning a new value when that makes ownership and side effects clearer.

Avoid mutable global state.

Be particularly careful with mutable default arguments.

Never write:

```python
def add_item(item, items=[]):
    ...
```

Prefer:

```python
def add_item(item, items=None):
    if items is None:
        items = []
    ...
```

or use a more appropriate design.

---

# 19. Exceptions

Handle specific exceptions.

Avoid:

```python
try:
    ...
except Exception:
    ...
```

unless there is a deliberate reason to catch all exceptions at that boundary.

Avoid bare:

```python
except:
    ...
```

Prefer:

```python
try:
    data = json.loads(text)
except json.JSONDecodeError as exc:
    raise InvalidMetadata("Invalid metadata JSON") from exc
```

Catch exceptions at the level where they can be handled meaningfully.

Do not catch an exception merely to log it and immediately re-raise it without adding useful information.

Do not use exceptions for ordinary control flow when a normal return value is clearer.

---

# 20. Resource Management

Use context managers for resources that require deterministic cleanup.

Prefer:

```python
with path.open("r", encoding="utf-8") as file:
    data = file.read()
```

over manually opening and closing the resource.

This applies to:

* files;
* locks;
* database connections;
* network clients;
* temporary resources;
* other context-manager-compatible resources.

---

# 21. Filesystem and Paths

Use `pathlib.Path` for filesystem paths.

Prefer:

```python
path = Path("data") / "records.json"
```

over manual string concatenation.

Prefer explicit encodings for text files:

```python
path.write_text(content, encoding="utf-8")
```

Do not assume the current working directory unless that behavior is intentional and documented.

---

# 22. Datetime

Be explicit about timezone semantics.

Prefer timezone-aware datetimes when representing real-world timestamps.

Prefer UTC for internal storage and comparison when appropriate.

Avoid mixing naive and timezone-aware datetimes.

Be explicit about timestamp units.

Do not assume that a numeric timestamp is seconds if the source may use milliseconds.

Document ambiguous timestamp semantics at the data boundary.

---

# 23. External Data

Treat external data as untrusted.

External data includes:

* JSON;
* CSV;
* database rows;
* API responses;
* command output;
* configuration files;
* user input;
* archive files.

Validate data at the boundary.

Prefer:

```text
external data
    ↓
parse
    ↓
validate
    ↓
typed internal representation
    ↓
business logic
```

rather than spreading defensive checks throughout the application.

Do not assume external fields exist, have the expected type, or have valid values.

---

# 24. Serialization

Keep serialization concerns close to the boundary.

Avoid passing raw external dictionaries through the entire application when the data has a stable internal structure.

Prefer converting external data into a clear internal representation early.

For example:

```python
raw_record = load_json(...)
record = parse_record(raw_record)

process_record(record)
```

rather than:

```python
process_record(raw_record["data"]["attributes"]["value"])
```

throughout the codebase.

---

# 25. Logging

Use structured logging rather than `print()` for application diagnostics.

Use `print()` when producing intentional command-line output.

Logs should provide useful context without exposing secrets or sensitive information.

Do not log:

* passwords;
* tokens;
* API keys;
* credentials;
* sensitive user data.

Avoid excessive logging inside tight loops unless it is intentional and appropriately throttled.

---

# 26. CLI Applications

For command-line programs:

* use `argparse` or the project's established CLI framework;
* keep argument parsing separate from application logic;
* use a `main()` entry point;
* provide useful help text;
* return meaningful exit statuses;
* write machine-readable output when the command is intended for automation.

Typical structure:

```python
def main() -> None:
    parser = argparse.ArgumentParser(...)
    ...
    args = parser.parse_args()

    ...


if __name__ == "__main__":
    main()
```

Keep `main()` readable.

Move substantial business logic into testable functions.

---

# 27. Async and Concurrency

Use asynchronous or concurrent execution only when it addresses a real problem.

Async code is particularly appropriate for I/O-bound workloads with many concurrent operations.

Do not introduce async merely because a library supports it.

Consider:

* I/O latency;
* concurrency limits;
* cancellation;
* shared state;
* resource exhaustion;
* error propagation;
* ordering requirements.

Prefer simple synchronous code when concurrency provides no meaningful benefit.

---

# 28. Performance

Optimize at the correct level.

Prefer, in roughly this order:

1. correct algorithm;
2. appropriate data structure;
3. efficient I/O;
4. batching;
5. streaming;
6. caching where justified;
7. concurrency where appropriate;
8. low-level micro-optimizations.

Do not sacrifice readability for negligible performance improvements.

Measure performance before optimizing non-obvious code.

When performance is important, document relevant constraints and assumptions.

---

# 29. Security

Treat input as untrusted.

Avoid:

* unsafe deserialization;
* shell command construction from untrusted input;
* dynamic code execution;
* hard-coded credentials;
* insecure temporary-file handling;
* logging secrets.

When invoking subprocesses, prefer argument lists over shell command strings when possible.

Prefer:

```python
subprocess.run(
    ["git", "status", "--short"],
    check=True,
    capture_output=True,
    text=True,
)
```

over constructing shell commands through string interpolation.

Security-sensitive behavior should be explicit and reviewable.

---

# 30. Testing

Test behavior rather than implementation details.

Tests should verify:

* expected behavior;
* important edge cases;
* failure behavior;
* externally observable contracts.

Prefer focused tests.

Do not test trivial implementation details merely to increase coverage.

For important algorithms, include cases that expose boundary conditions.

For parsing and external data, test malformed and incomplete inputs.

---

# 31. Design and Abstraction

Introduce abstractions when they solve an actual problem.

Good reasons include:

* multiple implementations;
* meaningful domain concepts;
* isolation of external dependencies;
* testability;
* encapsulation of invariants;
* reducing duplicated complex logic.

Bad reasons include:

* "we might need this later";
* following a design pattern for its own sake;
* making a simple function look more architectural;
* hiding straightforward code behind multiple layers.

Prefer composition over inheritance unless inheritance expresses a genuine relationship and contract.

---

# 32. Anti-Patterns

Avoid the following unless there is a documented reason.

### God functions

Functions that parse input, perform business logic, access databases, write files, and format output all at once.

### God classes

Classes responsible for unrelated concerns.

### Generic utility modules

Large `utils.py` modules containing unrelated functions.

### Over-abstraction

Multiple classes or layers for a problem that can be solved clearly with a few functions.

### Clever code

Dense expressions that require explanation to understand.

### Premature optimization

Complex optimizations without evidence that performance requires them.

### Premature generalization

Designing for hypothetical future requirements.

### Silent error handling

Catching errors and continuing without preserving enough information to diagnose the problem.

### Hidden side effects

Functions whose names suggest a pure calculation but mutate global state, write files, or perform network operations.

---

# 33. Preferred Patterns

Prefer patterns that make intent obvious.

## Parse at the boundary

```python
raw_data = load_data(path)
record = parse_record(raw_data)

process(record)
```

## Validate once

```python
record = parse_and_validate(raw_data)

process(record)
```

rather than repeatedly checking the same assumptions throughout the application.

## Stream large inputs

```python
for record in records(path):
    process(record)
```

rather than loading the entire dataset when it is unnecessary.

## Keep the main workflow visible

Prefer:

```python
def main() -> None:
    args = parse_args()
    records = load_records(args.file)
    result = analyze(records)
    write_result(result)
```

over hiding the workflow behind multiple layers of indirection.

---

# 34. Examples of Good Python

The following characteristics are generally desirable:

```python
def find_oldest_activity(records: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the record containing the earliest known activity."""

    oldest: dict[str, Any] | None = None

    for record in records:
        timestamp = extract_earliest_timestamp(record)

        if timestamp is None:
            continue

        if oldest is None or timestamp < oldest["timestamp"]:
            oldest = {
                "record": record,
                "timestamp": timestamp,
            }

    return oldest
```

This style favors:

* explicit names;
* a clear workflow;
* a single responsibility;
* streaming iteration;
* constant extra space;
* explicit handling of missing data;
* straightforward control flow;
* a meaningful return contract.

---

# 35. What the AI Should Do

When writing Python code, the AI should:

1. follow this guide;
2. follow project-specific conventions;
3. use established Python conventions rather than inventing alternatives;
4. prefer simple, readable solutions;
5. choose data structures deliberately;
6. consider algorithmic complexity for non-trivial operations;
7. validate external data at boundaries;
8. keep side effects explicit;
9. avoid unnecessary abstractions;
10. use modern Python features when supported by the project;
11. preserve existing local conventions when reasonable;
12. use tooling for mechanical formatting and linting;
13. explain non-obvious engineering decisions when presenting the implementation.

The AI should not:

* rewrite unrelated code merely for stylistic consistency;
* introduce abstractions without a concrete reason;
* optimize prematurely;
* add dependencies without justification;
* invent project conventions;
* hide important behavior behind clever code.

---

# 36. When Explaining Code

When explaining generated or modified Python code:

Explain **engineering decisions**, not basic Python syntax.

Prioritize:

* algorithm choice;
* complexity;
* data structures;
* API design;
* type design;
* error handling;
* resource management;
* concurrency;
* performance;
* security;
* framework-specific behavior;
* important trade-offs;
* alternatives that were considered.

Do not explain obvious syntax such as:

* what `if` does;
* what a `for` loop does;
* what parentheses mean;
* what a function parameter is.

The goal is to improve engineering judgment, not teach Python syntax.

**Explain engineering, not syntax.**

---

# 37. Tooling

Mechanical rules should be enforced by tools whenever practical.

Typical tools include:

* formatter;
* linter;
* type checker;
* test runner.

The exact tools and configuration are project-specific.

Do not duplicate formatter or linter rules in this document unless the rule represents an engineering decision that tooling cannot adequately express.

This guide defines how code should be designed and written.

Tooling defines how mechanical violations are detected and corrected.

---

# 38. Final Rule

When several valid implementations exist, prefer the one that makes the important behavior easiest for another engineer to understand.

Optimize for:

**clarity → correctness → maintainability → appropriate performance**

Do not optimize for cleverness.
