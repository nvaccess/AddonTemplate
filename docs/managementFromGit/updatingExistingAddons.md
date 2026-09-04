# Integrating the add-on template in your add-on

## Pre-requisites

1. Create a repository, for example on GitHub, providing readme and license files.
1. Clone the repository:

  ```sh
  git clone https://github.com/{repoName}.git
  ```

1. In the folder where your add-on repository is cloned, create an `addon` submolder and store the code for your add-on.

1. Go to the folder where your repository was cloned:

  ```sh
  cd {repoFolder}
  ```

1. Commit your changes:

  ```sh
  git add .
  git commit -m "Initial commit"
  ```

1. Add the template as a remote:

  ```sh
  git remote add template https://github.com/nvaccess/addonTemplate.git
  ```

1. Fetch the add-on template:

  ```sh
  git fetch template
  ```

## Updating an Existing Add-on

As AddonTemplate evolves, it receives improvements, bug fixes, new GitHub workflows, and build system updates.

You can merge the latest template changes into your repository instead of manually copying updated files.

*This document explains the update procedures, including both the recommended automated method using `syncAddonTool` and the manual Git merge workflow."*

> [!NOTE]
> Updating from AddonTemplate only affects your project's infrastructure (build scripts, GitHub workflows, configuration files, etc.). It does **not** modify your add-on's source code.

## Before you begin

Before updating your repository:

- Ensure your working tree is clean.

  ```sh
  git status
  ```

- Commit or stash any pending changes.

- It is recommended to perform the update on a dedicated branch.

If anything goes wrong before the merge commit is created, if you haven't passed the `--squash- flag, you can safely cancel the operation using:

```sh
git merge --abort
```

## Adding the template repository

If you have not already done so, add AddonTemplate as a remote:

```sh
git remote add template https://github.com/nvaccess/AddonTemplate.git
```

Then fetch the latest changes:

```sh
git fetch template
```

## Recommended Method: Automated Update Using the Companion Tool

To streamline the synchronization process and avoid dealing with syntax errors or manual merge conflicts in infrastructure files, a companion utility script is included in AddonTemplate: `syncAddonTool`.

This tool automatically extracts your legacy project settings (such as the add-on name, summary, authors, and repository URL from `buildVars.py`) and merges them cleanly into the newly generated `pyproject.toml` file, while safely preserving empty values if certain metadata is not set.

This automation ensures a seamless transition to the new template infrastructure without losing your original configuration.

The tool automatically supports updating two types of legacy add-ons:

- **Legacy Structure (Dictionary-based without pyproject.toml):**
  For older add-ons where `addon_info` was defined as a standard dictionary, the tool automatically migrates the metadata to the modern `AddonInfo` object structure.
  It generates a new, fully populated `pyproject.toml` file matching the latest template standards, and synchronizes all infrastructure files.

- **Modern Structure (AddonInfo-based):**
  For newer add-ons that already use the `AddonInfo` object but need upstream template updates, the tool checks for any missing metadata keys in `buildVars.py` to insert them.
  It safely updates `pyproject.toml` dependencies and versions while preserving your custom configuration rules for tools like `pyright` and `ruff`.

### Prerequisites

Before running the tool, ensure your system meets the following requirements:

- **Python**:
  Version **3.13** or newer must be installed (matching the template's required Python version).

- **Git**:
  Git must be installed and available in your system `PATH`.

- For add-ons without a pyproject.toml file, **Dependency Management (tomlkit)**:
  Because the automated script relies on the third-party `tomlkit` library to safely parse and merge configurations, it must be available in the Python environment used to run the script (either installed in the environment, or provided temporarily via `uv run --with tomlkit`).

> [!IMPORTANT]
> **Project Structure & Execution Methods:**
> The update engine is structured as a Python package that relies on the `syncAddonTool/` directory layout.
> You can copy the `syncAddonTool/` folder directly into any add-on repository and run `uv run python syncAddonTool`.
> Alternatively, if you prefer to run the tool from an external directory outside of the target repository, you can specify its location using the `-ad` parameter: `uv run python -m syncAddonTool -ad /path/to/my-nvda-addon`.
> Finally, you can use the standalone executable (`syncAddonTool.exe`), which requires no Python dependencies.

### Running the automated tool

The tool is highly flexible and supports two execution modes:

1. **Standard Mode (No arguments):**
   Run the tool directly from the root of your repository or from any of its subdirectories.
   It will automatically locate the project root by searching for `buildVars.py`.

   ```sh
   uv run python syncAddonTool
   ```

2. **Target Directory Mode (With argument):**
   Run the tool from any working directory by supplying the optional `addonDir` path (relative or absolute) pointing to the add-on repository you wish to update.

   ```sh
   uv run python syncAddonTool -ad ../MyAddon
   ```

> [!NOTE]
> Before applying any modifications, the tool creates an untracked backup directory located next to the add-on folder named `<addon>_bak_<timestamp>`.
> This directory contains a copy of the entire project before the update, allowing you to restore the previous state manually if necessary.

Once the update has completed, verify that the add-on still builds correctly:

```sh
uv sync
uv run scons
```

If everything builds successfully, remove the `<addon>_bak_<timestamp>` directory, stage and commit the updated infrastructure:

```sh
git clean -f
git add .
git commit -m "chore: sync infrastructure with AddonTemplate"
```

### Using the Update Tool via Command Line

The `syncAddonTool` tool provides a non-destructive industrial update engine to align your local add-on repository layout with the latest structure of the official NVDA `AddonTemplate`.

You can execute the tool with various command-line arguments to customize the update workflow.

#### Available Options

| Short Flag | Long Argument | Description | Default Value |
| :--- | :--- | :--- | :--- |
| `-ad` | `--addon-dir` | Path to the root directory of the local add-on you want to update. If not specified, the script automatically walks up from your current directory to find `buildVars.py`. | Current working directory |
| `-td` | `--template-dir` | Path to a local clone/directory of the NVDA `AddonTemplate`. When provided, the tool skips fetching the template via Git and synchronizes directly using this local reference. | None (clones from GitHub) |
| `-dr` | `--dry-run` | Simulates the execution. It analyzes structure, logs planned changes, and builds reports without writing or modifying any file on disk. | Disabled |
| `-s` | `--skip-backup` | Disables the automatic creation of a timestamped backup directory (e.g., `addonName_bak_YYYYMMDD_HHMMSS`) before processing updates. | Disabled (Backup is created) |
| `-v` | `--verbose` | Enables detailed debug logging output (`[DEBUG]` level) in the console/log output. | Disabled (`[INFO]` level) |
| `-h` | `--help` | Displays the default automated help menu listing all available parameters. | N/A |

##### 1. Generating the Executable

Since the `syncAddonTool.spec` configuration file is provided inside the `syncAddonTool` directory, you can build the standalone executable using `uv` and PyInstaller:

```sh
uv run --with pyinstaller pyinstaller syncAddonTool/syncAddonTool.spec
```

The compiled executable will be generated inside the `dist/` folder (`dist/syncAddonTool.exe`).

##### 2. Running the Executable

Once compiled or downloaded, `syncAddonTool.exe` accepts the exact same command-line flags (`-ad`, `-td`, `--dry-run`, `--skip-backup`) as the Python execution modes:

- **Targeting an add-on directory from anywhere**:

  ```cmd
  syncAddonTool.exe -ad C:\path\to\my-nvda-addon
  ```

- **Performing a dry-run test**:

  ```cmd
  syncAddonTool.exe -ad C:\path\to\my-nvda-addon --dry-run
  ```

#### Customizing Exclusions with `.addonmergeignore`

Rather than modifying the `syncAddonTool` core source code or changing its internal `PROTECTED_ELEMENTS` array, the update tool includes a robust file-exclusion system driven by a local file named `.addonmergeignore`.

This architectural design allows developers to cleanly decouple their project-specific freeze preferences from the update engine machinery.

##### How to Use `.addonmergeignore`

To declare custom exceptions, create a plain text file named `.addonmergeignore` and place it directly **at the root of your target add-on repository**.

- Inside this file, list the names, relative paths, or glob patterns of the files or folders you want the tool to skip during synchronization.
- The file uses standard `.gitignore` pattern matching syntax (parsed via `pathspec`).
- You can write one pattern per line. Empty lines and lines starting with `#` are automatically treated as comments and ignored.

For instance, if you wish to prevent the synchronization process from overwriting your custom execution scripts or specific workflows, simply add them to the file:

```gitignore
# Preserve local release workflows
.github/workflows/release.yml

# Protect custom localized documentation
addon/doc/fr/custom-extra-help.html
```

##### Crucial Requirements & Design Constraints

1. **Automatic Self-Exclusion:**
   The update tool automatically protects `.addonmergeignore` itself from being overwritten during synchronization. Even if `.addonmergeignore` is present in the template repository, the target add-on's local `.addonmergeignore` file is preserved without needing to explicitly list itself.

2. **Presence Check on Initial Run:**
   Before copying or updating any template files, the script explicitly checks whether `.addonmergeignore` is already present or absent at the root of the target add-on repository. If present, its custom rules are loaded immediately before processing any file transfers.

3. **Case-Insensitivity:**
   The update tool evaluates exclusions using a standardized, case-insensitive matching algorithm.
   This ensures maximum cross-platform reliability (especially between Windows and Unix-like environments).
   Since the tool automatically normalizes all inputs to lowercase during execution, **you can write your rules using any casing you prefer** (e.g., `UpdateAddonFromTemplate.py` or `updateaddonfromtemplate.py` will both work perfectly).

4. **File Location Requirement:**
   The update engine always loads custom exclusions from the target add-on's root folder being updated.
   Therefore, **the `.addonmergeignore` file must always reside inside the destination add-on directory**, even if you are executing the `syncAddonTool` tool from a completely different directory or an external workspace.

#### Usage Examples

Depending on your workflow, the synchronization tool can be executed directly using `uv` with `syncAddonTool` directory, via Python module flags (`-m`), or using the standalone executable (`syncAddonTool.exe`).

##### 1. Standard Automatic Update

Downloads the latest remote template, creates a safety backup of your repository, and non-destructively synchronizes the machinery files.

- **Syntax A (Directory execution inside the add-on repository)**:

  ```sh
  uv run python syncAddonTool
  ```

- **Syntax B (Targeting an external add-on directory)**:

  ```sh
  uv run python syncAddonTool -ad /path/to/my-nvda-addon
  ```

- **Syntax C (Standalone executable)**:

  ```cmd
  syncAddonTool.exe -ad C:\path\to\my-nvda-addon
  ```

##### 2. Updating from a Local Template Cache (Offline/Development)

Useful when testing local modifications applied to `AddonTemplate` or when working without an active internet connection.

- **Syntax A (Directory execution inside the add-on repository)**:

  ```sh
  uv run python syncAddonTool -td /path/to/local/AddonTemplate
  ```

- **Syntax B (Targeting an external add-on directory)**:

  ```sh
  uv run python syncAddonTool -ad /path/to/my-nvda-addon -td /path/to/local/AddonTemplate
  ```

- **Syntax D (Standalone executable)**:

  ```cmd
  syncAddonTool.exe -ad C:\path\to\my-nvda-addon -td C:\path\to\local\AddonTemplate
  ```

##### 3. Simulating Changes Safely (Dry Run)

Analyzes structural layouts, evaluates configurations, reads `.addonmergeignore` directives, and builds reports without writing anything to disk.

- **Syntax A (Directory execution inside the add-on repository)**:

  ```sh
  uv run python syncAddonTool --dry-run
  ```

- **Syntax B (Targeting an external add-on directory)**:

  ```sh
  uv run python syncAddonTool --dry-run -ad /path/to/my-nvda-addon
  ```

- **Syntax C (Standalone executable)**:

  ```cmd
  syncAddonTool.exe --dry-run -ad C:\path\to\my-nvda-addon
  ```

##### 4. Speeding Up with Backup Omission

Targets a project repository while skipping the automated safety backup creation phase to speed up execution.

- **Syntax A (Directory execution inside the add-on repository)**:

  ```sh
  uv run python syncAddonTool --skip-backup
  ```

- **Syntax B (Targeting an external add-on directory)**:

  ```sh
  uv run python syncAddonTool -ad /path/to/my-nvda-addon --skip-backup
  ```

- **Syntax C (Standalone executable)**:

  ```cmd
  syncAddonTool.exe -ad C:\path\to\my-nvda-addon --skip-backup
  ```

##### 5. Run without Prior Installation (`--with` option)

If you wish to execute the synchronization tool without installing its required third-party dependencies (like `tomlkit`) into your active environment beforehand, you can request `uv` to expose them temporarily during command execution:

- **Using directory execution with `uv`**:

  ```sh
  uv run --with tomlkit python syncAddonTool
  ```

- **Using module execution with `uv`**:

  ```sh
  uv run --with tomlkit python -m syncAddonTool
  ```

- **Using Standalone Executable**:

  *(Note: No `--with` option or dependency installation is needed when running `syncAddonTool.exe`, as all required dependencies are already bundled inside the executable.)*

  ```cmd
  syncAddonTool.exe
  ```

---

## Alternative Method: Manual Update Using Git Merge

If you prefer not to use the automated tool, you can manually merge the latest version of AddonTemplate into your repository.

Merge the latest version of AddonTemplate:

```sh
git merge template/master --allow-unrelated-histories --squash
```

The `--allow-unrelated-histories` option is required because your add-on repository and AddonTemplate do not share a common Git history.

The `--squash` flags will add changes from the template as a unique commit, instead of several ones, what may be useful to keep a cleaner history on your repository.

At this stage, Git may report merge conflicts.

This is completely normal.

## Understanding merge conflicts

During the merge, Git attempts to combine the contents of both repositories automatically.

When Git cannot determine which version should be kept, it reports a merge conflict.

A conflict does **not** mean that something went wrong.
It simply means that some files require manual review.

## Resolving the merge

### Using the restore command

The `restore` command can be used to update files on your working directory, i.e., the folder where your add-on repository was cloned.
The `--source` flag is used to determine where files to be restored can be found.

### Keep your add-on documentation

Your add-on documentation should not be replaced by the template.

To keep your `.md` files from your add-on repository, ensuring they aren't replaced with files from the template, you can use the following command:

```sh
git restore *.md --source=HEAD
```

### Remove the template documentation

The `docs/` directory belongs to AddonTemplate itself.

It is not intended to become part of your add-on repository.

Remove it:

```
git rm -r docs
```

Or use the restore command:

```sh
git restore docs --source=HEAD
```

### Resolve buildVars.py

`buildVars.py` usually contains merge conflicts because it includes both:

- information specific to your add-on;
- variables introduced by newer versions of AddonTemplate.

Review the file carefully.

In general:

- keep your add-on metadata;
- preserve your version number;
- keep your custom settings;
- add any new variables introduced by the template.

### Resolve pyproject.toml

`pyproject.toml` is another file that commonly requires manual review.

Keep your project-specific configuration while incorporating any new settings required by the updated template.

### Other files

For most remaining files, the version provided by AddonTemplate is generally the correct one.

Typical examples include:

- `.github/`
- `.gitignore`
- `manifest.ini.tpl`
- `manifest-translated.ini.tpl`
- `site_scons/`
- `sconstruct`

Review any conflicts if necessary before completing the merge.

## Completing the merge

Once all conflicts have been resolved, check if the add-on can be built properly:

```sh
uv sync  # Update dependencies
uv run scons  # Build the add-on
```


If all is right, stage the modified files:

```sh
git add .
```

Then create the merge commit:

```sh
git commit
```

## Summary

| File or directory | Recommended action |
|-------------------|--------------------|
| `README.md` | Keep the add-on version |
| `CHANGELOG.md` | Keep the add-on version |
| `docs/` | Remove |
| `buildVars.py` | Merge manually |
| `pyproject.toml` | Merge manually |
| Other template files | Usually accept the template version |

## Troubleshooting

### I don't understand a merge conflict

Merge conflicts are expected when updating from a newer version of AddonTemplate.

Most conflicts occur in `buildVars.py` and `pyproject.toml`.

Review the conflicting sections carefully and combine the changes from both versions.

### I want to cancel the update

If you have not yet committed the merge, and you haven't passed the `--squash` flag to `git merge`, you can restore your repository to its previous state:

```sh
git merge --abort
```

If you passed the `--squash` flag, `git merge --abort` won't work.
In this case, you can use the restore command:

```sh
git restore  . --staged  # Discard changes added to the staging area (after using `git add .`)
```

```sh
git restore . --source=HEAD  # Restores the working directory to the last commit made in your add-on repository
```

If you committed changes, you can use:

```sh
git reset --hard {cleanBranch}
```
