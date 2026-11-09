# Testing

This template provides a built-in testing structure powered by Python's standard `unittest` framework, supporting both unit tests and end-to-end (E2E) integration tests.

## Running All Tests Locally

To run the entire test suite (both unit and E2E tests) locally using `uv`:

```bash
uv run python -m unittest discover -s tests -v
```

Here is what each part of the command does:

* `uv`: Executes the command within the virtual environment managed by `uv`.
* `python -m unittest discover`: Automatically finds and runs all test files (matching `test*.py`) within the specified test directory.
* `-s tests`: Sets the start directory for test discovery to the `tests/` folder.
* `-v`: Enables verbose output, displaying the status and description of each test method individually.

## Unit Testing

Unit tests are located under the `tests/unit/` directory to validate internal synchronization logic, AST modifications, and helpers.

To execute tests for a specific unit test file:

```bash
uv run python -m unittest -v tests/unit/template/test_syncAddonTool.py
```

## End-to-End (E2E) Testing

End-to-end tests are located under the `tests/e2e/` directory to validate system-level workflows, CLI interfaces, and real-world packaging.

To execute tests for a specific E2E test file:

```bash
uv run python -m unittest -v tests/e2e/template/test_syncAddonTool.py
```
