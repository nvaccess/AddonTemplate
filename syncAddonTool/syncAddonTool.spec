# -*- mode: python ; coding: utf-8 -*-
# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""PyInstaller specification file for syncAddonTool standalone executable."""

from pathlib import Path
from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.win32.versioninfo import (
	FixedFileInfo,
	StringFileInfo,
	StringStruct,
	StringTable,
	VarFileInfo,
	VarStruct,
	VSVersionInfo,
)

# SPECPATH is automatically injected by PyInstaller during spec file execution
ROOT_DIR = Path(SPECPATH).resolve()

# -----------------------------------------------------------------------------
# Executable Metadata Configuration (Windows File Properties / Screen Reader)
# -----------------------------------------------------------------------------
version_info = VSVersionInfo(
	ffi=FixedFileInfo(
		filevers=(1, 0, 0, 0),
		prodvers=(1, 0, 0, 0),
		mask=0x3F,
		flags=0x0,
		OS=0x40004,  # VOS_NT_WINDOWS32
		fileType=0x1,  # VFT_APP
		subtype=0x0,
		date=(0, 0),
	),
	kids=[
		StringFileInfo(
			[
				StringTable(
					"040904b0",  # Unicode / US English
					[
						StringStruct("CompanyName", "NV Access Limited, Abdel"),
						StringStruct(
							"FileDescription",
							"NVDA Add-on Template Synchronization Tool",
						),
						StringStruct("FileVersion", "1.0.0.0"),
						StringStruct("InternalName", "syncAddonTool"),
						StringStruct(
							"LegalCopyright",
							"Copyright (C) 2026 NV Access Limited, Abdel",
						),
						StringStruct("OriginalFilename", "syncAddonTool.exe"),
						StringStruct("ProductName", "syncAddonTool"),
						StringStruct("ProductVersion", "1.0.0.0"),
					],
				)
			]
		),
		VarFileInfo([VarStruct("Translation", [1033, 1200])]),
	],
)

# Generate temporary text version file expected by PyInstaller
VERSION_FILE_PATH = ROOT_DIR / "build" / "version_info.txt"
VERSION_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
VERSION_FILE_PATH.write_text(str(version_info), encoding="utf-8")

# -----------------------------------------------------------------------------
# PyInstaller Analysis and Collection
# -----------------------------------------------------------------------------
a = Analysis(
	["__main__.py"],
	pathex=[str(ROOT_DIR)],
	binaries=[],
	datas=[],
	hiddenimports=[
		"syncAddonTool",
		"syncAddonTool.engine",
		"syncAddonTool.buildVarsSync",
		"syncAddonTool.pyproject",
		"tomlkit",
		"pathspec",
	],
	hookspath=[],
	hooksconfig={},
	runtime_hooks=[],
	excludes=[],
	noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
	pyz,
	a.scripts,
	a.binaries,
	a.datas,
	[],
	name="syncAddonTool",
	debug=False,
	bootloader_ignore_signals=False,
	strip=False,
	upx=True,
	upx_exclude=[],
	runtime_tmpdir=None,
	console=True,
	disable_windowed_traceback=False,
	argv_emulation=False,
	target_arch=None,
	codesign_identity=None,
	entitlements_file=None,
	version=str(VERSION_FILE_PATH),
)
