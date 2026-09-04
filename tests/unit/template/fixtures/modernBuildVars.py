# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Fixture file representing a modern buildVars.py without optional imports like SpeechDictionaries."""

from site_scons.site_tools.NVDATool.typings import (
	AddonInfo,
	BrailleTables,
	SymbolDictionaries,
)

addon_info = AddonInfo(
	addon_name="myAddon",
	addon_summary="My Test Addon",
)
