# Integrating the add-on template in your add-on

## Pre-requisites for initial setup

1. Create a repository, for example on GitHub, providing README and LICENSE files.

2. Clone the repository:

   ```sh
   cd {repoFolder}
   git clone https://github.com/{repoName}.git
   ```

3. In the folder where your add-on repository is cloned, create an `addon` subfolder and store the code for your add-on.

4. Go to the repository root:

   ```sh
   cd {repoFolder}
   ```

5. Commit your changes:

   ```sh
   git add .
   git commit -m "Initial commit"
   ```

6. Add AddonTemplate as a remote:

   ```sh
   git remote add template https://github.com/nvaccess/AddonTemplate.git
   ```

7. Fetch the template:

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

To streamline the synchronization process and avoid dealing with syntax errors or manual merge conflicts in infrastructure files, a companion update script is included within the template workspace: `updateAddon.py`.

The script automatically handles the update process while preserving the information specific to your add-on.

Among other things, it:

- updates infrastructure files from the latest version of AddonTemplate;
- preserves your add-on metadata;
- merges `buildVars.py` and `pyproject.toml`;
- removes placeholder metadata (such as `nvaccess` from the authors list when updating a third-party add-on);
- creates a backup of the original infrastructure files before applying any modifications.

### Prerequisites

Before running the tool, ensure your system meets the following requirements:

- **Python**: Version **3.11** or newer must be installed.
- **Git**: Git must be installed and available in your system `PATH`.

### Running the automated tool

The script is designed to be flexible and can be executed either from the root of your repository or from any other working directory.

Before updating your repository:

- Ensure your working tree is clean.

  ```sh
  git status
  ```

- Commit or stash any pending changes.
- It is recommended to perform the update on a dedicated branch.

Fetch the latest version of AddonTemplate:

```sh
git fetch template
```

Run the update script:

```sh
uv run updateAddon.py
```

> [!NOTE]
> Before modifying any infrastructure files, the script creates an untracked `_bak_` directory containing backups of every file it updates. If necessary, you can restore these files manually.

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

### Excluding specific template files

By default, the script synchronizes every infrastructure file provided by AddonTemplate.

If you want to preserve specific files from your repository (for example, a customized GitHub workflow), you can exclude them from synchronization.

Open `updateAddon.py` and locate the `IGNORED_FILES` set near the beginning of the `main()` function:

```python
IGNORED_FILES = {
    os.path.join(".github", "workflows", "build_addon.yml").lower(),
}
```

Add any relative path from the template root to this set to prevent that file from being synchronized.

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

If anything goes wrong before the merge commit is created, and you haven't used the `--squash` option, you can safely cancel the operation using:

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

The `--allow-unrelated-histories` option is required because your add-on repository and AddonTemplate do not share a common Git history.

The `--squash` option stages all changes from the template as a single uncommitted change, helping keep your repository history cleaner.

At this stage, Git may report merge conflicts.

This is completely normal.

## Understanding merge conflicts

During the merge, Git attempts to combine the contents of both repositories automatically.

When Git cannot determine which version should be kept, it reports a merge conflict.

A conflict does **not** mean that something went wrong.

It simply means that some files require manual review.
### Resolving the merge

### Using the restore command

The `restore` command can be used to update files in your working directory, i.e. the folder where your add-on repository was cloned.

The `--source` option specifies where the files should be restored from.

### Keep your add-on documentation

Your add-on documentation should not be replaced by the template.

To restore the Markdown files from your repository and prevent them from being overwritten by the template, run:

```sh
git restore *.md --source=HEAD
```

### Remove the template documentation

The `docs/` directory belongs to AddonTemplate itself.

It is intended for developing AddonTemplate and should not become part of your add-on repository.

Remove it:

```sh
git rm -r docs
```

Alternatively, if the directory already exists in your repository, you can restore your own version:

```sh
git restore docs --source=HEAD
```

### Resolve `buildVars.py`

`buildVars.py` usually contains merge conflicts because it includes both:

- information specific to your add-on;
- variables introduced by newer versions of AddonTemplate.

Review the file carefully.

In general:

- keep your add-on metadata;
- preserve your version number;
- keep your custom settings;
- add any new variables introduced by the updated template.

### Resolve `pyproject.toml`

`pyproject.toml` is another file that commonly requires manual review.

Keep your project-specific configuration while incorporating any new settings required by the updated template.

### Other files

For most remaining infrastructure files, the version provided by AddonTemplate is generally the correct one.

Typical examples include:

- `.github/`
- `.gitignore`
- `manifest.ini.tpl`
- `manifest-translated.ini.tpl`
- `site_scons/`
- `sconstruct`

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

Most conflicts occur in `buildVars.py` and `pyproject.toml`.

Review the conflicting sections carefully and combine the changes from both versions.

If you are unsure whether a change comes from your add-on or from AddonTemplate, compare the conflicting section with the latest version of AddonTemplate before resolving it.

### I want to cancel the update

#### Automated update

Since `updateAddon.py` creates an untracked `_bak_` directory before modifying any infrastructure files, you can restore the previous versions manually if you decide not to keep the update.

If you have already staged some changes, you can also discard them using:

```sh
git restore . --staged
```

Then restore your working tree:

```sh
git restore . --source=HEAD
```

#### Manual update

If you have not yet committed the merge and **did not** use the `--squash` option, you can cancel it with:

```sh
git merge --abort
```

If you performed a squash merge, `git merge --abort` is no longer available because no merge state is recorded.

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
