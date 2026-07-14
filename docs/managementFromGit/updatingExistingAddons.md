# Integrating the add-on template in your add-on

## Pre-requisites for initial setup

1. Create a repository, for example on GitHub, providing README and LICENSE files.

2. Clone the repository:

   ```sh
   cd {repoFolder}
   git clone https://github.com/{repoName}.git
   cd {repoName}
   ```

3. In the folder where your add-on repository is cloned, create an ```addon``` subfolder and store the code for your add-on.

4. Commit your changes:

   ```sh
   git add .
   git commit -m "Initial commit"
   ```

5. Add AddonTemplate as a remote:

   ```sh
   git remote add template https://github.com/nvaccess/AddonTemplate.git
   ```

6. Fetch the template:

   ```sh
   git fetch template
   ```

## Updating an Existing Add-on

AddonTemplate evolves over time and regularly receives improvements, bug fixes, new GitHub workflows, and build system updates.

The recommended way to keep your add-on synchronized with the latest version of AddonTemplate is to use the companion update script included with the template.

If you prefer to manage the update process yourself, a fully manual Git-based workflow is also available later in this document.

> [!NOTE]
> Updating from AddonTemplate only affects your project's infrastructure (build scripts, GitHub workflows, configuration files, etc.). It does **not** modify your add-on's source code.

---

## Recommended Method: Automated Update Using the Companion Tool

To streamline the synchronization process and avoid dealing with syntax errors or manual merge conflicts in infrastructure files, a companion update script is included in AddonTemplate: ```updateAddonFromTemplate.py```.

The script automatically supports updating two types of legacy add-ons:

- **Legacy Structure (Dictionary-based without pyproject.toml):** For older add-ons where `addon_info` was defined as a standard dictionary, the tool automatically migrates the metadata to the modern `AddonInfo` object structure, generates a new, fully populated `pyproject.toml` file matching the latest template standards, and synchronizes all infrastructure files.
- **Modern Structure (AddonInfo-based):** For newer add-ons that already use the `AddonInfo` object but need upstream template updates, the tool checks for any missing metadata keys in `buildVars.py` to insert them, and safely updates `pyproject.toml` dependencies and versions while preserving your custom configuration rules for tools like `pyright` and `ruff`.

### Prerequisites

Before running the tool, ensure your system meets the following requirements:

- **Python**: Version **3.13** or newer must be installed (matching the template's required Python version).
- **Git**: Git must be installed and available in your system ```PATH```.
- **Dependency Management (tomlkit)**: Because the automated script relies on the third-party `tomlkit` library to safely parse and merge configurations, it must be installed in your global Python environment before execution. This is necessary because legacy add-on repositories do not include this dependency yet, and it is not yet present by default in the template's stable `master` branch.

  To install or update `tomlkit` globally, run the following command in your terminal:

  ```sh
  python -m pip install -U tomlkit
  ```
  *(Note: Windows users using the standard Python launcher can replace `python` with `py` if needed: `py -m pip install -U tomlkit`)*

### Running the automated tool

The script is highly flexible and supports two execution modes:

1. **Standard Mode (No arguments):** Run the script directly from the root of your repository or from any of its subdirectories. It will automatically locate the project root by searching for `buildVars.py`.
2. **Target Directory Mode (With argument):** Run the script from any working directory by supplying the optional `addonDir` path (relative or absolute) pointing to the add-on repository you wish to update.

Before updating your repository:

- Ensure your working tree is clean.

  ```sh
  git status
  ```

- Commit or stash any pending changes.
- It is recommended to perform the update on a dedicated branch.

Run the update script in **Standard Mode**:

```sh
uv run updateAddonFromTemplate.py
```

Alternatively, run the script in **Target Directory Mode** by specifying the path to your add-on folder:

```sh
uv run updateAddonFromTemplate.py ../MyAddon
```

> [!NOTE]
> Before applying any modifications, the script creates an untracked backup directory located next to the add-on folder named `<addon>_bak_<timestamp>`. This directory contains a copy of the entire project before the update, allowing you to restore the previous state manually if necessary.

Once the update has completed, verify that the add-on still builds correctly:

```sh
uv sync
uv run scons
```

If everything builds successfully, stage and commit the updated infrastructure:

```sh
git add .
git commit -m "chore: sync infrastructure with AddonTemplate"
```

### Using the Update Tool via Command Line

The `updateAddonFromTemplate.py` script provides a non-destructive industrial update engine to align your local add-on repository layout with the latest structure of the official NVDA `AddonTemplate`.

You can execute the script with various command-line arguments to customize the update workflow.

#### Available Options

| Short Flag | Long Argument | Description | Default Value |
| :--- | :--- | :--- | :--- |
| `-ad` | `--addon-dir` | Path to the root directory of the local add-on you want to update. If not specified, the script automatically walks up from your current directory to find `buildVars.py`. | Current working directory |
| `-td` | `--template-dir` | Path to a local clone/directory of the NVDA `AddonTemplate`. When provided, the tool skips fetching the template via Git and synchronizes directly using this local reference. | None (clones from GitHub) |
| `-dr` | `--dry-run` | Simulates the execution. It analyzes structure, logs planned changes, and builds reports without writing or modifying any file on disk. | Disabled |
| `-s` | `--skip-backup` | Disables the automatic creation of a timestamped backup directory (e.g., `addonName_bak_YYYYMMDD_HHMMSS`) before processing updates. | Disabled (Backup is created) |
| `-h` | `--help` | Displays the default automated help menu listing all available parameters. | N/A |

#### Customizing Exclusions with .addonmergeignore

Rather than modifying the `updateAddonFromTemplate.py` core source code or changing its internal `PROTECTED_ELEMENTS` array, the update tool includes a robust file-exclusion system driven by a local file named `.addonmergeignore`.

This architectural design allows developers to cleanly decouple their project-specific freeze preferences from the update engine machinery.

##### How to Use `.addonmergeignore`
To declare custom exceptions, create a plain text file named `.addonmergeignore` and place it directly **at the root of your target add-on repository**. 
* Inside this file, list the names of the files or folders you want the tool to skip during synchronization.
* You can write one pattern per line. Empty lines and lines starting with `#` are automatically treated as comments and ignored.

For instance, if you wish to prevent the synchronization process from overwriting your custom execution scripts or your exclusion mapping file itself, simply add them to the file:
```
# Freeze the synchronization script version
updateaddonfromtemplate.py
# Protect your local merge settings file from being replaced
.addonmergeignore
```

##### Crucial Requirements & Design Constraints

1. **Case-Insensitivity:**
The update tool evaluates exclusions using a standardized, case-insensitive matching algorithm. This ensures maximum cross-platform reliability (especially between Windows and Unix-like environments). Since the script automatically normalizes all inputs to lowercase during execution, **you can write your rules using any casing you prefer** (e.g., `UpdateAddonFromTemplate.py` or `updateaddonfromtemplate.py` will both work perfectly).

2. **File Location Requirement:**
The update engine always loads custom exclusions from the target add-on's root folder being updated. Therefore, **the `.addonmergeignore` file must always reside inside the destination add-on directory**, even if you are executing the `updateAddonFromTemplate.py` script from a completely different directory or an external workspace.

#### Usage Examples

Depending on your workflow, the script can be executed either directly from within your add-on repository or from an external directory.

##### 1. Standard Automatic Update
Downloads the latest remote template, creates a safety backup of your repository, and non-destructively synchronizes the machinery files.

* **Syntax A (Script inside the add-on repository):**
```
python updateAddonFromTemplate.py
```

* **Syntax B (Script outside the add-on repository):**
```
python /path/to/updateAddonFromTemplate.py -ad /path/to/my-nvda-addon
```

##### 2. Updating from a Local Template Cache (Offline/Development)
Useful when testing local modifications applied to the `AddonTemplate` or when working without an active internet connection.

* **Syntax A (Script inside the add-on repository):**
```
python updateAddonFromTemplate.py -td /path/to/local/AddonTemplate
```

* **Syntax B (Script outside the add-on repository):**
```
python /path/to/updateAddonFromTemplate.py -ad /path/to/my-nvda-addon -td /path/to/local/AddonTemplate
```

##### 3. Simulating Changes Safely (Dry Run)
Analyzes structural layouts, evaluates configurations, reads the `.addonmergeignore` directives, and builds reports without writing anything to disk.

* **Syntax A (Script inside the add-on repository):**
```
python updateAddonFromTemplate.py --dry-run
```

* **Syntax B (Script outside the add-on repository):**
```
python /path/to/updateAddonFromTemplate.py --dry-run -ad /path/to/my-nvda-addon
```

##### 4. Speeding Up with Backup Omission
Target a project repository while skipping the automated safety backup creation phase to speed up execution.

* **Syntax A (Script inside the add-on repository):**
```
python updateAddonFromTemplate.py --skip-backup
```

* **Syntax B (Script outside the add-on repository):**
```
python /path/to/updateAddonFromTemplate.py -ad /path/to/my-nvda-addon --skip-backup
```

---

## Alternative Method: Manual Update Using Git Merge

If you prefer not to use the automated tool, you can manually merge the latest version of AddonTemplate into your repository.

### Before you begin

Before updating your repository:

- Ensure your working tree is clean.

  ```sh
  git status
  ```

- Commit or stash any pending changes.

- It is recommended to perform the update on a dedicated branch.

If anything goes wrong before the merge commit is created, and you haven't used the ```--squash``` option, you can safely cancel the operation using:

```sh
git merge --abort
```

### Adding the template repository

If you have not already done so, add AddonTemplate as a remote:

```sh
git remote add template https://github.com/nvaccess/AddonTemplate.git
```

Then fetch the latest changes:

```sh
git fetch template
```

### Merging the latest template

Merge the latest version of AddonTemplate:

```sh
git merge template/master --allow-unrelated-histories --squash
```

The ```--allow-unrelated-histories``` option is required because your add-on repository and AddonTemplate do not share a common Git history.

The ```--squash``` option stages all changes from the template as a single uncommitted change, helping keep your repository history cleaner.

At this stage, Git may report merge conflicts.

This is completely normal.

## Understanding merge conflicts

During the merge, Git attempts to combine the contents of both repositories automatically.

When Git cannot determine which version should be kept, it reports a merge conflict.

A conflict does **not** mean that something went wrong.

It simply means that some files require manual review.

### Resolving the merge

### Using the restore command

The ```restore``` command can be used to update files in your working directory, i.e. the folder where your add-on repository was cloned.

The ```--source``` option specifies where the files should be restored from.

### Keep your add-on documentation

Your add-on documentation should not be replaced by the template.

To restore the Markdown files from your repository and prevent them from being overwritten by the template, run:

```sh
git restore *.md --source=HEAD
```

### Remove the template documentation

The ```docs/``` directory belongs to AddonTemplate itself.

It is intended for developing AddonTemplate and should not become part of your add-on repository.

Remove it:

```sh
git rm -r docs
```

Alternatively, if the directory already exists in your repository, you can restore your own version:

```sh
git restore docs --source=HEAD
```

### Resolve ```buildVars.py```

```buildVars.py``` usually contains merge conflicts because it includes both:

- information specific to your add-on;
- variables introduced by newer versions of AddonTemplate.

Review the file carefully.

In general:

- keep your add-on metadata;
- preserve your version number;
- keep your custom settings;
- add any new variables introduced by the updated template.

### Resolve ```pyproject.toml```

```pyproject.toml``` is another file that commonly requires manual review.

Keep your project-specific configuration while incorporating any new settings required by the updated template.

### Other files

For most remaining infrastructure files, the version provided by AddonTemplate is generally the correct one.

Typical examples include:

- ```.github/```
- ```.gitignore```
- ```manifest.ini.tpl```
- ```manifest-translated.ini.tpl```
- ```site_scons/```
- ```sconstruct```

Review any conflicts if necessary before completing the merge.

## Completing the merge

Once all conflicts have been resolved, verify that the add-on still builds correctly:

```sh
uv sync
uv run scons
```

If everything builds successfully, stage the modified files:

```sh
git add .
```

Then create the commit:

```sh
git commit -m "chore: sync infrastructure with AddonTemplate"
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

Most conflicts occur in ```buildVars.py``` and ```pyproject.toml```.

Review the conflicting sections carefully and combine the changes from both versions.

If you are unsure whether a change comes from your add-on or from AddonTemplate, compare the conflicting section with the latest version of AddonTemplate before resolving it.

### I want to cancel the update

#### Automated update

Since the automated script creates an untracked timestamped full copy backup directory named `<addon>_bak_<timestamp>` before modifying any infrastructure files, you can restore your previous state manually from that folder if you decide not to keep the update.

If you have already staged some changes, you can also discard them using:

```sh
git restore . --staged
```

Then restore your working tree:

```sh
git restore . --source=HEAD
```

#### Manual update

If you have not yet committed the merge and **did not** use the ```--squash``` option, you can cancel it with:

```sh
git merge --abort
```

If you performed a squash merge, ```git merge --abort``` is no longer available because no merge state is recorded.

In this case, restore your repository with:

```sh
git restore . --staged
```

```sh
git restore . --source=HEAD
```

If you have already committed the update and want to return to the previous state, you can reset your branch:

```sh
git reset --hard {cleanBranch}
```
