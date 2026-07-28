# Unit Testing

This template provides a built-in unit testing structure powered by Python's standard `unittest` framework.

## Running Tests Locally

To run the unit test suite locally using `uv`:

``` bash
uv run python -m unittest discover -s tests -v
```

Or execute tests for a specific file:

``` bash
uv run python -m unittest -v tests/unit/template/test_sanity.py
```
