# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Command-line interface and main entry point orchestration."""

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .buildVarsSync import extractBuildvarsMetadata
from .engine import runSynchronization

logger: logging.Logger = logging.getLogger("syncAddon")


def buildArgParser() -> argparse.ArgumentParser:
	"""Build and configure the command-line argument parser.

	:return: Configured ArgumentParser object.
	"""
	parser: argparse.ArgumentParser = argparse.ArgumentParser(
		description="Non-destructive industrial update tool for NVDA Add-ons.",
	)
	parser.add_argument(
		"-ad",
		"--addon-dir",
		dest="addonDir",
		default=None,
		help="Path to the root directory of the add-on to update (defaults to current directory).",
	)
	parser.add_argument(
		"-td",
		"--template-dir",
		dest="templateDir",
		default=None,
		help="Path to a local directory containing the NVDA AddonTemplate to use instead of fetching it via Git.",
	)
	parser.add_argument(
		"-dr",
		"--dry-run",
		dest="dryRun",
		action="store_true",
		help="Simulate execution without modifying any files.",
	)
	parser.add_argument(
		"-s",
		"--skip-backup",
		dest="skipBackup",
		action="store_true",
		help="Disable safety automatic project backup.",
	)
	parser.add_argument(
		"-v",
		"--verbose",
		dest="verbose",
		action="store_true",
		help="Enable verbose debug logs.",
	)
	return parser


def main() -> None:
	"""Execute main CLI entry point for the NVDA Add-on update tool.

	:return: None
	"""
	parserObj: argparse.ArgumentParser = buildArgParser()
	parsedArgs: argparse.Namespace = parserObj.parse_args()

	loggingLevel: int = logging.DEBUG if parsedArgs.verbose else logging.INFO
	logging.basicConfig(level=loggingLevel, format="[%(levelname)s] %(message)s")

	addonDirInputText: str | None = parsedArgs.addonDir
	addonDir: str
	if addonDirInputText:
		addonDir = os.path.abspath(addonDirInputText)
	else:
		cwdPath: Path = Path(os.getcwd()).resolve()
		addonRootPath: Path | None = next(
			(p for p in (cwdPath, *cwdPath.parents) if (p / "buildVars.py").exists()),
			None,
		)
		addonDir = str(addonRootPath) if addonRootPath is not None else str(cwdPath)

	logger.info("=== NVDA ADD-ON UPDATE TOOL ===")
	logger.info("Target Directory: %s", addonDir)

	oldBuildvarsPath: str = os.path.join(addonDir, "buildVars.py")

	if not os.path.exists(oldBuildvarsPath):
		logger.error("'%s' does not appear to be a valid NVDA Add-on (missing buildVars.py).", addonDir)
		if sys.stdin.isatty():
			input("\nPress Enter to exit...")
		sys.exit(1)

	logger.info("Phase 1: Analyzing existing project structure and metadata...")
	buildvarsMetadataDict: dict[str, Any]
	buildvarsMetadataDict, _ = extractBuildvarsMetadata(oldBuildvarsPath)
	addonNameVal: Any = buildvarsMetadataDict.get("addon_name", os.path.basename(addonDir))
	logger.info("Target Add-on Identified: %s", addonNameVal)

	if parsedArgs.dryRun:
		logger.info("RUNNING IN SIMULATION MODE (--dry-run). No files will be modified.")

	logger.info("Phase 2: Safety backup verification...")
	if parsedArgs.dryRun:
		logger.debug("Safety backup skipped (simulation mode active).")
	elif parsedArgs.skipBackup:
		logger.info("Safety backup skipped (--skip-backup requested by user).")
	else:
		backupDirPath: str = f"{addonDir}_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
		logger.info("Creating safety automatic backup in: %s...", os.path.basename(backupDirPath))
		try:
			shutil.copytree(
				addonDir,
				backupDirPath,
				ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "*_bak_*"),
			)
			logger.info("Backup created successfully.")
		except Exception as exceptionObj:
			logger.error("Critical: Backup failed (%s). Aborting update.", exceptionObj)
			if sys.stdin.isatty():
				input("\nPress Enter to exit...")
			sys.exit(1)

	if parsedArgs.templateDir:
		templatePath: str = os.path.abspath(parsedArgs.templateDir)
		logger.info("Phase 3: Using local template directory: %s", templatePath)
		if not os.path.exists(os.path.join(templatePath, "buildVars.py")):
			logger.error(
				"Provided template directory does not appear to be a valid NVDA AddonTemplate (missing buildVars.py)."
			)
			if sys.stdin.isatty():
				input("\nPress Enter to exit...")
			sys.exit(1)
		runSynchronization(templatePath, addonDir, parsedArgs.dryRun)
	else:
		logger.info("Phase 3: Provisioning latest official NVDA AddonTemplate via Git...")
		with tempfile.TemporaryDirectory() as tempDir:
			logger.debug("Cloning template into temporary workspace...")
			templateUrlText: str = "https://github.com/nvaccess/AddonTemplate.git"

			try:
				subprocess.run(
					["git", "clone", "--depth", "1", templateUrlText, tempDir],
					check=True,
					stdout=subprocess.DEVNULL,
					stderr=subprocess.PIPE,
				)
				logger.info("Template cloned successfully.")
			except (subprocess.CalledProcessError, FileNotFoundError) as exceptionObj:
				logger.error("Failed to execute git clone. Make sure Git is available in your PATH.")
				if isinstance(exceptionObj, subprocess.CalledProcessError) and exceptionObj.stderr:
					logger.error("Details: %s", exceptionObj.stderr.decode("utf-8", errors="ignore"))
				if sys.stdin.isatty():
					input("\nPress Enter to exit...")
				sys.exit(1)

			runSynchronization(tempDir, addonDir, parsedArgs.dryRun)

	if not parsedArgs.dryRun:
		logger.info("Project successfully updated. Workspace cleared.")
	else:
		logger.info("Simulation finished. Workspace cleared.")
