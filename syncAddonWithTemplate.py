# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

from collections.abc import MutableMapping, MutableSequence
import re
import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile

# Built-in in Python 3.11+, fully standardized for Python 3.13
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import tomlkit

TOMLKIT_AVAILABLE: bool = True


def parseAstDict(node: ast.Dict) -> dict[str, Any]:
	"""Extract key-value pairs from an AST Dict node.

	:param node: The ast.Dict node to parse.
	:return: A dictionary containing the extracted keys and values.
	"""
	extracted: dict[str, Any] = {}
	for keyNode, valNode in zip(node.keys, node.values):
		if keyNode is None:
			continue
		key = getattr(keyNode, "value", None)
		if isinstance(valNode, ast.Call) and getattr(valNode.func, "id", None) == "_":
			valNode = valNode.args[0]
		val = getattr(valNode, "value", None)
		if key is not None:
			extracted[key] = val
	return extracted


def parseAstKeywords(keywords: list[ast.keyword]) -> dict[str, Any]:
	"""Extract key-value pairs from a list of AST keyword nodes.

	:param keywords: The list of ast.keyword nodes to parse.
	:return: A dictionary containing the extracted keys and values.
	"""
	extracted: dict[str, Any] = {}
	for keyword in keywords:
		key = keyword.arg
		valNode = keyword.value
		if isinstance(valNode, ast.Call) and getattr(valNode.func, "id", None) == "_":
			valNode = valNode.args[0]
		val = getattr(valNode, "value", None)
		if key is not None:
			extracted[key] = val
	return extracted


def formatAuthorList(rawAuthors: str) -> tomlkit.items.Array:
	"""Convert a comma-separated string of authors into a tomlkit multiline array of inline tables.

	:param rawAuthors: The raw authors string (e.g., "Author Name <email@example.com>, Another").
	:return: A tomlkit.items.Array object containing inline tables.
	"""
	authorsList = tomlkit.array()
	authorsList.multiline(True)
	parts = [p.strip() for p in rawAuthors.split(",") if p.strip()]

	for part in parts:
		m = re.match(r"^(.*?)\s*<(.*?)>$", part)
		if m:
			t = tomlkit.inline_table()
			t.update({"name": m.group(1).strip(), "email": m.group(2).strip()})
			authorsList.append(t)
		elif part:
			t = tomlkit.inline_table()
			t.update({"name": part, "email": ""})
			authorsList.append(t)
	return authorsList


def cleanupPlaceholderAuthors(projectSection: dict[str, Any]) -> None:
	"""Remove NV Access placeholder entries from authors and maintainers fields in-place.

	:param projectSection: The project table/dictionary within the TOML structure.
	:return: None
	"""
	for field in ["authors", "maintainers"]:
		if field in projectSection and isinstance(projectSection[field], list):
			tomlList = projectSection[field]
			# Reverse loop to safely delete by index within tomlkit structure
			for i in range(len(tomlList) - 1, -1, -1):
				item = tomlList[i]
				name = item.get("name", "") if hasattr(item, "get") else ""
				if not name and isinstance(item, dict):
					name = item.get("name", "")

				if str(name).strip().lower() in ["nv access", "nvaccess"]:
					tomlList.pop(i)


def getBasePackageName(s: str) -> str:
	"""Extract base package name robustly (handles !=, <=, ~=, @ URLs, markers, etc.).

	:param s: The raw dependency string.
	:return: The normalized base package name in lowercase.
	"""
	m = re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", s.strip())
	return m.group(0).lower() if m else s.strip().lower()


def replaceAstRange(tplLines: list[str], replacements: dict[tuple[int, int], str]) -> None:
	"""Apply AST line replacements on a line-by-line list in reverse order.

	:param tplLines: The list of lines representing the file content.
	:param replacements: A dictionary mapping (start_line, end_line) tuples to the replacing string.
	:return: None
	"""
	sortedRanges = sorted(replacements.keys(), key=lambda x: x[0], reverse=True)
	for start, end in sortedRanges:
		tplLines[start:end] = [replacements[(start, end)]]


def deepMergeDicts(dictProj: dict[str, Any], dictTpl: dict[str, Any]) -> dict[str, Any]:
	"""Recursively merges dictTpl into dictProj.

	Note: tomlkit returns custom table/array objects that behave like mappings/sequences but are not
	instances of built-in `dict`/`list`, so we must detect by ABCs rather than concrete types.

	:param dictProj: The original dictionary to be updated.
	:param dictTpl: The template dictionary whose values will be merged into dictProj.
	:return: The updated dictProj with merged values from dictTpl.
	"""
	for key, value in dictTpl.items():
		if key in dictProj:
			projVal = dictProj[key]
			if isinstance(projVal, MutableMapping) and isinstance(value, MutableMapping):
				deepMergeDicts(projVal, value)
			elif isinstance(projVal, MutableSequence) and isinstance(value, MutableSequence):
				for item in value:
					if item not in projVal:
						projVal.append(item)
			else:
				pass
		else:
			dictProj[key] = value
	return dictProj


def extractBuildvarsMetadata(filePath: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
	"""Extract metadata from an old buildVars.py file safely using modern AST APIs.

	:param filePath: The path to the buildVars.py file.
	:return: A tuple containing two dictionaries: metadata and globalVars.
	"""
	p = Path(filePath)
	if not p.exists():
		return {}, {}

	with p.open("r", encoding="utf-8") as f:
		try:
			tree = ast.parse(f.read())
		except SyntaxError as e:
			print(f"[-] Syntax error while reading {p}: {e}")
			return {}, {}

	metadata: dict[str, Any] = {}
	globalVars: dict[str, Any] = {}
	topLevelVars: set[str] = {
		"pythonSources",
		"excludedFiles",
		"baseLanguage",
		"markdownExtensions",
		"brailleTables",
		"symbolDictionaries",
		"speechDictionaries",
	}

	for node in ast.walk(tree):
		if isinstance(node, ast.Assign) and len(node.targets) == 1:
			target = node.targets[0]
			if not isinstance(target, ast.Name):
				continue
			varName = target.id

			if varName == "addon_info":
				if isinstance(node.value, ast.Dict):
					metadata.update(parseAstDict(node.value))
				elif isinstance(node.value, ast.Call) and getattr(node.value.func, "id", None) == "AddonInfo":
					metadata.update(parseAstKeywords(node.value.keywords))
			elif varName in topLevelVars:
				globalVars[varName] = ast.unparse(node.value)
		elif isinstance(node, ast.AnnAssign):
			if isinstance(node.target, ast.Name) and node.target.id in topLevelVars:
				if node.value is not None:
					globalVars[node.target.id] = ast.unparse(node.value)

	return metadata, globalVars


def mergePyprojectToml(projPath: str | Path, tplPath: str | Path, metadata: dict[str, Any], dryRun: bool = False) -> str:
	"""Merge template pyproject.toml configuration into the developer's file.

	:param projPath: Path to the existing pyproject.toml file.
	:param tplPath: Path to the template pyproject.toml file.
	:param metadata: Dictionary containing legacy metadata values from buildVars.py.
	:param dryRun: If True, simulate the merge without writing changes to disk.
	:return: A string indicating the result of the merge operation.
	"""
	pTpl = Path(tplPath)
	pProj = Path(projPath)

	if not pTpl.exists():
		return "skipped (no template)"

	if not pProj.exists():
		try:
			with pTpl.open("r", encoding="utf-8") as f:
				projData = tomlkit.parse(f.read())

			if "project" not in projData:
				projData["project"] = tomlkit.table()

			if "addon_name" in metadata and metadata["addon_name"]:
				projData["project"]["name"] = metadata["addon_name"]

			if "addon_summary" in metadata and metadata["addon_summary"]:
				projData["project"]["description"] = metadata["addon_summary"]

			# Extract the repository URL from buildVars metadata
			# Always preserve the key even if it is empty ("")
			addonUrl = str(metadata.get("addon_url", "")).strip()
			
			if "urls" not in projData["project"]:
				projData["project"]["urls"] = tomlkit.table()

			projData["project"]["urls"]["Repository"] = addonUrl

			# Build the maintainers multiline array using standard inline tables
			if "addon_author" in metadata and metadata["addon_author"]:
				projData["project"]["maintainers"] = formatAuthorList(metadata["addon_author"])

			if not dryRun:
				# Dump to string and sanitize indentation to strict tabs before writing
				tomlOutput = tomlkit.dumps(projData)
				tomlOutput = tomlOutput.replace("    ", "\t")

				with pProj.open("w", encoding="utf-8") as f:
					f.write(tomlOutput)
			return "created from template"
		except Exception as e:
			return f"failed to create from template ({str(e)})"

	try:
		with pProj.open("r", encoding="utf-8") as f:
			projData = tomlkit.parse(f.read())
		with pTpl.open("r", encoding="utf-8") as f:
			tplData = tomlkit.parse(f.read())

		# Check if NV Access was ALREADY the original author/maintainer of the project
		wasOriginallyNvaccess = False
		if "project" in projData:
			for field in ["authors", "maintainers"]:
				if field in projData["project"] and isinstance(projData["project"][field], list):
					for item in projData["project"][field]:
						name = item.get("name", "") if hasattr(item, "get") else ""
						if not name and isinstance(item, dict):
							name = item.get("name", "")
						if str(name).strip().lower() in ["nv access", "nvaccess"]:
							wasOriginallyNvaccess = True
							break

		# Backup dependencies from project to merge them manually later
		projDeps = []
		if "project" in projData and "dependencies" in projData["project"]:
			projDeps = list(projData["project"]["dependencies"])
			# Temporarily remove dependencies from project to let template comments win
			del projData["project"]["dependencies"]

		# Execute the main structural merge
		mergedData = deepMergeDicts(cast(dict[str, Any], projData), cast(dict[str, Any], tplData))

		if "project" in mergedData:
			projectSection = mergedData["project"]

			# 1. Conditional cleanup of NV Access placeholders
			# Only remove them if NV Access wasn't the original author of the add-on
			if not wasOriginallyNvaccess:
				cleanupPlaceholderAuthors(projectSection)

			# 2. Smart merge of dependencies (Template layout and comments win)
			if "dependencies" in projectSection:
				tplDeps = projectSection["dependencies"]
				tplBases = {getBasePackageName(d) for d in tplDeps}

				# Append custom user dependencies only if they are not already defined by the template
				for dep in projDeps:
					base = getBasePackageName(dep)
					if base not in tplBases:
						tplDeps.append(dep)

		if not dryRun:
			with pProj.open("w", encoding="utf-8") as f:
				f.write(tomlkit.dumps(cast(tomlkit.TOMLDocument, mergedData)))
		return "merged intelligently (tomlkit)"
	except Exception as e:
		return f"failed to merge ({str(e)})"


def mergeBuildvarsFile(
	projPath: str | Path,
	tplPath: str | Path,
	metadata: dict[str, Any],
	globalVars: dict[str, Any],
	dryRun: bool = False,
) -> str:
	"""Merge template buildVars.py using precise AST range tracking to prevent multiline leaks.

	:param projPath: Path to the existing buildVars.py file.
	:param tplPath: Path to the template buildVars.py file.
	:param metadata: Dictionary containing metadata values to update.
	:param globalVars: Dictionary containing global variable values to update.
	:param dryRun: If True, simulate the merge without writing changes to disk.
	:return: A string indicating the result of the merge operation.
	"""
	pTpl = Path(tplPath)
	pProj = Path(projPath)

	if not pTpl.exists():
		return "failed (no template found)"

	with pTpl.open("r", encoding="utf-8") as f:
		tplContent = f.read()

	try:
		tree = ast.parse(tplContent)
	except SyntaxError as e:
		return f"failed (template syntax error: {e})"

	tplLines = tplContent.splitlines(keepends=True)
	replacements: dict[tuple[int, int], str] = {}

	for node in ast.walk(tree):
		if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "AddonInfo":
			for kw in node.keywords:
				if kw.arg in metadata:
					key = kw.arg
					val = metadata[key]
					if val is None:
						formattedVal = "None"
					elif isinstance(val, str):
						isTranslatable = key in ["addon_summary", "addon_description", "addon_changelog"]
						formattedVal = f'_({val!r})' if isTranslatable else repr(val)
					else:
						formattedVal = str(val)

					if kw.end_lineno is not None:
						lineContent = tplLines[kw.lineno - 1]
						indent = lineContent[: len(lineContent) - len(lineContent.lstrip())]
						replacements[(kw.lineno - 1, kw.end_lineno)] = f"{indent}{key}={formattedVal},\n"

		elif isinstance(node, ast.Assign) and len(node.targets) == 1:
			target = node.targets[0]
			if isinstance(target, ast.Name) and target.id in globalVars:
				key = target.id
				valExpression = globalVars[key]
				if node.end_lineno is not None:
					lineContent = tplLines[node.lineno - 1]
					indent = lineContent[: len(lineContent) - len(lineContent.lstrip())]
					prefix = f"{indent}import os\n" if "os." in valExpression else ""
					replacements[(node.lineno - 1, node.end_lineno)] = (
						f"{prefix}{indent}{key} = {valExpression}\n"
					)

		elif isinstance(node, ast.AnnAssign):
			if isinstance(node.target, ast.Name) and node.target.id in globalVars:
				key = node.target.id
				valExpression = globalVars[key]
				if node.end_lineno is not None:
					lineContent = tplLines[node.lineno - 1]
					indent = lineContent[: len(lineContent) - len(lineContent.lstrip())]
					typeStr = ast.unparse(node.annotation)
					prefix = f"{indent}import os\n" if "os." in valExpression else ""
					replacements[(node.lineno - 1, node.end_lineno)] = (
						f"{prefix}{indent}{key}: {typeStr} = {valExpression}\n"
					)

	replaceAstRange(tplLines, replacements)

	if not dryRun:
		with pProj.open("w", encoding="utf-8") as f:
			f.writelines(tplLines)
	return "merged & structured (AST verified)"


def runSynchronization(tempDir: str, addonDir: str, dryRun: bool) -> None:
	"""Synchronizes template machinery files from the temporary workspace into the target directory.

	:param tempDir: Path to the local temporary directory containing the template files.
	:param addonDir: Path to the target add-on root directory.
	:param dryRun: If True, simulate the sync without writing changes to disk.
	:return: None
	"""
	print("[*] Synchronizing template machinery files...")
	protectedElements = {
		"readme.md",
		"changelog.md",
		"addon",
		".git",
		"__pycache__",
		".venv",
		"docs",
		".ruff_cache",
	}

	# Dynamically load custom ignore patterns from the target add-on directory if they exist
	ignoreFilePath = os.path.join(addonDir, ".addonmergeignore")
	if os.path.exists(ignoreFilePath):
		print("[*] Reading local custom exclusions from .addonmergeignore...")
		try:
			with open(ignoreFilePath, "r", encoding="utf-8") as f:
				for line in f:
					cleanLine = line.strip().lower()
					# Exclude comments and empty lines
					if cleanLine and not cleanLine.startswith("#"):
						protectedElements.add(cleanLine)
		except Exception as e:
			print(f"[-] Warning: Failed to parse .addonmergeignore ({e})")

	syncReport: list[str] = []

	for item in os.listdir(tempDir):
		if item.lower() in protectedElements:
			syncReport.append(f"{item} .................... skipped (protected scope)")
			continue

		if item in ["buildVars.py", "pyproject.toml"]:
			continue

		srcItem = os.path.join(tempDir, item)
		dstItem = os.path.join(addonDir, item)

		try:
			if os.path.isdir(srcItem):
				if not dryRun:
					os.makedirs(dstItem, exist_ok=True)
					shutil.copytree(srcItem, dstItem, dirs_exist_ok=True)
				syncReport.append(f"{item}/ ................... merged safely")
			else:
				if not dryRun:
					shutil.copy2(srcItem, dstItem)
				syncReport.append(f"{item} .................... synchronized")
		except Exception as e:
			syncReport.append(f"{item} .................... failed ({str(e)})")

	print("[*] Phase 4: Processing structural configuration merges...")
	templateBuildvars = os.path.join(tempDir, "buildVars.py")
	templatePyproject = os.path.join(tempDir, "pyproject.toml")

	oldBuildvars = os.path.join(addonDir, "buildVars.py")
	oldPyproject = os.path.join(addonDir, "pyproject.toml")

	bvMeta, bvGlobals = extractBuildvarsMetadata(oldBuildvars)
	addonName = bvMeta.get("addon_name", os.path.basename(addonDir))

	bvStatus = mergeBuildvarsFile(oldBuildvars, templateBuildvars, bvMeta, bvGlobals, dryRun)
	ppStatus = mergePyprojectToml(oldPyproject, templatePyproject, bvMeta, dryRun)

	print("\n" + "=" * 50)
	print("UPDATE REPORT")
	print("=" * 50)
	print(f"Add-on ....................... {addonName}")
	print("\nTemplate synchronization:")
	for entry in syncReport:
		print(f"  - {entry}")
	print(
		f"\nConfiguration files:\n"
		f"  buildVars.py ............... {bvStatus}\n"
		f"  pyproject.toml ............. {ppStatus}",
	)


def main() -> None:
	"""Execute main CLI entry point for the NVDA Add-on update tool."""
	parser = argparse.ArgumentParser(
		description="Non-destructive industrial update tool for NVDA Add-ons.",
	)
	parser.add_argument(
		"-ad", "--addon-dir",
		dest="addonDir",
		default=None,
		help="Path to the root directory of the add-on to update (defaults to current directory).",
	)
	parser.add_argument(
		"-td", "--template-dir",
		dest="templateDir",
		default=None,
		help="Path to a local directory containing the NVDA AddonTemplate to use instead of fetching it via Git.",
	)
	parser.add_argument(
		"-dr", "--dry-run",
		dest="dryRun",
		action="store_true",
		help="Simulate execution without modifying any files.",
	)
	parser.add_argument(
		"-s", "--skip-backup",
		dest="skipBackup",
		action="store_true",
		help="Disable safety automatic project backup.",
	)
	args = parser.parse_args()

	addonDirInput = args.addonDir
	if addonDirInput:
		addonDir = os.path.abspath(addonDirInput)
	else:
		# If executed from a subdirectory, walk upwards to find the add-on root.
		cwd = Path(os.getcwd()).resolve()
		addonRoot = next((p for p in (cwd, *cwd.parents) if (p / "buildVars.py").exists()), None)
		addonDir = str(addonRoot) if addonRoot is not None else str(cwd)

	print("=== NVDA ADD-ON UPDATE TOOL ===")
	print(f"[*] Target Directory: {addonDir}")

	oldBuildvars = os.path.join(addonDir, "buildVars.py")

	if not os.path.exists(oldBuildvars):
		print(f"[-] Error: '{addonDir}' does not appear to be a valid NVDA Add-on (missing buildVars.py).")
		if sys.stdin.isatty():
			input("\nPress Enter to exit...")
		sys.exit(1)

	print("[*] Phase 1: Analyzing existing project structure and metadata...")
	bvMeta, _ = extractBuildvarsMetadata(oldBuildvars)
	addonName = bvMeta.get("addon_name", os.path.basename(addonDir))
	print(f"[+] Target Add-on Identified: {addonName}")

	if args.dryRun:
		print("[!] RUNNING IN SIMULATION MODE (--dry-run). No files will be modified.")

	print("[*] Phase 2: Safety backup verification...")
	if args.dryRun:
		print("[*] Safety backup skipped (simulation mode active).")
	elif args.skipBackup:
		print("[!] Safety backup skipped (--skip-backup requested by user).")
	else:
		backupDir = f"{addonDir}_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
		print(f"[*] Creating safety automatic backup in: {os.path.basename(backupDir)}...")
		try:
			shutil.copytree(
				addonDir,
				backupDir,
				ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv", "*_bak_*"),
			)
			print("[+] Backup created successfully.")
		except Exception as e:
			print(f"[-] Critical: Backup failed ({e}). Aborting update.")
			if sys.stdin.isatty():
				input("\nPress Enter to exit...")
			sys.exit(1)

	if args.templateDir:
		templatePath = os.path.abspath(args.templateDir)
		print(f"[*] Phase 3: Using local template directory: {templatePath}")
		if not os.path.exists(os.path.join(templatePath, "buildVars.py")):
			print("[-] Error: Provided template directory does not appear to be a valid NVDA AddonTemplate (missing buildVars.py).")
			if sys.stdin.isatty():
				input("\nPress Enter to exit...")
			sys.exit(1)
		runSynchronization(templatePath, addonDir, args.dryRun)
	else:
		print("[*] Phase 3: Provisioning latest official NVDA AddonTemplate via Git...")
		with tempfile.TemporaryDirectory() as tempDir:
			print("[*] Cloning template into temporary workspace...")
			templateUrl = "https://github.com/nvaccess/AddonTemplate.git"

			try:
				subprocess.run(
					["git", "clone", "--depth", "1", templateUrl, tempDir],
					check=True,
					stdout=subprocess.DEVNULL,
					stderr=subprocess.PIPE,
				)
				print("[+] Template cloned successfully.")
			except (subprocess.CalledProcessError, FileNotFoundError) as e:
				print("[-] Error: Failed to execute git clone. Make sure Git is available in your PATH.")
				if isinstance(e, subprocess.CalledProcessError) and e.stderr:
					print(f"Details: {e.stderr.decode('utf-8', errors='ignore')}")
				if sys.stdin.isatty():
					input("\nPress Enter to exit...")
				sys.exit(1)

			runSynchronization(tempDir, addonDir, args.dryRun)

	if not args.dryRun:
		print("\n[+] Project successfully updated. Workspace cleared.")
	else:
		print("\n[+] Simulation finished. Workspace cleared.")


if __name__ == "__main__":
	main()
    