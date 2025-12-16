# Copyright (C) 2024-2025 NV Access Limited, Noelia Ruiz Martínez
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

import os, sys, json
sys.path.insert(0, os.getcwd())
import buildVars, sha256


def main():
	addonId = buildVars.addon_info["addon_name"]
	readmeFile = os.path.join(os.getcwd(), "readme.md")
	i18nSources = sorted(buildVars.i18nSources)
	if os.path.isfile(readmeFile):
		readmeSha = sha256.sha256_checksum([readmeFile])
	i18nSourcesSha = sha256.sha256_checksum(i18nSources)
	hashFile = os.path.join(os.getcwd(), "hash.json")
	data = dict()
	if os.path.isfile(hashFile):
		with open(hashFile, "rt") as f:
			data = json.load(f)
		shouldUpdateMd = (data.get("readmeSha") != readmeSha and data.get("readmeSha") is not None) and os.path.isfile(readmeFile)
		shouldUpdatePot = (data.get("i18nSourcesSha") != i18nSourcesSha and data.get("i18nSourcesSha") is not None)
	data = dict()
	if readmeSha:
		data["readmeSha"] = readmeSha
	if i18nSourcesSha:
		data["i18nSourcesSha"] = i18nSourcesSha
	with open(hashFile, "wt", encoding="utf-8") as f:
		json.dump(data, f, indent="\t", ensure_ascii=False)
	name = 'addonId'
	value = addonId
	name0 = 'shouldUpdateMd'
	value0 = str(shouldUpdateMd).lower()
	name1 = 'shouldUpdatePot'
	value1 = str(shouldUpdatePot).lower()
	with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
		f.write(f"{name}={value}\n{name0}={value0}\n{name1}={value1}\n")


if __name__ == "__main__":
	main()