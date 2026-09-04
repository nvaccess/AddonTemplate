# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""CLI entry point for the NVDA Add-on Template synchronization tool."""

from pathlib import Path
import sys

# Ensure the repository root directory is on sys.path so the `syncAddonTool`
# package can be properly resolved regardless of the execution mode.
PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from syncAddonTool.cli import main

if __name__ == "__main__":
    main()
