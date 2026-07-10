# Integrating the add-on template in your add-on[cite: 5]

## Pre-requisites for initial setup[cite: 5]

1. Create a repository, for example on GitHub, providing README and LICENSE files.[cite: 5]

2. Clone the repository:[cite: 5]

   ```sh
   cd {repoFolder}
   git clone https://github.com/{repoName}.git
   ```

3. In the folder where your add-on repository is cloned, create an ```addon``` subfolder and store the code for your add-on.[cite: 5]

4. Go to the repository root:[cite: 5]

   ```sh
   cd {repoFolder}
   ```

5. Commit your changes:[cite: 5]

   ```sh
   git add .
   git commit -m "Initial commit"
   ```

6. Add AddonTemplate as a remote:[cite: 5]

   ```sh
   git remote add template https://github.com/nvaccess/AddonTemplate.git
   ```

7. Fetch the template:[cite: 5]

   ```sh
   git fetch template
   ```

## Updating an Existing Add-on[cite: 5]

AddonTemplate evolves over time and regularly receives improvements, bug fixes, new GitHub workflows, and build system updates.[cite: 5]

The recommended way to keep your add-on synchronized with the latest version of AddonTemplate is to use the companion update script included with the template.[cite: 5]

If you prefer to manage the update process yourself, a fully manual Git-based workflow is also available later in this document.[cite: 5]

> [!NOTE]
> Updating from AddonTemplate only affects your project's infrastructure (build scripts, GitHub workflows, configuration files, etc.). It does **not** modify your add-on's source code.[cite: 5]

---

## Recommended Method: Automated Update Using the Companion Tool[cite: 5]

To streamline the synchronization process and avoid dealing with syntax errors or manual merge conflicts in infrastructure files, a companion update script is included within the template workspace: ```updateAddonFromTemplate.py```.[cite: 5]

The script automatically handles the update process while preserving the information specific to your add-on.[cite: 5]

Among other things, it:[cite: 5]

- updates infrastructure files from the latest version of AddonTemplate;[cite: 5]
- preserves your add-on metadata;[cite: 5]
- merges ```buildVars.py``` and ```pyproject.toml```;[cite: 5]
- removes placeholder metadata (such as ```nvaccess``` from the authors list when updating a third-party add-on);[cite: 5]
- creates a backup of the original infrastructure files before applying any modifications.[cite: 5]

### Prerequisites[cite: 5]

Before running the tool, ensure your system meets the following requirements:[cite: 5]

- **Python**: Version **3.11** or newer must be installed.[cite: 5]
- **Git**: Git must be installed and available in your system ```PATH```.[cite: 5]

### Running the automated tool[cite: 5]

The script is designed to be flexible and can be executed either from the root of your repository or from any other working directory.[cite: 5]

Before updating your repository:[cite: 5]

- Ensure your working tree is clean.[cite: 5]

  ```sh
  git status
  ```

- Commit or stash any pending changes.[cite: 5]
- It is recommended to perform the update on a dedicated branch.[cite: 5]

Fetch the latest version of AddonTemplate:[cite: 5]

```sh
git fetch template
```

Run the update script:[cite: 5]

```sh
uv run updateAddonFromTemplate.py
```

> [!NOTE]
> Before modifying any infrastructure files, the script creates an untracked ```_bak_``` directory containing backups of every file it updates. If necessary, you can restore these files manually.[cite: 5]

Once the update has completed, verify that the add-on still builds correctly:[cite: 5]

```sh
uv sync
uv run scons
```

If everything builds successfully, stage and commit the updated infrastructure:[cite: 5]

```sh
git add .
git commit -m "chore: sync infrastructure with AddonTemplate"
```

### Excluding specific template files[cite: 5]

By default, the script synchronizes every infrastructure file provided by AddonTemplate.[cite: 5]

If you want to preserve specific files from your repository (for example, a customized GitHub workflow), you can exclude them from synchronization.[cite: 5]

Open ```updateAddonFromTemplate.py``` and locate the ```IGNORED_FILES``` set near the beginning of the ```main()``` function:[cite: 5]

```python
IGNORED_FILES = {
    os.path.join(".github", "workflows", "build_addon.yml").lower(),
}
```

Add any relative path from the template root to this set to prevent that file from being synchronized.[cite: 5]

---

## Alternative Method: Manual Update Using Git Merge[cite: 5]

If you prefer not to use the automated tool, you can manually merge the latest version of AddonTemplate into your repository.[cite: 5]

### Before you begin[cite: 5]

Before updating your repository:[cite: 5]

- Ensure your working tree is clean.[cite: 5]

  ```sh
  git status
  ```

- Commit or stash any pending changes.[cite: 5]

- It is recommended to perform the update on a dedicated branch.[cite: 5]

If anything goes wrong before the merge commit is created, and you haven't used the ```--squash``` option, you can safely cancel the operation using:[cite: 5]

```sh
git merge --abort
```

### Adding the template repository[cite: 5]

If you have not already done so, add AddonTemplate as a remote:[cite: 5]

```sh
git remote add template https://github.com/nvaccess/AddonTemplate.git
```

Then fetch the latest changes:[cite: 5]

```sh
git fetch template
```

### Merging the latest template[cite: 5]

Merge the latest version of AddonTemplate:[cite: 5]

```sh
git merge template/master --allow-unrelated-histories --squash
```

The ```--allow-unrelated-histories``` option is required because your add-on repository and AddonTemplate do not share a common Git history.[cite: 5]

The ```--squash``` option stages all changes from the template as a single uncommitted change, helping keep your repository history cleaner.[cite: 5]

At this stage, Git may report merge conflicts.[cite: 5]

This is completely normal.[cite: 5]

## Understanding merge conflicts[cite: 5]

During the merge, Git attempts to combine the contents of both repositories automatically.[cite: 5]

When Git cannot determine which version should be kept, it reports a merge conflict.[cite: 5]

A conflict does **not** mean that something went wrong.[cite: 5]

It simply means that some files require manual review.[cite: 5]
### Resolving the merge[cite: 5]

### Using the restore command[cite: 5]

The ```restore``` command can be used to update files in your working directory, i.e. the folder where your add-on repository was cloned.[cite: 5]

The ```--source``` option specifies where the files should be restored from.[cite: 5]

### Keep your add-on documentation[cite: 5]

Your add-on documentation should not be replaced by the template.[cite: 5]

To restore the Markdown files from your repository and prevent them from being overwritten by the template, run:[cite: 5]

```sh
git restore *.md --source=HEAD
```

### Remove the template documentation[cite: 5]

The ```docs/``` directory belongs to AddonTemplate itself.[cite: 5]

It is intended for developing AddonTemplate and should not become part of your add-on repository.[cite: 5]

Remove it:[cite: 5]

```sh
git rm -r docs
```

Alternatively, if the directory already exists in your repository, you can restore your own version:[cite: 5]

```sh
git restore docs --source=HEAD
```

### Resolve ```buildVars.py```[cite: 5]

```buildVars.py``` usually contains merge conflicts because it includes both:[cite: 5]

- information specific to your add-on;[cite: 5]
- variables introduced by newer versions of AddonTemplate.[cite: 5]

Review the file carefully.[cite: 5]

In general:[cite: 5]

- keep your add-on metadata;[cite: 5]
- preserve your version number;[cite: 5]
- keep your custom settings;[cite: 5]
- add any new variables introduced by the updated template.[cite: 5]

### Resolve ```pyproject.toml```[cite: 5]

```pyproject.toml``` is another file that commonly requires manual review.[cite: 5]

Keep your project-specific configuration while incorporating any new settings required by the updated template.[cite: 5]

### Other files[cite: 5]

For most remaining infrastructure files, the version provided by AddonTemplate is generally the correct one.[cite: 5]

Typical examples include:[cite: 5]

- ```.github/```[cite: 5]
- ```.gitignore```[cite: 5]
- ```manifest.ini.tpl```[cite: 5]
- ```manifest-translated.ini.tpl```[cite: 5]
- ```site_scons/```[cite: 5]
- ```sconstruct```[cite: 5]

Review any conflicts if necessary before completing the merge.[cite: 5]

## Completing the merge[cite: 5]

Once all conflicts have been resolved, verify that the add-on still builds correctly:[cite: 5]

```sh
uv sync
uv run scons
```

If everything builds successfully, stage the modified files:[cite: 5]

```sh
git add .
```

Then create the commit:[cite: 5]

```sh
git commit -m "chore: sync infrastructure with AddonTemplate"
```

## Summary[cite: 5]

| File or directory | Recommended action |
|-------------------|--------------------|
| `README.md` | Keep the add-on version |
| `CHANGELOG.md` | Keep the add-on version |
| `docs/` | Remove |
| `buildVars.py` | Merge manually |
| `pyproject.toml` | Merge manually |
| Other template files | Usually accept the template version |

## Troubleshooting[cite: 5]

### I don't understand a merge conflict[cite: 5]

Merge conflicts are expected when updating from a newer version of AddonTemplate.[cite: 5]

Most conflicts occur in ```buildVars.py``` and ```pyproject.toml```.[cite: 5]

Review the conflicting sections carefully and combine the changes from both versions.[cite: 5]

If you are unsure whether a change comes from your add-on or from AddonTemplate, compare the conflicting section with the latest version of AddonTemplate before resolving it.[cite: 5]

### I want to cancel the update[cite: 5]

#### Automated update[cite: 5]

Since ```updateAddonFromTemplate.py``` creates an untracked ```_bak_``` directory before modifying any infrastructure files, you can restore the previous versions manually if you decide not to keep the update.[cite: 5]

If you have already staged some changes, you can also discard them using:[cite: 5]

```sh
git restore . --staged
```

Then restore your working tree:[cite: 5]

```sh
git restore . --source=HEAD
```

#### Manual update[cite: 5]

If you have not yet committed the merge and **did not** use the ```--squash``` option, you can cancel it with:[cite: 5]

```sh
git merge --abort
```

If you performed a squash merge, ```git merge --abort``` is no longer available because no merge state is recorded.[cite: 5]

In this case, restore your repository with:[cite: 5]

```sh
git restore . --staged
```

```sh
git restore . --source=HEAD
```

If you have already committed the update and want to return to the previous state, you can reset your branch:[cite: 5]

```sh
git reset --hard {cleanBranch}
```
