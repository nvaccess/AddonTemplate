# Testing

This template provides a built-in testing structure powered by Python's standard `unittest` framework, supporting both unit tests and end-to-end (E2E) integration tests.

## Running All Tests Locally

To run the entire test suite (both unit and E2E tests) locally using `uv`:

```bash
uv run python -m unittest discover -s tests -v
```

## Unit Testing

Unit tests are located under the `tests/unit/` directory.

To execute tests for a specific unit test file:

```bash
uv run python -m unittest -v tests/unit/template/test_sanity.py
```

## End-to-End (E2E) Testing

End-to-end tests are located under the `tests/e2e/` directory to validate system-level workflows and CLI integration.

To execute tests for a specific E2E test file:

```bash
uv run python -m unittest -v tests/e2e/test_sanity.py
```
