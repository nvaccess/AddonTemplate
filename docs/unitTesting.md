# Unit Testing

This template provides a built-in unit testing structure powered by Python's standard `unittest` framework.

Ensuring your add-on and tooling behavior remains consistent during development and following template updates is done through automated unit testing.

## Running Tests Locally

For unit tests to execute successfully, target modules (such as `syncAddonWithTemplate.py`) must be located at the root of the repository as sibling files to the `tests/` directory (at the same hierarchical level). This ensures Python's module discovery properly imports scripts when `unittest` runs from the project root.

### Run the Full Test Suite

To run the entire unit test suite with automatic test discovery and detailed output for every executed test case:

``` bash
uv run python -m unittest discover -s tests -v
```

Here is what each part of the command does:
* `uv run`: Executes the command within the virtual environment managed by `uv`.
* `python -m unittest discover`: Automatically finds and runs all test files (matching `test*.py`) within the specified test directory.
* `-s tests`: Sets the start directory for test discovery to the `tests/` folder.
* `-v`: Enables verbose output, displaying the status and description of each test method individually.

### Run Specific Test Suites

You can run individual test modules during development by specifying their path:

* **Add-on Synchronization Tool Tests:**
  ``` bash
  uv run python -m unittest -v tests/unit/template/test_syncAddonTool
  ```

---

