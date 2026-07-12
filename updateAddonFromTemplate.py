# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

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


def deepMergeDicts(dictProj: dict[str, Any], dictTpl: dict[str, Any]) -> dict[str, Any]:
	"""Recursively merges dictTpl into dictProj.

	Note: tomlkit returns custom table/array objects that behave like mappings/sequences but are not
	instances of built-in `dict`/`list`, so we must detect by ABCs rather than concrete types.
	"""
	from collections.abc import MutableMapping, MutableSequence

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
	topLevelVars = {
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
					for keyNode, valNode in zip(node.value.keys, node.value.values):
						if keyNode is None:
							continue
						key = getattr(keyNode, "value", None)
						if isinstance(valNode, ast.Call) and getattr(valNode.func, "id", None) == "_":
							valNode = valNode.args[0]
						val = getattr(valNode, "value", None)
						if key is not None:
							metadata[key] = val
				elif isinstance(node.value, ast.Call) and getattr(node.value.func, "id", None) == "AddonInfo":
					for keyword in node.value.keywords:
						key = keyword.arg
						valNode = keyword.value
						if isinstance(valNode, ast.Call) and getattr(valNode.func, "id", None) == "_":
							valNode = valNode.args[0]
						val = getattr(valNode, "value", None)
						if key is not None:
							metadata[key] = val
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

			# Build the maintainers multiline array using standard inline tables
			authors_list = tomlkit.array()
			authors_list.multiline(True)

			if "addon_author" in metadata and metadata["addon_author"]:
				import re
				raw_authors = str(metadata["addon_author"])
				parts = [p.strip() for p in raw_authors.split(",") if p.strip()]

				for part in parts:
					m = re.match(r"^(.*?)\s*<(.*?)>$", part)
					if m:
						t = tomlkit.inline_table()
						t.update({"name": m.group(1).strip(), "email": m.group(2).strip()})
						authors_list.append(t)
					elif part:
						t = tomlkit.inline_table()
						t.update({"name": part, "email": ""})
						authors_list.append(t)

			projData["project"]["maintainers"] = authors_list

			if not dryRun:
				# Dump to string and sanitize indentation to strict tabs before writing
				toml_output = tomlkit.dumps(projData)
				toml_output = toml_output.replace("    ", "\t")

				with pProj.open("w", encoding="utf-8") as f:
					f.write(toml_output)
			return "created from template"
		except Exception as e:
			return f"failed to create from template ({str(e)})"

	try:
		with pProj.open("r", encoding="utf-8") as f:
			projData = tomlkit.parse(f.read())
		with pTpl.open("r", encoding="utf-8") as f:
			tplData = tomlkit.parse(f.read())

		# Check if NV Access was ALREADY the original author/maintainer of the project
		was_originally_nvaccess = False
		if "project" in projData:
			for field in ["authors", "maintainers"]:
				if field in projData["project"] and isinstance(projData["project"][field], list):
					for item in projData["project"][field]:
						name = item.get("name", "") if hasattr(item, "get") else ""
						if not name and isinstance(item, dict):
							name = item.get("name", "")
						if str(name).strip().lower() in ["nv access", "nvaccess"]:
							was_originally_nvaccess = True
							break

		# Backup dependencies from project to merge them manually later
		proj_deps = []
		if "project" in projData and "dependencies" in projData["project"]:
			proj_deps = list(projData["project"]["dependencies"])
			# Temporarily remove dependencies from project to let template comments win
			del projData["project"]["dependencies"]

		# Execute the main structural merge
		mergedData = deepMergeDicts(cast(dict[str, Any], projData), cast(dict[str, Any], tplData))

		if "project" in mergedData:
			project_section = mergedData["project"]

			# 1. Conditional cleanup of NV Access placeholders
			# Only remove them if NV Access wasn't the original author of the add-on
			if not was_originally_nvaccess:
				for field in ["authors", "maintainers"]:
					if field in project_section and isinstance(project_section[field], list):
						toml_list = project_section[field]
						# Reverse loop to safely delete by index within tomlkit structure
						for i in range(len(toml_list) - 1, -1, -1):
							item = toml_list[i]
							name = item.get("name", "") if hasattr(item, "get") else ""
							if not name and isinstance(item, dict):
								name = item.get("name", "")

							if str(name).strip().lower() in ["nv access", "nvaccess"]:
								toml_list.pop(i)

			# 2. Smart merge of dependencies (Template layout and comments win)
			if "dependencies" in project_section:
				tpl_deps = project_section["dependencies"]

				# Extract base package name robustly (handles !=, <=, ~=, @ URLs, markers, etc.)
				def get_base(s: str) -> str:
					import re
					m = re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*", s.strip())
					return m.group(0).lower() if m else s.strip().lower()
				tpl_bases = {get_base(d) for d in tpl_deps}

				# Append custom user dependencies only if they are not already defined by the template
				for dep in proj_deps:
					base = get_base(dep)
					if base not in tpl_bases:
						tpl_deps.append(dep)

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
	:Return: A string indicating the result of the merge operation.
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
						is_translatable = key in ["addon_summary", "addon_description", "addon_changelog"]
						formattedVal = f"_({val!r})" if is_translatable else repr(val)
					else:
						formattedVal = str(val)

					if kw.end_lineno is not None:
						line_content = tplLines[kw.lineno - 1]
						indent = line_content[: len(line_content) - len(line_content.lstrip())]
						replacements[(kw.lineno - 1, kw.end_lineno)] = f"{indent}{key}={formattedVal},\n"

		elif isinstance(node, ast.Assign) and len(node.targets) == 1:
			target = node.targets[0]
			if isinstance(target, ast.Name) and target.id in globalVars:
				key = target.id
				valExpression = globalVars[key]
				if node.end_lineno is not None:
					line_content = tplLines[node.lineno - 1]
					indent = line_content[: len(line_content) - len(line_content.lstrip())]
					prefix = f"{indent}import os\n" if "os." in valExpression else ""
					replacements[(node.lineno - 1, node.end_lineno)] = (
						f"{prefix}{indent}{key} = {valExpression}\n"
					)

		elif isinstance(node, ast.AnnAssign):
			if isinstance(node.target, ast.Name) and node.target.id in globalVars:
				key = node.target.id
				valExpression = globalVars[key]
				if node.end_lineno is not None:
					line_content = tplLines[node.lineno - 1]
					indent = line_content[: len(line_content) - len(line_content.lstrip())]
					typeStr = ast.unparse(node.annotation)
					prefix = f"{indent}import os\n" if "os." in valExpression else ""
					replacements[(node.lineno - 1, node.end_lineno)] = (
						f"{prefix}{indent}{key}: {typeStr} = {valExpression}\n"
					)

	sortedRanges = sorted(replacements.keys(), key=lambda x: x[0], reverse=True)
	for start, end in sortedRanges:
		tplLines[start:end] = [replacements[(start, end)]]

	if not dryRun:
		with pProj.open("w", encoding="utf-8") as f:
			f.writelines(tplLines)
	return "merged & structured (AST verified)"


def main() -> None:
	"""Execute main CLI entry point for the NVDA Add-on update tool."""
	parser = argparse.ArgumentParser(
		description="Non-destructive industrial update tool for NVDA Add-ons.",
	)
	parser.add_argument(
		"addonDir",
		nargs="?",
		default=None,
		help="Path to the root directory of the add-on to update (defaults to current directory).",
	)
	parser.add_argument(
		"--dry-run",
		dest="dryRun",
		action="store_true",
		help="Simulate execution without modifying any files.",
	)
	parser.add_argument(
		"--skip-backup",
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
	oldPyproject = os.path.join(addonDir, "pyproject.toml")

	if not os.path.exists(oldBuildvars):
		print(f"[-] Error: '{addonDir}' does not appear to be a valid NVDA Add-on (missing buildVars.py).")
		if sys.stdin.isatty():
			input("\nPress Enter to exit...")
		sys.exit(1)

	print("[*] Phase 1: Analyzing existing project structure and metadata...")
	bvMeta, bvGlobals = extractBuildvarsMetadata(oldBuildvars)
	addonName = bvMeta.get("addon_name", os.path.basename(addonDir))
	print(f"[+] Target Add-on Identified: {addonName}")

	if args.dryRun:
		print("[!] RUNNING IN SIMULATION MODE (--dry-run). No files will be modified.")

	if not args.skipBackup and not args.dryRun:
		backupDir = f"{addonDir}_bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
		print(f"[*] Phase 2: Creating safety automatic backup in: {os.path.basename(backupDir)}...")
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
	else:
		print("[*] Phase 2: Safety backup skipped.")

	print("[*] Phase 3: Provisioning latest official NVDA AddonTemplate via Git...")

	# List of template-relative paths to ignore during synchronization (requested by @CyrilleB79)
	# Lowercase paths are used to prevent case mismatch issues across OS environments
	IGNORED_FILES = {
		#os.path.join(".github", "workflows", "build_addon.yml").lower(),
	}

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
			"updateaddonfromtemplate.py",
		}
		syncReport = []

		# Custom ignore handler for shutil.copytree to filter subdirectories and files
		def tree_ignore_handler(path: str, names: list[str]) -> list[str]:
			ignored = []
			for name in names:
				full_sub_path = os.path.join(path, name)
				rel_sub_path = os.path.relpath(full_sub_path, start=tempDir).lower()
				if rel_sub_path in IGNORED_FILES:
					ignored.append(name)
			return ignored

		for item in os.listdir(tempDir):
			if item.lower() in protectedElements:
				syncReport.append(f"{item} .................... skipped (protected scope)")
				continue

			if item in ["buildVars.py", "pyproject.toml"]:
				continue

			srcItem = os.path.join(tempDir, item)
			dstItem = os.path.join(addonDir, item)

			# Check if the root item itself is explicitly ignored
			relItemPath = os.path.relpath(srcItem, start=tempDir).lower()
			if relItemPath in IGNORED_FILES:
				syncReport.append(f"{item} .................... skipped (user ignored)")
				continue

			try:
				if os.path.isdir(srcItem):
					if not args.dryRun:
						os.makedirs(dstItem, exist_ok=True)
						shutil.copytree(srcItem, dstItem, ignore=tree_ignore_handler, dirs_exist_ok=True)
					syncReport.append(f"{item}/ ................... merged safely")
				else:
					if not args.dryRun:
						shutil.copy2(srcItem, dstItem)
					syncReport.append(f"{item} .................... synchronized")
			except Exception as e:
				syncReport.append(f"{item} .................... failed ({str(e)})")

		print("[*] Phase 4: Processing structural configuration merges...")
		templateBuildvars = os.path.join(tempDir, "buildVars.py")
		templatePyproject = os.path.join(tempDir, "pyproject.toml")

		bvStatus = mergeBuildvarsFile(oldBuildvars, templateBuildvars, bvMeta, bvGlobals, args.dryRun)
		ppStatus = mergePyprojectToml(oldPyproject, templatePyproject, bvMeta, args.dryRun)

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

		if not args.dryRun:
			print("\n[+] Project successfully updated. Temporary workspace destroyed.")
		else:
			print("\n[+] Simulation finished. Workspace cleared.")


if __name__ == "__main__":
	main()
