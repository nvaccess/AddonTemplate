# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Extraction, parsing, and precise AST range merging for buildVars.py."""

import ast
import logging
from pathlib import Path
from typing import Any

from .astUtils import parseAstDict, parseAstKeywords, replaceAstRange, usesOsModule

logger: logging.Logger = logging.getLogger("syncAddon")


def formatStringLiteral(val: str, useDoubleQuotes: bool = False, isTranslatable: bool = False) -> str:
	"""Format a string literal preserving either double or single quotes.

	:param val: The string value to format.
	:param useDoubleQuotes: If True, format using double quotes; otherwise default to single quotes.
	:param isTranslatable: If True, wrap the formatted string in the gettext `_()` call.
	:return: The formatted string literal representation, optionally wrapped in `_()`.
	"""
	formattedText: str
	if useDoubleQuotes:
		# Escape backslashes and internal double quotes if needed
		escapedValText: str = val.replace("\\", "\\\\").replace('"', '\\"')
		formattedText = f'"{escapedValText}"'
	else:
		# Default style using repr (single quotes)
		formattedText = repr(val)

	return f"_({formattedText})" if isTranslatable else formattedText


def extractBuildvarsMetadata(filePath: str | Path) -> tuple[dict[str, Any], dict[str, tuple[ast.AST, str]]]:
	"""Extract metadata and raw assignment expressions along with AST nodes from buildVars.py safely.

	:param filePath: The path to the buildVars.py file.
	:return: A tuple containing two dictionaries: metadata and globalVars mapping varName -> (astNode, unparsedExpr).
	"""
	fileRootPath: Path = Path(filePath)
	if not fileRootPath.exists():
		return {}, {}

	with fileRootPath.open("r", encoding="utf-8") as f:
		try:
			parsedTree: ast.AST = ast.parse(f.read())
		except SyntaxError as syntaxErrorObj:
			logger.error("Syntax error while reading %s: %s", fileRootPath, syntaxErrorObj)
			raise

	metadataDict: dict[str, Any] = {}
	globalVarsDict: dict[str, tuple[ast.AST, str]] = {}
	topLevelVarsSet: set[str] = {
		"pythonSources",
		"excludedFiles",
		"baseLanguage",
		"markdownExtensions",
		"brailleTables",
		"symbolDictionaries",
		"speechDictionaries",
	}

	astNodeItem: ast.AST
	for astNodeItem in ast.walk(parsedTree):
		if isinstance(astNodeItem, ast.Assign) and len(astNodeItem.targets) == 1:
			assignTarget: ast.expr = astNodeItem.targets[0]
			if not isinstance(assignTarget, ast.Name):
				continue
			varNameText: str = assignTarget.id

			if varNameText == "addon_info":
				if isinstance(astNodeItem.value, ast.Dict):
					metadataDict.update(parseAstDict(astNodeItem.value))
				elif isinstance(astNodeItem.value, ast.Call) and getattr(astNodeItem.value.func, "id", None) == "AddonInfo":
					metadataDict.update(parseAstKeywords(astNodeItem.value.keywords))
			elif varNameText in topLevelVarsSet:
				# Preserve raw source segment to maintain original quote formatting
				rawSegmentText: str | None = ast.get_source_segment(tplContentText if 'tplContentText' in locals() else f.read(), astNodeItem.value) if False else None
				# Note: Read source directly or fallback to ast.unparse
				sourceSegmentText: str = ast.get_source_segment(fileRootPath.read_text(encoding="utf-8"), astNodeItem.value) or ast.unparse(astNodeItem.value)
				globalVarsDict[varNameText] = (astNodeItem.value, sourceSegmentText)
		elif isinstance(astNodeItem, ast.AnnAssign):
			if isinstance(astNodeItem.target, ast.Name) and astNodeItem.target.id in topLevelVarsSet:
				if astNodeItem.value is not None:
					sourceSegmentText = ast.get_source_segment(fileRootPath.read_text(encoding="utf-8"), astNodeItem.value) or ast.unparse(astNodeItem.value)
					globalVarsDict[astNodeItem.target.id] = (astNodeItem.value, sourceSegmentText)

	return metadataDict, globalVarsDict


def mergeBuildvarsFile(
	projFilePath: str | Path,
	tplFilePath: str | Path,
	metadataDict: dict[str, Any],
	globalVarsDict: dict[str, tuple[ast.AST, str]],
	dryRun: bool = False,
) -> str:
	"""Merge template buildVars.py using precise AST range tracking to prevent multiline leaks.

	:param projFilePath: Path to the existing buildVars.py file.
	:param tplFilePath: Path to the template buildVars.py file.
	:param metadataDict: Dictionary containing metadata values to update.
	:param globalVarsDict: Dictionary containing global variables mapping varName -> (astNode, unparsedExpr).
	:param dryRun: If True, simulate the merge without writing changes to disk.
	:return: A string indicating the result of the merge operation.
	"""
	templatePathObj: Path = Path(tplFilePath)
	projectPathObj: Path = Path(projFilePath)

	if not templatePathObj.exists():
		return "failed (no template found)"

	with templatePathObj.open("r", encoding="utf-8") as f:
		tplContentText: str = f.read()

	try:
		parsedTree: ast.AST = ast.parse(tplContentText)
	except SyntaxError as syntaxErr:
		return f"failed (template syntax error: {syntaxErr})"

	templateLineList: list[str] = tplContentText.splitlines(keepends=True)
	replacementMap: dict[tuple[int, int], str] = {}
	requiresOsImport: bool = False

	astNodeItem: ast.AST
	for astNodeItem in ast.walk(parsedTree):
		if isinstance(astNodeItem, ast.Call) and getattr(astNodeItem.func, "id", None) == "AddonInfo":
			kwItem: ast.keyword
			for kwItem in astNodeItem.keywords:
				if kwItem.arg in metadataDict:
					keyName: str = kwItem.arg
					valueVal: Any = metadataDict[keyName]
					formattedValueText: str
					if valueVal is None:
						formattedValueText = "None"
					elif isinstance(valueVal, str):
						isTranslatable: bool = keyName in ["addon_summary", "addon_description", "addon_changelog"]
						
						# Inspect source segment to detect original quote style (double vs single)
						rawSourceText: str = ast.get_source_segment(tplContentText, kwItem.value) or ""
						cleanedSourceText: str = rawSourceText.strip()
						useDoubleQuotesBool: bool = cleanedSourceText.startswith('"') or cleanedSourceText.startswith('_("')
						
						formattedValueText = formatStringLiteral(
							valueVal,
							useDoubleQuotes=useDoubleQuotesBool,
							isTranslatable=isTranslatable,
						)
					else:
						formattedValueText = str(valueVal)

					if kwItem.end_lineno is not None:
						lineContentText: str = templateLineList[kwItem.lineno - 1]
						indentText: str = lineContentText[: len(lineContentText) - len(lineContentText.lstrip())]
						replacementMap[(kwItem.lineno - 1, kwItem.end_lineno)] = (
							f"{indentText}{keyName}={formattedValueText},\n"
						)

		elif isinstance(astNodeItem, ast.Assign) and len(astNodeItem.targets) == 1:
			assignTarget: ast.expr = astNodeItem.targets[0]
			if isinstance(assignTarget, ast.Name) and assignTarget.id in globalVarsDict:
				keyName = assignTarget.id
				valAstNode: ast.AST
				valExprText: str
				valAstNode, valExprText = globalVarsDict[keyName]
				if usesOsModule(valAstNode):
					requiresOsImport = True
				if astNodeItem.end_lineno is not None:
					lineContentText = templateLineList[astNodeItem.lineno - 1]
					indentText = lineContentText[: len(lineContentText) - len(lineContentText.lstrip())]
					replacementMap[(astNodeItem.lineno - 1, astNodeItem.end_lineno)] = (
						f"{indentText}{keyName} = {valExprText}\n"
					)

		elif isinstance(astNodeItem, ast.AnnAssign):
			if isinstance(astNodeItem.target, ast.Name) and astNodeItem.target.id in globalVarsDict:
				keyName = astNodeItem.target.id
				valAstNode, valExprText = globalVarsDict[keyName]
				if usesOsModule(valAstNode):
					requiresOsImport = True
				if astNodeItem.end_lineno is not None:
					lineContentText = templateLineList[astNodeItem.lineno - 1]
					indentText = lineContentText[: len(lineContentText) - len(lineContentText.lstrip())]
					typeAnnotationText: str = ast.unparse(astNodeItem.annotation)
					replacementMap[(astNodeItem.lineno - 1, astNodeItem.end_lineno)] = (
						f"{indentText}{keyName}: {typeAnnotationText} = {valExprText}\n"
					)

	replaceAstRange(templateLineList, replacementMap)

	if requiresOsImport:
		hasOsImport: bool = any("import os" in line for line in templateLineList[:15])
		if not hasOsImport:
			templateLineList.insert(0, "import os\n")

	if not dryRun:
		with projectPathObj.open("w", encoding="utf-8") as f:
			f.writelines(templateLineList)
	return "merged & structured (AST verified)"
