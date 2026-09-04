# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""Fixture file representing official AddonTemplate buildVars.py using AddonInfo class."""

from site_scons.site_tools.NVDATool.typings import (
	AddonInfo,
	BrailleTables,
	SpeechDictionaries,
	SymbolDictionaries,
)

addon_info = AddonInfo(
	addon_name="myAddon",
	addon_summary="My Test Addon",
	addon_version="1.0.0",
)
