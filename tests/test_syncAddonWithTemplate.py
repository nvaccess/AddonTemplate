# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

import ast
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from unittest.mock import patch

import tomlkit

# Import the functions to test from the main module
from syncAddonWithTemplate import (
	cleanupPlaceholderAuthors,
	deepMergeDicts,
	extractBuildvarsMetadata,
	formatAuthorList,
	getBasePackageName,
	mergeBuildvarsFile,
	mergePyprojectToml,
	parseAstDict,
	parseAstKeywords,
	replaceAstRange,
)


class TestSyncAddonWithTemplate(unittest.TestCase):
	"""Unit tests for checking the robust synchronization and merging helper functions."""

	def test_parseAstDict(self) -> None:
		"""Test parsing of an AST Dict node containing literal values and translatable strings.

		:return: None
		"""
		codeExpression = "{'name': 'My Addon', 'summary': _('A great helper')}"
		tree = ast.parse(codeExpression)
		dictNode = tree.body[0].value
		self.assertTrue(isinstance(dictNode, ast.Dict))

		result = parseAstDict(dictNode)
		expected = {"name": "My Addon", "summary": "A great helper"}
		self.assertEqual(result, expected)

	def test_parseAstKeywords(self) -> None:
		"""Test parsing of AST keyword arguments from a call expression (e.g. AddonInfo).

		:return: None
		"""
		codeExpression = "AddonInfo(addon_name='Test', addon_summary=_('Test Summary'))"
		tree = ast.parse(codeExpression)
		callNode = tree.body[0].value
		self.assertTrue(isinstance(callNode, ast.Call))

		result = parseAstKeywords(callNode.keywords)
		expected = {"addon_name": "Test", "addon_summary": "Test Summary"}
		self.assertEqual(result, expected)

	def test_formatAuthorList(self) -> None:
		"""Test formatting of comma-separated author strings into a list of inline tables.

		:return: None
		"""
		rawAuthors = "John Doe <john@example.com>, Jane Smith, Bob <bob@dev.org>"
		result = formatAuthorList(rawAuthors)

		self.assertEqual(len(result), 3)
		self.assertEqual(result[0]["name"], "John Doe")
		self.assertEqual(result[0]["email"], "john@example.com")
		self.assertEqual(result[1]["name"], "Jane Smith")
		self.assertEqual(result[1]["email"], "")
		self.assertEqual(result[2]["name"], "Bob")
		self.assertEqual(result[2]["email"], "bob@dev.org")

	def test_cleanupPlaceholderAuthors(self) -> None:
		"""Test removal of NV Access placeholder author entries from project tables.

		:return: None
		"""
		projectSection = {
			"authors": [
				{"name": "Developer One", "email": "dev1@example.com"},
				{"name": "NV Access", "email": "info@nvaccess.org"},
			],
			"maintainers": [
				{"name": "nvaccess", "email": "info@nvaccess.org"},
				{"name": "Developer Two", "email": "dev2@example.com"},
			],
		}

		cleanupPlaceholderAuthors(projectSection)

		self.assertEqual(len(projectSection["authors"]), 1)
		self.assertEqual(projectSection["authors"][0]["name"], "Developer One")
		self.assertEqual(len(projectSection["maintainers"]), 1)
		self.assertEqual(projectSection["maintainers"][0]["name"], "Developer Two")

	def test_getBasePackageName(self) -> None:
		"""Test extracting a dependency base name with operators, markers, and versions.

		:return: None
		"""
		self.assertEqual(getBasePackageName("requests>=2.28.0"), "requests")
		self.assertEqual(getBasePackageName("tomlkit==0.11.6; python_version >= '3.11'"), "tomlkit")
		self.assertEqual(getBasePackageName("  BeautifulSoup4<=4.12.0 "), "beautifulsoup4")

	def test_replaceAstRange(self) -> None:
		"""Test replacing target lines in a source text list using a mapping of line indexes.

		:return: None
		"""
		tplLines = [
			"line 1\n",
			"line 2 to replace\n",
			"line 3 to replace\n",
			"line 4\n",
		]
		replacements = {(1, 3): "replaced line\n"}

		replaceAstRange(tplLines, replacements)

		expected = [
			"line 1\n",
			"replaced line\n",
			"line 4\n",
		]
		self.assertEqual(tplLines, expected)

	def test_deepMergeDicts(self) -> None:
		"""Test recursive merging of template settings into an existing dictionary.

		:return: None
		"""
		dictProj = {
			"tool": {
				"ruff": {
					"line-length": 120,
					"select": ["E", "F"],
				}
			},
			"project": {
				"dependencies": ["requests"],
			},
		}

		dictTpl = {
			"tool": {
				"ruff": {
					"select": ["E", "F", "W"],
				},
				"pyright": {
					"typeCheckingMode": "basic",
				},
			},
			"project": {
				"dependencies": ["tomlkit"],
			},
		}

		result = deepMergeDicts(dictProj, dictTpl)

		# Ensure nested dictionaries were merged, prioritizing existing or accumulating list entries
		self.assertEqual(result["tool"]["ruff"]["line-length"], 120)
		self.assertEqual(result["tool"]["ruff"]["select"], ["E", "F", "W"])
		self.assertEqual(result["tool"]["pyright"]["typeCheckingMode"], "basic")
		self.assertEqual(result["project"]["dependencies"], ["requests", "tomlkit"])

	def test_extractBuildvarsMetadata(self) -> None:
		"""Test extracting legacy buildVars.py metadata with dictionary and global variables.

		:return: None
		"""
		buildvarsContent = """
addon_info = {
	"addon_name": "MyAddon",
	"addon_summary": _("This is my addon"),
	"addon_url": "https://github.com/user/addon",
	"addon_author": "John Doe <john@example.com>"
}

pythonSources = ["addon", "globalPlugins"]
excludedFiles = ["test.py"]
"""
		with TemporaryDirectory() as tempDir:
			filePath = Path(tempDir) / "buildVars.py"
			with filePath.open("w", encoding="utf-8") as f:
				f.write(buildvarsContent)

			metadata, globalVars = extractBuildvarsMetadata(filePath)

			self.assertEqual(metadata["addon_name"], "MyAddon")
			self.assertEqual(metadata["addon_summary"], "This is my addon")
			self.assertEqual(metadata["addon_url"], "https://github.com/user/addon")
			self.assertEqual(metadata["addon_author"], "John Doe <john@example.com>")

			self.assertEqual(globalVars["pythonSources"], "['addon', 'globalPlugins']")
			self.assertEqual(globalVars["excludedFiles"], "['test.py']")

	def test_mergePyprojectToml_creation(self) -> None:
		"""Test creating a pyproject.toml when it does not exist, utilizing metadata.

		:return: None
		"""
		metadata = {
			"addon_name": "DynamicAddon",
			"addon_summary": "Summary of addon",
			"addon_url": "https://github.com/org/repo",
			"addon_author": "Author One <one@example.com>",
		}

		with TemporaryDirectory() as tempDir:
			projPath = Path(tempDir) / "pyproject.toml"
			tplPath = Path(tempDir) / "template_pyproject.toml"

			# Populate template with empty tool definitions
			tplContent = "[project]\n[project.urls]\n"
			with tplPath.open("w", encoding="utf-8") as f:
				f.write(tplContent)

			status = mergePyprojectToml(projPath, tplPath, metadata, dryRun=False)
			self.assertEqual(status, "created from template")

			with projPath.open("r", encoding="utf-8") as f:
				createdData = tomlkit.parse(f.read())

			self.assertEqual(createdData["project"]["name"], "DynamicAddon")
			self.assertEqual(createdData["project"]["description"], "Summary of addon")
			self.assertEqual(createdData["project"]["urls"]["Repository"], "https://github.com/org/repo")
			self.assertEqual(createdData["project"]["maintainers"][0]["name"], "Author One")

	def test_mergePyprojectToml_intelligent_merge(self) -> None:
		"""Test merging pyproject.toml with preserve rules and dependency updates.

		:return: None
		"""
		with TemporaryDirectory() as tempDir:
			projPath = Path(tempDir) / "pyproject.toml"
			tplPath = Path(tempDir) / "template_pyproject.toml"

			projContent = """
[project]
name = "MyAddon"
dependencies = ["requests"]

[tool.ruff]
line-length = 120
"""
			tplContent = """
[project]
name = "TemplateAddon"
dependencies = ["tomlkit"]

[tool.ruff]
select = ["E"]
"""
			with projPath.open("w", encoding="utf-8") as f:
				f.write(projContent)
			with tplPath.open("w", encoding="utf-8") as f:
				f.write(tplContent)

			status = mergePyprojectToml(projPath, tplPath, {}, dryRun=False)
			self.assertEqual(status, "merged intelligently (tomlkit)")

			with projPath.open("r", encoding="utf-8") as f:
				mergedData = tomlkit.parse(f.read())

			self.assertEqual(mergedData["project"]["name"], "MyAddon")
			self.assertEqual(list(mergedData["project"]["dependencies"]), ["tomlkit", "requests"])
			self.assertEqual(mergedData["tool"]["ruff"]["line-length"], 120)
			self.assertEqual(mergedData["tool"]["ruff"]["select"], ["E"])

	def test_mergeBuildvarsFile(self) -> None:
		"""Test merging buildVars.py using AST replacements to write key values safely.

		:return: None
		"""
		metadata = {
			"addon_name": "CoolAddon",
			"addon_summary": "A very cool addon indeed",
		}
		globalVars = {
			"pythonSources": "['addon', 'modules']",
		}

		with TemporaryDirectory() as tempDir:
			projPath = Path(tempDir) / "buildVars.py"
			tplPath = Path(tempDir) / "template_buildVars.py"

			tplContent = """
addon_info = AddonInfo(
	addon_name="TemplateName",
	addon_summary=_("TemplateSummary"),
)

pythonSources: list[str] = ["addon"]
"""
			with tplPath.open("w", encoding="utf-8") as f:
				f.write(tplContent)

			status = mergeBuildvarsFile(projPath, tplPath, metadata, globalVars, dryRun=False)
			self.assertEqual(status, "merged & structured (AST verified)")

			with projPath.open("r", encoding="utf-8") as f:
				resultContent = f.read()

			self.assertIn('addon_name="CoolAddon"', resultContent)
			self.assertIn('addon_summary=_(\'A very cool addon indeed\')', resultContent)
			self.assertIn("pythonSources: list[str] = ['addon', 'modules']", resultContent)


if __name__ == "__main__":
	unittest.main()
    