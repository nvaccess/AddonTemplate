# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

import tempfile
import unittest
from pathlib import Path

# Import functions to test
from syncAddonWithTemplate import (
	extractBuildvarsMetadata,
	fixTomlIndentation,
	formatAuthorList,
	mergeBuildvarsFile,
	mergePyprojectToml,
)


class TestSyncAddonWithTemplate(unittest.TestCase):
	"""Unit test suite for syncAddonWithTemplate.py module."""

	def testFixTomlIndentation(self) -> None:
		"""Ensure that 4 spaces are replaced by a tab inside maintainers/authors blocks only."""
		inputToml = (
			'name = "myAddon"\n'
			"maintainers = [\n"
			'    {name = "John Doe", email = "john@example.com"},\n'
			"]\n"
			"otherSection = {\n"
			'    key = "value"\n'
			"}\n"
		)
		expectedOutput = (
			'name = "myAddon"\n'
			"maintainers = [\n"
			'\t{name = "John Doe", email = "john@example.com"},\n'
			"]\n"
			"otherSection = {\n"
			'    key = "value"\n'
			"}\n"
		)

		result = fixTomlIndentation(inputToml)
		self.assertEqual(result, expectedOutput)

	def testFormatAuthorList(self) -> None:
		"""Ensure raw author string parsing produces a formatted tomlkit array."""
		rawAuthors = "John Doe <john@example.com>, Jane Smith"
		authorsArray = formatAuthorList(rawAuthors)

		self.assertEqual(len(authorsArray), 2)
		self.assertEqual(authorsArray[0]["name"], "John Doe")
		self.assertEqual(authorsArray[0]["email"], "john@example.com")
		self.assertEqual(authorsArray[1]["name"], "Jane Smith")
		self.assertEqual(authorsArray[1]["email"], "")

	def testMergeLegacyBuildvarsWithOfficialTemplate(self) -> None:
		"""Ensure legacy buildVars.py is correctly merged into the latest official template structure."""
		with tempfile.TemporaryDirectory() as tempDir:
			projBvPath = Path(tempDir) / "buildVars.py"
			tplBvPath = Path(tempDir) / "template_buildVars.py"

			# 1. Legacy dictionary-based buildVars.py
			projBvPath.write_text(
				'addon_info = {\n'
				'    "addon_name": "dayOfTheWeek",\n'
				'    "addon_summary": _("Day of the week"),\n'
				'    "addon_version": "20251022.0.1",\n'
				'}\n'
				'import os\n'
				'pythonSources = [os.path.join("addon", "globalPlugins", "*.py")]\n'
				'i18nSources = pythonSources + ["buildVars.py"]\n'
				'excludedFiles = []\n'
				'baseLanguage = "en"\n'
				'markdownExtensions = []\n',
				encoding="utf-8",
			)

			# 2. Official template buildVars.py content
			tplBvPath.write_text(
				'from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries, SpeechDictionaries\n'
				'from site_scons.site_tools.NVDATool.utils import _\n\n'
				'addon_info = AddonInfo(\n'
				'    addon_name="addonTemplate",\n'
				'    addon_summary=_("Add-on user visible name"),\n'
				'    addon_description=_("""Description."""),\n'
				'    addon_version="x.y",\n'
				'    addon_changelog=_("""Changelog."""),\n'
				'    addon_author="name <name@domain.com>",\n'
				'    addon_url=None,\n'
				'    addon_sourceURL=None,\n'
				'    addon_docFileName="readme.html",\n'
				'    addon_minimumNVDAVersion=None,\n'
				'    addon_lastTestedNVDAVersion=None,\n'
				'    addon_updateChannel=None,\n'
				'    addon_license=None,\n'
				'    addon_licenseURL=None,\n'
				')\n\n'
				'pythonSources: list[str] = []\n'
				'i18nSources: list[str] = pythonSources + ["buildVars.py"]\n'
				'excludedFiles: list[str] = []\n'
				'baseLanguage: str = "en"\n'
				'markdownExtensions: list[str] = []\n'
				'brailleTables: BrailleTables = {}\n'
				'symbolDictionaries: SymbolDictionaries = {}\n'
				'speechDictionaries: SpeechDictionaries = {}\n',
				encoding="utf-8",
			)

			metadata, globalVars = extractBuildvarsMetadata(projBvPath)
			status = mergeBuildvarsFile(
				projBvPath, tplBvPath, metadata, globalVars, dryRun=False
			)

			self.assertEqual(status, "merged & structured (AST verified)")

			content = projBvPath.read_text(encoding="utf-8")
			# Verify legacy metadata mapping (handling single quote formatting)
			self.assertIn("addon_name='dayOfTheWeek'", content)
			self.assertIn("addon_version='20251022.0.1'", content)
			# Verify new official template imports and variables
			self.assertIn("from site_scons.site_tools.NVDATool.utils import _", content)
			self.assertIn("brailleTables: BrailleTables = {}", content)
			self.assertIn("symbolDictionaries: SymbolDictionaries = {}", content)
			self.assertIn("speechDictionaries: SpeechDictionaries = {}", content)

	def testMergeModernBuildvarsMissingSpeechDictionaries(self) -> None:
		"""Ensure modern buildVars.py gets missing speechDictionaries injected from official template."""
		with tempfile.TemporaryDirectory() as tempDir:
			projBvPath = Path(tempDir) / "buildVars.py"
			tplBvPath = Path(tempDir) / "template_buildVars.py"

			# 1. Modern buildVars.py without speechDictionaries
			projBvPath.write_text(
				'from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries\n'
				'from site_scons.site_tools.NVDATool.utils import _\n\n'
				'addon_info = AddonInfo(\n'
				'    addon_name="dayOfTheWeek",\n'
				'    addon_summary=_("Day of the week"),\n'
				'    addon_version="20260222.0.0",\n'
				')\n\n'
				'import os\n'
				'pythonSources: list[str] = [os.path.join("addon", "globalPlugins", "*.py")]\n'
				'i18nSources: list[str] = pythonSources + ["buildVars.py"]\n'
				'excludedFiles: list[str] = []\n'
				'baseLanguage: str = "en"\n'
				'markdownExtensions: list[str] = []\n'
				'brailleTables: BrailleTables = {}\n'
				'symbolDictionaries: SymbolDictionaries = {}\n',
				encoding="utf-8",
			)

			# 2. Official template buildVars.py
			tplBvPath.write_text(
				'from site_scons.site_tools.NVDATool.typings import AddonInfo, BrailleTables, SymbolDictionaries, SpeechDictionaries\n'
				'from site_scons.site_tools.NVDATool.utils import _\n\n'
				'addon_info = AddonInfo(\n'
				'    addon_name="addonTemplate",\n'
				'    addon_summary=_("Add-on user visible name"),\n'
				'    addon_version="x.y",\n'
				')\n\n'
				'pythonSources: list[str] = []\n'
				'i18nSources: list[str] = pythonSources + ["buildVars.py"]\n'
				'excludedFiles: list[str] = []\n'
				'baseLanguage: str = "en"\n'
				'markdownExtensions: list[str] = []\n'
				'brailleTables: BrailleTables = {}\n'
				'symbolDictionaries: SymbolDictionaries = {}\n'
				'speechDictionaries: SpeechDictionaries = {}\n',
				encoding="utf-8",
			)

			metadata, globalVars = extractBuildvarsMetadata(projBvPath)
			status = mergeBuildvarsFile(
				projBvPath, tplBvPath, metadata, globalVars, dryRun=False
			)

			self.assertEqual(status, "merged & structured (AST verified)")

			content = projBvPath.read_text(encoding="utf-8")
			self.assertIn("addon_name='dayOfTheWeek'", content)
			self.assertIn("speechDictionaries: SpeechDictionaries = {}", content)


if __name__ == "__main__":
	unittest.main()
