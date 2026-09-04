# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""TOML manipulation and pyproject.toml merging algorithms."""

from collections.abc import MutableMapping, MutableSequence
import logging
from pathlib import Path
import re
from typing import Any, cast

import tomlkit

from .utils import (
	cleanupPlaceholderAuthors,
	fixTomlIndentation,
	formatAuthorList,
	getBasePackageName,
	insertKeyAfter,
)

# Map legacy tools to their modern template equivalents (e.g. pre-commit -> prek)
REPLACED_PACKAGES: dict[str, str] = {
	"pre-commit": "prek",
}

logger: logging.Logger = logging.getLogger("syncAddon")


def createPyprojectFromTemplate(templateFilePath: Path, metadataDict: dict[str, Any]) -> tomlkit.TOMLDocument:
	"""Create a new pyproject.toml document based on the official template, preserving tab indentation.

	:param templateFilePath: Path to the reference template pyproject.toml file.
	:param metadataDict: Extracted metadata dictionary from legacy buildVars/manifest.
	:return: A tomlkit TOMLDocument adhering to template tab formatting and populated with metadata.
	"""
	with templateFilePath.open("r", encoding="utf-8") as f:
		tomlDoc: tomlkit.TOMLDocument = tomlkit.parse(f.read())

	if "project" not in tomlDoc:
		tomlDoc["project"] = tomlkit.table()

	projectSection: Any = tomlDoc["project"]

	if "addon_name" in metadataDict and metadataDict["addon_name"]:
		projectSection["name"] = metadataDict["addon_name"]

	if "addon_summary" in metadataDict and metadataDict["addon_summary"]:
		projectSection["description"] = metadataDict["addon_summary"]

	addonUrlText: str = str(metadataDict.get("addon_url", "")).strip()
	if addonUrlText:
		if "urls" not in projectSection:
			projectSection["urls"] = tomlkit.table()
		projectSection["urls"]["Repository"] = addonUrlText

	if "addon_author" in metadataDict and metadataDict["addon_author"]:
		projectSection["maintainers"] = formatAuthorList(metadataDict["addon_author"])

	return tomlDoc


def mergeDependencyLists(
	projList: list[Any],
	tplList: list[Any],
	contextName: str = "",
) -> list[Any]:
	"""Intelligently merge two dependency lists by updating package versions based on base names.

	Preserves custom user dependencies and retains user version constraints strictly
	if they are higher (>). Otherwise, updates to the template version. Handles replaced
	packages (e.g. pre-commit -> prek).

	:param projList: The existing project's dependency list.
	:param tplList: The template's dependency list.
	:param contextName: Optional key/section name for logging context.
	:return: A merged list with updated versions and preserved custom or newer user items.
	"""
	isActualDependencyList: bool = contextName in ["dependencies", "dependency-groups"]
	# Only emit decision logs if processing dependency-groups, preventing duplicate
	# or premature decision logs on flat project.dependencies before migration/purge.
	shouldLogDecisions: bool = contextName != "dependencies" and isActualDependencyList

	if projList or tplList:
		contextLabel: str = f" [{contextName}]" if contextName else ""
		if isActualDependencyList:
			logger.debug(
				"Merging dependency list%s. User count: %d, Template count: %d",
				contextLabel,
				len(projList),
				len(tplList),
			)
		else:
			logger.debug(
				"Merging list%s. User count: %d, Template count: %d",
				contextLabel,
				len(projList),
				len(tplList),
			)

	projIndexByBase: dict[str, int] = {}
	itemIndex: int
	depItem: Any
	for itemIndex, depItem in enumerate(projList):
		if isinstance(depItem, str):
			baseName: str = getBasePackageName(depItem)
			canonicalBaseName: str = REPLACED_PACKAGES.get(baseName, baseName)
			projIndexByBase[canonicalBaseName] = itemIndex

	mergedList: list[Any] = []
	handledUserIndices: set[int] = set()

	tplItem: Any
	for tplItem in tplList:
		if isinstance(tplItem, str):
			tplBaseName: str = getBasePackageName(tplItem)
			if tplBaseName in projIndexByBase:
				targetIndex: int = projIndexByBase[tplBaseName]
				handledUserIndices.add(targetIndex)
				userItemText: str = str(projList[targetIndex])
				userOriginalBaseName: str = getBasePackageName(userItemText)

				if userOriginalBaseName in REPLACED_PACKAGES:
					if shouldLogDecisions:
						logger.debug(
							"DECISION [%s]: PACKAGE REPLACED (%s -> %s), FORCING TEMPLATE VERSION -> %r",
							tplBaseName,
							userOriginalBaseName,
							tplBaseName,
							tplItem,
						)
					mergedList.append(tplItem)
					continue

				userMatch: re.Match[str] | None = re.search(r"([0-9]+(?:\.[0-9]+)+)", userItemText)
				tplMatch: re.Match[str] | None = re.search(r"([0-9]+(?:\.[0-9]+)+)", tplItem)

				if userMatch and tplMatch:
					try:
						userVersionTuple: tuple[int, ...] = tuple(map(int, userMatch.group(1).split(".")))
						tplVersionTuple: tuple[int, ...] = tuple(map(int, tplMatch.group(1).split(".")))

						if userVersionTuple > tplVersionTuple:
							if shouldLogDecisions:
								logger.debug(
									"DECISION [%s]: KEEP USER VERSION (%s > %s) -> %r",
									tplBaseName,
									userVersionTuple,
									tplVersionTuple,
									userItemText,
								)
							mergedList.append(userItemText)
							continue
						else:
							if shouldLogDecisions:
								logger.debug(
									"DECISION [%s]: USE TEMPLATE VERSION (%s <= %s) -> %r",
									tplBaseName,
									userVersionTuple,
									tplVersionTuple,
									tplItem,
								)
					except ValueError:
						pass

				mergedList.append(tplItem)
			else:
				if shouldLogDecisions:
					logger.debug("DECISION [%s]: ADD TEMPLATE DEPENDENCY %r", tplBaseName, tplItem)
				mergedList.append(tplItem)
		else:
			if tplItem not in mergedList:
				mergedList.append(tplItem)

	for itemIndex, depItem in enumerate(projList):
		if itemIndex not in handledUserIndices:
			if isinstance(depItem, str):
				baseName = getBasePackageName(depItem)
				if baseName in REPLACED_PACKAGES:
					if shouldLogDecisions:
						logger.debug(
							"DECISION [%s]: REPLACED BY TEMPLATE EQUIVALENT %r",
							baseName,
							REPLACED_PACKAGES[baseName],
						)
					continue
			if shouldLogDecisions:
				logger.debug("DECISION [custom]: PRESERVE USER DEPENDENCY %r", depItem)
			mergedList.append(depItem)

	return mergedList


def deepMergeDicts(
	projDict: dict[str, Any],
	tplDict: dict[str, Any],
	parentPath: str = "",
) -> dict[str, Any]:
	"""Recursively merge tplDict into projDict.

	:param projDict: The original project dictionary to be updated.
	:param tplDict: The template dictionary whose values will be merged into projDict.
	:param parentPath: Optional accumulated section prefix for context logging (e.g., 'tool.ruff').
	:return: The updated projDict with merged values from tplDict.
	"""
	dictKey: str
	dictValue: Any
	for dictKey, dictValue in tplDict.items():
		fullPath: str = f"{parentPath}.{dictKey}" if parentPath else dictKey
		if dictKey in projDict:
			projVal: Any = projDict[dictKey]
			if isinstance(projVal, MutableMapping) and isinstance(dictValue, MutableMapping):
				deepMergeDicts(projVal, dictValue, parentPath=fullPath)
			elif isinstance(projVal, MutableSequence) and isinstance(dictValue, MutableSequence):
				projDict[dictKey] = mergeDependencyLists(list(projVal), list(dictValue), contextName=fullPath)
			else:
				pass
		else:
			projDict[dictKey] = dictValue
	return projDict


def processDependencyGroupsMigration(
	mergedDictData: dict[str, Any],
	userFlatDependenciesList: list[Any],
) -> None:
	"""Migrate legacy flat project dependencies into modern template dependency-groups.

	Updates group versions if user versions are strictly higher, and purges migrated
	items from project.dependencies to prevent unsatisfiable uv sync conflicts.

	:param mergedDictData: The merged TOML structure dictionary.
	:param userFlatDependenciesList: The original list of flat dependencies from user's project.
	:return: None
	"""
	if "dependency-groups" not in mergedDictData:
		return

	userDepsByBaseName: dict[str, str] = {}
	depItem: Any
	for depItem in userFlatDependenciesList:
		if isinstance(depItem, str):
			baseName: str = getBasePackageName(depItem)
			canonicalBaseName: str = REPLACED_PACKAGES.get(baseName, baseName)
			userDepsByBaseName[canonicalBaseName] = depItem

	migratedBaseNamesSet: set[str] = set()
	depGroupsTable: dict[str, Any] = mergedDictData["dependency-groups"]

	groupName: str
	groupList: Any
	for groupName, groupList in list(depGroupsTable.items()):
		if not isinstance(groupList, list):
			continue

		updatedGroupList: list[Any] = []
		groupItem: Any
		for groupItem in groupList:
			if isinstance(groupItem, str):
				tplBaseName: str = getBasePackageName(groupItem)
				if tplBaseName in userDepsByBaseName:
					migratedBaseNamesSet.add(tplBaseName)
					userDepText: str = userDepsByBaseName[tplBaseName]
					userOriginalBaseName: str = getBasePackageName(userDepText)

					if userOriginalBaseName in REPLACED_PACKAGES:
						logger.debug(
							"DECISION [%s in %s]: PACKAGE REPLACED (%s -> %s), FORCING TEMPLATE VERSION -> %r",
							tplBaseName,
							groupName,
							userOriginalBaseName,
							tplBaseName,
							groupItem,
						)
						updatedGroupList.append(groupItem)
						continue

					userMatch: re.Match[str] | None = re.search(r"([0-9]+(?:\.[0-9]+)+)", userDepText)
					tplMatch: re.Match[str] | None = re.search(r"([0-9]+(?:\.[0-9]+)+)", groupItem)

					if userMatch and tplMatch:
						try:
							userVersionTuple: tuple[int, ...] = tuple(map(int, userMatch.group(1).split(".")))
							tplVersionTuple: tuple[int, ...] = tuple(map(int, tplMatch.group(1).split(".")))

							if userVersionTuple > tplVersionTuple:
								logger.debug(
									"DECISION [%s in %s]: KEEP USER VERSION (%s > %s) -> %r",
									tplBaseName,
									groupName,
									userVersionTuple,
									tplVersionTuple,
									userDepText,
								)
								updatedGroupList.append(userDepText)
								continue
							else:
								logger.debug(
									"DECISION [%s in %s]: USE TEMPLATE VERSION (%s <= %s) -> %r",
									tplBaseName,
									groupName,
									userVersionTuple,
									tplVersionTuple,
									groupItem,
								)
						except ValueError:
							pass

					updatedGroupList.append(groupItem)
				else:
					updatedGroupList.append(groupItem)
			else:
				updatedGroupList.append(groupItem)

		depGroupsTable[groupName] = updatedGroupList

	if "project" in mergedDictData and "dependencies" in mergedDictData["project"]:
		projectDepsList: list[Any] = mergedDictData["project"]["dependencies"]
		filteredProjectDepsList: list[Any] = []
		for depItem in projectDepsList:
			if isinstance(depItem, str):
				baseName = getBasePackageName(depItem)
				canonicalBaseName = REPLACED_PACKAGES.get(baseName, baseName)
				if canonicalBaseName in migratedBaseNamesSet:
					logger.debug("Purging migrated dependency from flat list: %r", depItem)
					continue
			logger.debug("DECISION [custom]: PRESERVE USER DEPENDENCY IN PROJECT.DEPENDENCIES %r", depItem)
			filteredProjectDepsList.append(depItem)

		mergedDictData["project"]["dependencies"] = filteredProjectDepsList


def mergePyprojectToml(
	projFilePath: str | Path,
	tplFilePath: str | Path,
	metadataDict: dict[str, Any],
	dryRun: bool = False,
) -> str:
	"""Merge template pyproject.toml configuration into the developer's file.

	Handles package replacements (e.g. pre-commit -> prek), dependency-groups migration,
	and preserves custom add-on dependencies or higher versions.

	:param projFilePath: Path to the existing pyproject.toml file.
	:param tplFilePath: Path to the template pyproject.toml file.
	:param metadataDict: Dictionary containing legacy metadata values from buildVars.py.
	:param dryRun: If True, simulate the merge without writing changes to disk.
	:return: A string indicating the result of the merge operation.
	"""
	templatePathObj: Path = Path(tplFilePath)
	projectPathObj: Path = Path(projFilePath)

	if not templatePathObj.exists():
		return "skipped (no template found)"

	if not projectPathObj.exists():
		try:
			projTomlData: tomlkit.TOMLDocument = createPyprojectFromTemplate(templatePathObj, metadataDict)
			if not dryRun:
				tomlFormattedText: str = fixTomlIndentation(tomlkit.dumps(projTomlData))
				projectPathObj.parent.mkdir(parents=True, exist_ok=True)
				with projectPathObj.open("w", encoding="utf-8") as f:
					f.write(tomlFormattedText)
				logger.info("Created missing pyproject.toml at %s", projectPathObj)
			return "created from template"
		except Exception as exceptionObj:
			logger.error("Failed to create pyproject.toml: %s", exceptionObj)
			return f"failed to create from template ({str(exceptionObj)})"

	try:
		with projectPathObj.open("r", encoding="utf-8") as f:
			projTomlData = tomlkit.parse(f.read())
		with templatePathObj.open("r", encoding="utf-8") as f:
			tplTomlData: tomlkit.TOMLDocument = tomlkit.parse(f.read())

		userFlatDepsList: list[Any] = []
		if "project" in projTomlData and "dependencies" in projTomlData["project"]:
			userFlatDepsList = list(projTomlData["project"]["dependencies"])

		wasOriginallyNvaccess: bool = False
		if "project" in projTomlData:
			fieldName: str
			for fieldName in ["authors", "maintainers"]:
				if fieldName in projTomlData["project"] and isinstance(
					projTomlData["project"][fieldName], (list, MutableSequence)
				):
					authorItem: Any
					for authorItem in projTomlData["project"][fieldName]:
						authorName: Any = authorItem.get("name", "") if hasattr(authorItem, "get") else ""
						if not authorName and isinstance(authorItem, dict):
							authorName = authorItem.get("name", "")
						if str(authorName).strip().lower() in ["nv access", "nvaccess"]:
							wasOriginallyNvaccess = True
							break

		mergedDictData: dict[str, Any] = deepMergeDicts(
			cast(dict[str, Any], projTomlData), cast(dict[str, Any], tplTomlData)
		)

		processDependencyGroupsMigration(mergedDictData, userFlatDepsList)

		if "project" in mergedDictData:
			projectSectionDict: dict[str, Any] = mergedDictData["project"]

			if not wasOriginallyNvaccess:
				cleanupPlaceholderAuthors(projectSectionDict)

		finalDoc: tomlkit.TOMLDocument = tomlkit.document()
		sectionKey: str
		sectionVal: Any
		for sectionKey, sectionVal in mergedDictData.items():
			finalDoc[sectionKey] = sectionVal

		if "project" in finalDoc:
			projectTable: Any = finalDoc["project"]
			for fieldName in ["maintainers", "authors"]:
				if fieldName in projectTable and isinstance(projectTable[fieldName], list):
					rawAuthorsList: list[str] = []
					for authorEntry in projectTable[fieldName]:
						if isinstance(authorEntry, dict):
							nameText: str = authorEntry.get("name", "")
							emailText: str = authorEntry.get("email", "")
							rawAuthorsList.append(f"{nameText} <{emailText}>" if emailText else nameText)
					if rawAuthorsList:
						formattedVal: tomlkit.items.Array = formatAuthorList(", ".join(rawAuthorsList))
						if fieldName == "maintainers" and "description" in projectTable:
							insertKeyAfter(
								projectTable,
								targetKey="description",
								newKey="maintainers",
								value=formattedVal,
							)
						else:
							projectTable[fieldName] = formattedVal

		def makeMultilineArray(containerObj: Any, keyName: str) -> None:
			"""Force specified array attributes to multiline TOML layout with proper newline separation.

			:param containerObj: The container object holding the key.
			:param keyName: The key name within the container to convert.
			:return: None
			"""
			if keyName in containerObj and isinstance(containerObj[keyName], list):
				arrayObj: tomlkit.items.Array = tomlkit.array()
				arrayObj.multiline(True)
				for elementItem in containerObj[keyName]:
					if isinstance(elementItem, (dict, MutableMapping)):
						inlineTab: tomlkit.items.InlineTable = tomlkit.inline_table()
						inlineTab.update(dict(elementItem))
						arrayObj.append(inlineTab)
					else:
						arrayObj.append(elementItem)
				containerObj[keyName] = arrayObj

		if "project" in finalDoc:
			makeMultilineArray(finalDoc["project"], "classifiers")
			makeMultilineArray(finalDoc["project"], "dependencies")

		if "dependency-groups" in finalDoc:
			depGroupsSection: Any = finalDoc["dependency-groups"]
			groupKey: str
			for groupKey in depGroupsSection:
				makeMultilineArray(depGroupsSection, groupKey)

		if "tool" in finalDoc:
			toolSection: Any = finalDoc["tool"]
			if "ruff" in toolSection:
				makeMultilineArray(toolSection["ruff"], "builtins")
				makeMultilineArray(toolSection["ruff"], "include")
				makeMultilineArray(toolSection["ruff"], "exclude")
			if "pyright" in toolSection:
				makeMultilineArray(toolSection["pyright"], "include")
				makeMultilineArray(toolSection["pyright"], "exclude")
				makeMultilineArray(toolSection["pyright"], "extraPaths")

		if not dryRun:
			tomlFormattedText: str = fixTomlIndentation(tomlkit.dumps(finalDoc))
			with projectPathObj.open("w", encoding="utf-8") as f:
				f.write(tomlFormattedText)
		return "merged intelligently (tomlkit)"
	except Exception as exceptionObj:
		logger.error("Failed to merge pyproject.toml: %s", exceptionObj)
		return f"failed to merge ({str(exceptionObj)})"
