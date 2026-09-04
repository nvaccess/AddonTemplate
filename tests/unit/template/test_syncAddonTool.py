# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Unit test suite for syncAddonTool package."""

import tempfile
import unittest
from pathlib import Path

# Import functions from their exact module location within syncAddonTool
from syncAddonTool.buildVarsSync import extractBuildvarsMetadata, mergeBuildvarsFile
from syncAddonTool.engine import runSynchronization, setupAddonMergeIgnore
from syncAddonTool.pyproject import (
	fixTomlIndentation,
	formatAuthorList,
	mergeDependencyLists,
	mergePyprojectToml,
)

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"


def load_tests(
	loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None
) -> unittest.TestSuite:
	"""Protocol function to override default unittest test loading order.

	Enforces test execution in source code definition order using class dict insertion order.
	"""
	orderIndex: dict[str, int] = {
		name: i for i, name in enumerate(TestSyncAddonTool.__dict__)
	}
	loader.sortTestMethodsUsing = (
		lambda a, b: orderIndex.get(a, 999) - orderIndex.get(b, 999)
	)
	return loader.loadTestsFromTestCase(TestSyncAddonTool)


class TestSyncAddonTool(unittest.TestCase):
	"""Test cases for checking synchronization logic and file merges."""

	def testMergeLegacyBuildvarsWithOfficialTemplate(self) -> None:
		"""Ensure legacy buildVars.py is correctly merged into the latest official template structure."""
		with tempfile.TemporaryDirectory() as tempDir:
			projBvPath: Path = Path(tempDir) / "buildVars.py"
			tplBvPath: Path = Path(tempDir) / "template_buildVars.py"

			# 1. Legacy buildVars fixture
			legacyFixture: Path = FIXTURES_DIR / "legacyBuildVars.py"
			projBvPath.write_text(legacyFixture.read_text(encoding="utf-8"), encoding="utf-8")

			# 2. Official template buildVars fixture
			templateFixture: Path = FIXTURES_DIR / "templateBuildVars.py"
			tplBvPath.write_text(templateFixture.read_text(encoding="utf-8"), encoding="utf-8")

			metadata: dict
			globalVars: dict
			metadata, globalVars = extractBuildvarsMetadata(projBvPath)
			status: str = mergeBuildvarsFile(
				projBvPath, tplBvPath, metadata, globalVars, dryRun=False
			)

			self.assertEqual(status, "merged & structured (AST verified)")

			content: str = projBvPath.read_text(encoding="utf-8")
			# Verify metadata mapping from fixture
			self.assertIn("addon_name='myAddon'", content)
			self.assertIn("addon_version='1.0.0'", content)
			# Verify new official template imports
			self.assertIn("from site_scons.site_tools.NVDATool.typings import", content)

	def testMergeModernBuildvarsMissingSpeechDictionaries(self) -> None:
		"""Ensure modern buildVars.py gets missing speechDictionaries imported/injected from official template."""
		with tempfile.TemporaryDirectory() as tempDir:
			projBvPath: Path = Path(tempDir) / "buildVars.py"
			tplBvPath: Path = Path(tempDir) / "template_buildVars.py"

			# 1. Modern buildVars fixture (without SpeechDictionaries imported in original)
			modernFixture: Path = FIXTURES_DIR / "modernBuildVars.py"
			projBvPath.write_text(modernFixture.read_text(encoding="utf-8"), encoding="utf-8")

			# 2. Official template buildVars fixture
			templateFixture: Path = FIXTURES_DIR / "templateBuildVars.py"
			tplBvPath.write_text(templateFixture.read_text(encoding="utf-8"), encoding="utf-8")

			metadata: dict
			globalVars: dict
			metadata, globalVars = extractBuildvarsMetadata(projBvPath)
			status: str = mergeBuildvarsFile(
				projBvPath, tplBvPath, metadata, globalVars, dryRun=False
			)

			self.assertEqual(status, "merged & structured (AST verified)")

			content: str = projBvPath.read_text(encoding="utf-8")
			self.assertIn("addon_name='myAddon'", content)
			self.assertIn("SpeechDictionaries", content)

	def testSetupAddonMergeIgnore(self) -> None:
		"""Verify bootstrapping of .addonmergeignore from template to add-on directory.

		Tests creation when missing, preservation when existing, and behavior in dry-run mode.
		"""
		tempDirObj: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
		self.addCleanup(tempDirObj.cleanup)
		tempPath: Path = Path(tempDirObj.name)

		addonDir: Path = tempPath / "myAddon"
		templateDir: Path = tempPath / "template"
		addonDir.mkdir(parents=True, exist_ok=True)
		templateDir.mkdir(parents=True, exist_ok=True)

		# Create template .addonmergeignore
		templateIgnore: Path = templateDir / ".addonmergeignore"
		templateIgnore.write_text("*.tmp\nbuild/\n", encoding="utf-8")

		addonIgnore: Path = addonDir / ".addonmergeignore"

		# Case 1: Dry run should NOT copy the file
		setupAddonMergeIgnore(tempDir=templateDir, addonDir=addonDir, dryRun=True)
		self.assertFalse(addonIgnore.exists())

		# Case 2: Standard execution should copy (bootstrap) the missing file
		setupAddonMergeIgnore(tempDir=templateDir, addonDir=addonDir, dryRun=False)
		self.assertTrue(addonIgnore.exists())
		self.assertEqual(addonIgnore.read_text(encoding="utf-8"), "*.tmp\nbuild/\n")

		# Case 3: Existing file should NOT be overwritten by template
		addonIgnore.write_text("customRule/\n", encoding="utf-8")
		setupAddonMergeIgnore(tempDir=templateDir, addonDir=addonDir, dryRun=False)
		self.assertEqual(addonIgnore.read_text(encoding="utf-8"), "customRule/\n")

	def testAddonMergeIgnore(self) -> None:
		"""Verify that files specified in .addonmergeignore are excluded during synchronization.

		Ensures that existing files listed in the ignore file retain their original content
		and are not overwritten by template files.
		"""
		tempDirObj: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
		self.addCleanup(tempDirObj.cleanup)
		tempPath: Path = Path(tempDirObj.name)

		# 1. Setup project directories
		addonDir: Path = tempPath / "myAddon"
		templateDir: Path = tempPath / "template"
		addonDir.mkdir(parents=True, exist_ok=True)
		templateDir.mkdir(parents=True, exist_ok=True)

		# 2. Populate template and addon files
		normalFileTemplate: Path = templateDir / "normalFile.txt"
		normalFileTemplate.write_text("Template content", encoding="utf-8")

		ignoredFileTemplate: Path = templateDir / "ignoredFile.txt"
		ignoredFileTemplate.write_text("Template ignored content", encoding="utf-8")

		ignoredFileAddon: Path = addonDir / "ignoredFile.txt"
		ignoredFileAddon.write_text("Original addon content", encoding="utf-8")

		# 3. Create .addonmergeignore file in the addon directory
		ignoreFile: Path = addonDir / ".addonmergeignore"
		ignoreFile.write_text("ignoredFile.txt\n", encoding="utf-8")

		# 4. Execute synchronization with correct arguments
		runSynchronization(
			tempDir=templateDir,
			addonDir=addonDir,
			dryRun=False,
		)

		# 5. Assertions
		normalFileAddon: Path = addonDir / "normalFile.txt"
		self.assertTrue(normalFileAddon.exists())
		self.assertEqual(normalFileAddon.read_text(encoding="utf-8"), "Template content")

		# The ignored file must preserve its original content
		self.assertEqual(
			ignoredFileAddon.read_text(encoding="utf-8"),
			"Original addon content",
		)

	def testMergeBuildvarsAutoImportsOs(self) -> None:
		"""Ensure 'import os' is automatically added if merged buildVars uses the os module."""
		with tempfile.TemporaryDirectory() as tempDir:
			projBvPath: Path = Path(tempDir) / "buildVars.py"
			tplBvPath: Path = Path(tempDir) / "template_buildVars.py"

			# Legacy buildVars using os module without import in template
			projBvPath.write_text(
				'import os\n'
				'pythonSources = [os.path.join("addon", "*.py")]\n',
				encoding="utf-8",
			)

			tplBvPath.write_text(
				'pythonSources: list[str] = []\n',
				encoding="utf-8",
			)

			metadata: dict
			globalVars: dict
			metadata, globalVars = extractBuildvarsMetadata(projBvPath)
			mergeBuildvarsFile(projBvPath, tplBvPath, metadata, globalVars, dryRun=False)

			content: str = projBvPath.read_text(encoding="utf-8")
			self.assertTrue(content.startswith("import os\n"))

	def testFixTomlIndentation(self) -> None:
		"""Ensure 4-space indentations are converted to tabs across TOML blocks."""
		inputToml: str = (
			'name = "myAddon"\n'
			"maintainers = [\n"
			'    {name = "John Doe", email = "john@example.com"},\n'
			"]\n"
			"otherSection = {\n"
			'    key = "value"\n'
			"}\n"
		)
		expectedOutput: str = (
			'name = "myAddon"\n'
			"maintainers = [\n"
			'\t{name = "John Doe", email = "john@example.com"},\n'
			"]\n"
			"otherSection = {\n"
			'\tkey = "value"\n'
			"}\n"
		)

		result: str = fixTomlIndentation(inputToml)
		self.assertEqual(result, expectedOutput)

	def testFormatAuthorList(self) -> None:
		"""Ensure raw author string parsing produces a formatted tomlkit array."""
		rawAuthors: str = "John Doe <john@example.com>, Jane Smith"
		authorsArray: list = formatAuthorList(rawAuthors)

		self.assertEqual(len(authorsArray), 2)
		self.assertEqual(authorsArray[0]["name"], "John Doe")
		self.assertEqual(authorsArray[0]["email"], "john@example.com")
		self.assertEqual(authorsArray[1]["name"], "Jane Smith")
		# Verify that the email key is omitted when empty (PEP 621 / uv compliance)
		self.assertNotIn("email", authorsArray[1])

	def testMergeDependencyLists(self) -> None:
		"""Ensure dependency lists merge updates existing package versions while preserving custom ones."""
		projDeps: list[str] = ["pyright>=1.1.0", "requests>=2.28.0", "ruff==0.1.0"]
		tplDeps: list[str] = ["pyright>=1.2.0", "ruff==0.2.0", "pytest"]

		merged: list[str] = mergeDependencyLists(projDeps, tplDeps)

		# Check that versions from template override project versions
		self.assertIn("pyright>=1.2.0", merged)
		self.assertNotIn("pyright>=1.1.0", merged)
		self.assertIn("ruff==0.2.0", merged)

		# Check that custom dependency is preserved
		self.assertIn("requests>=2.28.0", merged)

		# Check that new template dependency is added
		self.assertIn("pytest", merged)

	def testMergePyprojectTomlIntelligent(self) -> None:
		"""Ensure pyproject.toml is intelligently merged without duplicating dependencies."""
		with tempfile.TemporaryDirectory() as tempDir:
			projToml: Path = Path(tempDir) / "pyproject.toml"
			tplToml: Path = Path(tempDir) / "template_pyproject.toml"

			projToml.write_text(
				'[project]\n'
				'name = "myAddon"\n'
				'dependencies = ["requests>=2.0.0", "pyright>=1.0.0"]\n',
				encoding="utf-8",
			)

			tplToml.write_text(
				'[project]\n'
				'name = "addonTemplate"\n'
				'dependencies = ["pyright>=2.0.0", "ruff"]\n'
				'[dependency-groups]\n'
				'dev = ["pytest"]\n',
				encoding="utf-8",
			)

			status: str = mergePyprojectToml(
				projToml, tplToml, metadataDict={}, dryRun=False
			)
			self.assertEqual(status, "merged intelligently (tomlkit)")

			content: str = projToml.read_text(encoding="utf-8")
			self.assertIn('name = "myAddon"', content)
			self.assertIn('requests>=2.0.0', content)

	def testMergePyprojectTomlPreservesHigherUserVersions(self) -> None:
		"""Ensure user dependencies with higher versions than template are preserved during merge."""
		with tempfile.TemporaryDirectory() as tempDir:
			projToml: Path = Path(tempDir) / "pyproject.toml"
			tplToml: Path = Path(tempDir) / "template_pyproject.toml"

			userFixture: Path = FIXTURES_DIR / "userPyproject.toml"
			projToml.write_text(userFixture.read_text(encoding="utf-8"), encoding="utf-8")

			templateFixture: Path = FIXTURES_DIR / "templatePyproject.toml"
			tplToml.write_text(templateFixture.read_text(encoding="utf-8"), encoding="utf-8")

			status: str = mergePyprojectToml(
				projToml, tplToml, metadataDict={}, dryRun=False
			)
			self.assertEqual(status, "merged intelligently (tomlkit)")

			content: str = projToml.read_text(encoding="utf-8")

			# Verify that higher user version 1.1.411 is retained over template version 1.1.407
			self.assertIn(
				"1.1.411",
				content,
				"Higher user version 1.1.411 was not preserved in pyproject.toml",
			)
			self.assertNotIn(
				"1.1.407",
				content,
				"Lower template version 1.1.407 should have been overridden",
			)

	def testMergePyprojectTomlPreservesHigherTemplateVersions(self) -> None:
		"""Ensure template dependencies with higher versions than user are adopted during merge."""
		with tempfile.TemporaryDirectory() as tempDir:
			projToml: Path = Path(tempDir) / "pyproject.toml"
			tplToml: Path = Path(tempDir) / "template_pyproject.toml"

			userFixture: Path = FIXTURES_DIR / "userPyproject.toml"
			projToml.write_text(userFixture.read_text(encoding="utf-8"), encoding="utf-8")

			templateFixture: Path = FIXTURES_DIR / "templatePyproject.toml"
			tplToml.write_text(templateFixture.read_text(encoding="utf-8"), encoding="utf-8")

			status: str = mergePyprojectToml(
				projToml, tplToml, metadataDict={}, dryRun=False
			)
			self.assertEqual(status, "merged intelligently (tomlkit)")

			content: str = projToml.read_text(encoding="utf-8")

			# Verify that higher template version 0.2.0 (ruff) overrides lower user version 0.1.0
			self.assertIn(
				"0.2.0",
				content,
				"Higher template version 0.2.0 was not adopted in pyproject.toml",
			)
			self.assertNotIn(
				"0.1.0",
				content,
				"Lower user version 0.1.0 should have been overridden",
			)


if __name__ == "__main__":
	unittest.main()
