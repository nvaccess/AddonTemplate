# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""File tree traversal, file copying, ignore handling, and synchronization orchestration."""

import ast
import logging
import os
from pathlib import Path
import shutil
from typing import Any

from .buildVarsSync import extractBuildvarsMetadata, mergeBuildvarsFile
from .pyproject import mergePyprojectToml

logger: logging.Logger = logging.getLogger("syncAddon")


def setupAddonMergeIgnore(tempDir: str | Path, addonDir: str | Path, dryRun: bool = False) -> None:
	"""Ensure .addonmergeignore exists in the target add-on directory.

	If missing, copies it from the template to bootstrap default ignore rules.
	Does nothing if the file is already present.

	:param tempDir: Path to the template directory.
	:param addonDir: Path to the target add-on directory.
	:param dryRun: If True, simulate execution without modifying files.
	:return: None
	"""
	ignoreFilePath: Path = Path(addonDir) / ".addonmergeignore"
	templateIgnorePath: Path = Path(tempDir) / ".addonmergeignore"

	if not ignoreFilePath.exists() and templateIgnorePath.exists():
		if not dryRun:
			shutil.copy2(templateIgnorePath, ignoreFilePath)
		logger.info("Bootstrapped missing .addonmergeignore from template.")


def runSynchronization(tempDir: str, addonDir: str, dryRun: bool) -> None:
	"""Synchronize template machinery files from the temporary workspace into the target directory.

	:param tempDir: Path to the local temporary directory containing the template files.
	:param addonDir: Path to the target add-on root directory.
	:param dryRun: If True, simulate the sync without writing changes to disk.
	:return: None
	"""
	logger.info("Phase 4: Synchronizing template machinery files...")
	setupAddonMergeIgnore(tempDir, addonDir, dryRun)

	protectedElementsSet: set[str] = {
		"readme.md",
		"changelog.md",
		"addontemplate.egg-info",
		".github/workflows/unittests.yml",
		"addon",
		".git",
		"__pycache__",
		".venv",
		"docs",
		".ruff_cache",
		"tests",
	}

	ignoreFilePath: str = os.path.join(addonDir, ".addonmergeignore")
	if os.path.exists(ignoreFilePath):
		logger.debug("Reading local custom exclusions from .addonmergeignore...")
		try:
			with open(ignoreFilePath, "r", encoding="utf-8") as f:
				lineItem: str
				for lineItem in f:
					cleanLineText: str = lineItem.strip().replace("\\", "/").lower()
					if cleanLineText and not cleanLineText.startswith("#"):
						protectedElementsSet.add(cleanLineText)
		except Exception as exceptionObj:
			logger.warning("Failed to parse .addonmergeignore (%s)", exceptionObj)

	syncReportList: list[str] = []

	def addReportEntry(reportEntryText: str) -> None:
		"""Add an entry to syncReportList ensuring no duplicates exist.

		:param reportEntryText: The status report line to record.
		:return: None
		"""
		if reportEntryText not in syncReportList:
			syncReportList.append(reportEntryText)

	def inspectAndCopyDirectory(srcDirPath: str, dstDirPath: str) -> None:
		"""Inspect directory recursively for protected elements and copy non-protected files.

		:param srcDirPath: Path to the source directory to inspect.
		:param dstDirPath: Path to the destination target directory.
		:return: None
		"""
		walkRoot: str
		walkDirs: list[str]
		walkFiles: list[str]
		for walkRoot, walkDirs, walkFiles in os.walk(srcDirPath):
			relDirPath: str = os.path.relpath(walkRoot, tempDir)

			dirsToCopyList: list[str] = []
			dirNameItem: str
			for dirNameItem in walkDirs:
				relPathText: str = dirNameItem if relDirPath == "." else os.path.join(relDirPath, dirNameItem)
				relPathNormalizedText: str = relPathText.replace("\\", "/").lower()
				if relPathNormalizedText in protectedElementsSet:
					displayPathText: str = relPathText.replace("\\", "/")
					addReportEntry(f"- **{displayPathText}/**: skipped (protected scope)")
				else:
					dirsToCopyList.append(dirNameItem)
			walkDirs[:] = dirsToCopyList

			relDstPath: str = os.path.relpath(walkRoot, srcDirPath)
			targetRootPath: str = os.path.join(dstDirPath, relDstPath)

			fileNameItem: str
			for fileNameItem in walkFiles:
				relPathText = fileNameItem if relDirPath == "." else os.path.join(relDirPath, fileNameItem)
				relPathNormalizedText = relPathText.replace("\\", "/").lower()
				if relPathNormalizedText in protectedElementsSet:
					displayPathText = relPathText.replace("\\", "/")
					addReportEntry(f"- **{displayPathText}**: skipped (protected scope)")
				else:
					if not dryRun:
						srcFilePath: str = os.path.join(walkRoot, fileNameItem)
						dstFilePath: str = os.path.join(targetRootPath, fileNameItem)
						os.makedirs(os.path.dirname(dstFilePath), exist_ok=True)
						shutil.copy2(srcFilePath, dstFilePath)

	rootItemName: str
	for rootItemName in os.listdir(tempDir):
		itemNormalizedText: str = rootItemName.lower()
		if itemNormalizedText in protectedElementsSet:
			addReportEntry(f"- **{rootItemName}**: skipped (protected scope)")
			continue

		if rootItemName in ["buildVars.py", "pyproject.toml"]:
			continue

		srcItemPath: str = os.path.join(tempDir, rootItemName)
		dstItemPath: str = os.path.join(addonDir, rootItemName)

		try:
			if os.path.isdir(srcItemPath):
				inspectAndCopyDirectory(srcItemPath, dstItemPath)
				addReportEntry(f"- **{rootItemName}/**: merged safely")
			else:
				if not dryRun:
					shutil.copy2(srcItemPath, dstItemPath)
				addReportEntry(f"- **{rootItemName}**: synchronized")
		except Exception as exceptionObj:
			addReportEntry(f"- **{rootItemName}**: failed ({str(exceptionObj)})")

	logger.info("Processing structural configuration merges...")
	templateBuildvarsPath: str = os.path.join(tempDir, "buildVars.py")
	templatePyprojectPath: str = os.path.join(tempDir, "pyproject.toml")

	oldBuildvarsPath: str = os.path.join(addonDir, "buildVars.py")
	oldPyprojectPath: str = os.path.join(addonDir, "pyproject.toml")

	buildvarsMetadataDict: dict[str, Any]
	buildvarsGlobalsDict: dict[str, tuple[ast.AST, str]]
	buildvarsMetadataDict, buildvarsGlobalsDict = extractBuildvarsMetadata(oldBuildvarsPath)
	addonNameVal: Any = buildvarsMetadataDict.get("addon_name", os.path.basename(addonDir))

	buildvarsStatusText: str = mergeBuildvarsFile(
		oldBuildvarsPath,
		templateBuildvarsPath,
		buildvarsMetadataDict,
		buildvarsGlobalsDict,
		dryRun,
	)
	pyprojectStatusText: str = mergePyprojectToml(
		oldPyprojectPath,
		templatePyprojectPath,
		buildvarsMetadataDict,
		dryRun,
	)

	logger.info("=" * 50)
	logger.info("UPDATE REPORT")
	logger.info("=" * 50)
	logger.info("Add-on: %s", addonNameVal)
	logger.info("\nTemplate synchronization:")
	reportEntryItem: str
	for reportEntryItem in sorted(syncReportList):
		logger.info("  %s", reportEntryItem)
	logger.info(
		"\nConfiguration files:\n  - **buildVars.py**: %s\n  - **pyproject.toml**: %s",
		buildvarsStatusText,
		pyprojectStatusText,
	)
