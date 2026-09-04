# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Abstract Syntax Tree (AST) parsing and manipulation utilities."""

import ast
from typing import Any


def parseAstDict(dictNode: ast.Dict) -> dict[str, Any]:
	"""Extract key-value pairs from an AST Dict node.

	:param dictNode: The ast.Dict node to parse.
	:return: A dictionary containing the extracted keys and values.
	"""
	extractedData: dict[str, Any] = {}
	keyNode: ast.expr | None
	valNode: ast.expr
	for keyNode, valNode in zip(dictNode.keys, dictNode.values):
		if keyNode is None:
			continue
		keyName: Any = getattr(keyNode, "value", None)
		if isinstance(valNode, ast.Call) and getattr(valNode.func, "id", None) == "_":
			valNode = valNode.args[0]
		valValue: Any = getattr(valNode, "value", None)
		if keyName is not None:
			extractedData[keyName] = valValue
	return extractedData


def parseAstKeywords(keywordList: list[ast.keyword]) -> dict[str, Any]:
	"""Extract key-value pairs from a list of AST keyword nodes.

	:param keywordList: The list of ast.keyword nodes to parse.
	:return: A dictionary containing the extracted keys and values.
	"""
	extractedData: dict[str, Any] = {}
	keywordItem: ast.keyword
	for keywordItem in keywordList:
		keyName: str | None = keywordItem.arg
		valNode: ast.expr = keywordItem.value
		if isinstance(valNode, ast.Call) and getattr(valNode.func, "id", None) == "_":
			valNode = valNode.args[0]
		valValue: Any = getattr(valNode, "value", None)
		if keyName is not None:
			extractedData[keyName] = valValue
	return extractedData


def usesOsModule(astNode: ast.AST) -> bool:
	"""Check recursively if an AST node contains an actual reference to the 'os' module.

	:param astNode: The AST node to inspect.
	:return: True if the node references 'os', False otherwise.
	"""
	childNode: ast.AST
	for childNode in ast.walk(astNode):
		if isinstance(childNode, ast.Name) and childNode.id == "os":
			return True
	return False


def replaceAstRange(templateLineList: list[str], replacementMap: dict[tuple[int, int], str]) -> None:
	"""Apply AST line replacements on a line-by-line list in reverse order.

	:param templateLineList: The list of lines representing the file content.
	:param replacementMap: A dictionary mapping (startLine, endLine) tuples to the replacing string.
	:return: None
	"""
	sortedRanges: list[tuple[int, int]] = sorted(replacementMap.keys(), key=lambda rangeTuple: rangeTuple[0], reverse=True)
	startLineIndex: int
	endLineIndex: int
	for startLineIndex, endLineIndex in sortedRanges:
		templateLineList[startLineIndex:endLineIndex] = [replacementMap[(startLineIndex, endLineIndex)]]
