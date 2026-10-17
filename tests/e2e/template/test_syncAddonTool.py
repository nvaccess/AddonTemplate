# Copyright (C) 2026 NV Access Limited, Abdel
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

"""End-to-end test suite for syncAddonTool CLI execution, modes, options, packaging, and buildVars migrations."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

FIXTURES_DIR: Path = Path(__file__).parent / "fixtures"


class TestSyncAddonToolE2E(unittest.TestCase):
	"""Test cases for verifying syncAddonTool CLI interface, synchronization modes, options, PyInstaller packaging, and buildVars migrations."""

	def test_cli_help_output(self) -> None:
		"""Ensure the synchronization tool displays help instructions correctly via CLI using -h / --help."""
		helpFlag: str
		for helpFlag in ["--help", "-h"]:
			with self.subTest(flag=helpFlag):
				result: subprocess.CompletedProcess[str] = subprocess.run(
					[
						"uv",
						"run",
						"--no-project",
						"--with",
						"tomlkit",
						"python",
						"-m",
						"syncAddonTool",
						helpFlag,
					],
					capture_output=True,
					text=True,
					check=False,
				)
				self.assertEqual(result.returncode, 0)
				self.assertIn("--addon-dir", result.stdout)
				self.assertIn("--template-dir", result.stdout)
				self.assertIn("--dry-run", result.stdout)
				self.assertIn("--skip-backup", result.stdout)

	def test_standard_mode_run_inside_addon_directory(self) -> None:
		"""Test standard execution mode: running the tool directly from inside clipContentsDesigner root without -ad."""
		addonFixture: Path = FIXTURES_DIR / "clipContentsDesigner"
		if not addonFixture.exists():
			self.skipTest("Fixture clipContentsDesigner not found.")

		projectRoot: Path = Path(__file__).parents[3]
		toolPackageSrc: Path = projectRoot / "syncAddonTool"

		with tempfile.TemporaryDirectory() as tempDir:
			tempPath: Path = Path(tempDir)
			addonPath: Path = tempPath / "clipContentsDesigner"
			shutil.copytree(addonFixture, addonPath)

			# Embed syncAddonTool package inside the addon directory to allow standalone execution without -ad
			shutil.copytree(toolPackageSrc, addonPath / "syncAddonTool", dirs_exist_ok=True)

			result: subprocess.CompletedProcess[str] = subprocess.run(
				[
					"uv",
					"run",
					"--no-project",
					"--with",
					"tomlkit",
					"python",
					"-m",
					"syncAddonTool",
					"--dry-run",
				],
				cwd=str(addonPath),
				capture_output=True,
				text=True,
				check=False,
			)
			self.assertEqual(
				result.returncode,
				0,
				f"Standard mode failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
			)

			buildVarsFile: Path = addonPath / "buildVars.py"
			if buildVarsFile.exists():
				content: str = buildVarsFile.read_text(encoding="utf-8")
				self.assertIn("addon_name", content)

	def test_target_directory_mode_with_external_ad(self) -> None:
		"""Test target directory mode: running the tool specifying -ad for clipContentsDesigner from an external workspace."""
		addonFixture: Path = FIXTURES_DIR / "clipContentsDesigner"
		if not addonFixture.exists():
			self.skipTest("Fixture clipContentsDesigner not found.")

		projectRoot: Path = Path(__file__).parents[3]

		with tempfile.TemporaryDirectory() as tempDir:
			tempPath: Path = Path(tempDir)
			addonPath: Path = tempPath / "clipContentsDesigner"
			shutil.copytree(addonFixture, addonPath)

			result: subprocess.CompletedProcess[str] = subprocess.run(
				[
					"uv",
					"run",
					"--no-project",
					"--with",
					"tomlkit",
					"python",
					"-m",
					"syncAddonTool",
					"--dry-run",
					"-ad",
					str(addonPath),
				],
				cwd=str(projectRoot),
				capture_output=True,
				text=True,
				check=False,
			)
			self.assertEqual(
				result.returncode,
				0,
				f"External -ad mode failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
			)

			buildVarsFile: Path = addonPath / "buildVars.py"
			if buildVarsFile.exists():
				content: str = buildVarsFile.read_text(encoding="utf-8")
				self.assertIn("addon_name", content)

	def test_local_template_dir_with_td(self) -> None:
		"""Ensure the -td / --template-dir option successfully synchronizes using a local template reference."""
		templateFixture: Path = FIXTURES_DIR / "addonTemplate"
		addonFixture: Path = FIXTURES_DIR / "clipContentsDesigner"
		if not templateFixture.exists() or not addonFixture.exists():
			self.skipTest("Template or clipContentsDesigner add-on fixture not found.")

		with tempfile.TemporaryDirectory() as tempDir:
			tempPath: Path = Path(tempDir)
			addonPath: Path = tempPath / "clipContentsDesigner"
			templatePath: Path = tempPath / "localTemplate"
			shutil.copytree(addonFixture, addonPath)
			shutil.copytree(templateFixture, templatePath)

			result: subprocess.CompletedProcess[str] = subprocess.run(
				[
					"uv",
					"run",
					"--no-project",
					"--with",
					"tomlkit",
					"python",
					"-m",
					"syncAddonTool",
					"-ad",
					str(addonPath),
					"-td",
					str(templatePath),
				],
				capture_output=True,
				text=True,
				check=False,
			)
			self.assertEqual(result.returncode, 0)

	def test_dry_run_flag_dr(self) -> None:
		"""Ensure both --dry-run and short flag -dr simulate updates without altering files or creating backups."""
		addonFixture: Path = FIXTURES_DIR / "clipContentsDesigner"
		if not addonFixture.exists():
			self.skipTest("Fixture clipContentsDesigner not found.")

		dryRunFlag: str
		for dryRunFlag in ["--dry-run", "-dr"]:
			with self.subTest(flag=dryRunFlag):
				with tempfile.TemporaryDirectory() as tempDir:
					tempPath: Path = Path(tempDir)
					addonPath: Path = tempPath / "clipContentsDesigner"
					shutil.copytree(addonFixture, addonPath)

					result: subprocess.CompletedProcess[str] = subprocess.run(
						[
							"uv",
							"run",
							"--no-project",
							"--with",
							"tomlkit",
							"python",
							"-m",
							"syncAddonTool",
							dryRunFlag,
							"-ad",
							str(addonPath),
						],
						capture_output=True,
						text=True,
						check=False,
					)
					self.assertEqual(result.returncode, 0)
					backups: list[Path] = list(addonPath.parent.glob("*_bak_*"))
					self.assertEqual(len(backups), 0)

	def test_skip_backup_flag_s(self) -> None:
		"""Ensure both --skip-backup and short flag -s prevent the creation of a timestamped backup directory."""
		templateFixture: Path = FIXTURES_DIR / "addonTemplate"
		addonFixture: Path = FIXTURES_DIR / "clipContentsDesigner"
		if not templateFixture.exists() or not addonFixture.exists():
			self.skipTest("Template or clipContentsDesigner add-on fixture not found.")

		skipBackupFlag: str
		for skipBackupFlag in ["--skip-backup", "-s"]:
			with self.subTest(flag=skipBackupFlag):
				with tempfile.TemporaryDirectory() as tempDir:
					tempPath: Path = Path(tempDir)
					addonPath: Path = tempPath / "clipContentsDesigner"
					templatePath: Path = tempPath / "localTemplate"
					shutil.copytree(addonFixture, addonPath)
					shutil.copytree(templateFixture, templatePath)

					result: subprocess.CompletedProcess[str] = subprocess.run(
						[
							"uv",
							"run",
							"--no-project",
							"--with",
							"tomlkit",
							"python",
							"-m",
							"syncAddonTool",
							"-ad",
							str(addonPath),
							"-td",
							str(templatePath),
							skipBackupFlag,
						],
						capture_output=True,
						text=True,
						check=False,
					)
					self.assertEqual(result.returncode, 0)
					backups: list[Path] = list(addonPath.parent.glob("*_bak_*"))
					self.assertEqual(len(backups), 0, f"Expected no backup directory when {skipBackupFlag} is passed")

	def test_verbose_logging_flag_v(self) -> None:
		"""Ensure both --verbose and short flag -v enable detailed debug logging in console output."""
		addonFixture: Path = FIXTURES_DIR / "clipContentsDesigner"
		if not addonFixture.exists():
			self.skipTest("Fixture clipContentsDesigner not found.")

		verboseFlag: str
		for verboseFlag in ["--verbose", "-v"]:
			with self.subTest(flag=verboseFlag):
				with tempfile.TemporaryDirectory() as tempDir:
					tempPath: Path = Path(tempDir)
					addonPath: Path = tempPath / "clipContentsDesigner"
					shutil.copytree(addonFixture, addonPath)

					result: subprocess.CompletedProcess[str] = subprocess.run(
						[
							"uv",
							"run",
							"--no-project",
							"--with",
							"tomlkit",
							"python",
							"-m",
							"syncAddonTool",
							"--dry-run",
							verboseFlag,
							"-ad",
							str(addonPath),
						],
						capture_output=True,
						text=True,
						check=False,
					)
					self.assertEqual(result.returncode, 0)
					combinedOutput: str = result.stdout + result.stderr
					self.assertIn("DEBUG", combinedOutput)

	def test_e2e_legacy_buildvars_migration(self) -> None:
		"""Ensure legacy buildVars.py from dayOfTheWeek-legacy fixture is correctly merged via CLI execution."""
		legacyFixture: Path = FIXTURES_DIR / "dayOfTheWeek-legacy"
		templateFixture: Path = FIXTURES_DIR / "addonTemplate"
		if not legacyFixture.exists() or not templateFixture.exists():
			self.skipTest("Fixture dayOfTheWeek-legacy or addonTemplate not found.")

		with tempfile.TemporaryDirectory() as tempDir:
			tempPath: Path = Path(tempDir)
			addonPath: Path = tempPath / "dayOfTheWeek"
			templatePath: Path = tempPath / "localTemplate"
			shutil.copytree(legacyFixture, addonPath)
			shutil.copytree(templateFixture, templatePath)

			result: subprocess.CompletedProcess[str] = subprocess.run(
				[
					"uv",
					"run",
					"--no-project",
					"--with",
					"tomlkit",
					"python",
					"-m",
					"syncAddonTool",
					"-ad",
					str(addonPath),
					"-td",
					str(templatePath),
				],
				capture_output=True,
				text=True,
				check=False,
			)
			self.assertEqual(
				result.returncode,
				0,
				f"Legacy buildVars migration E2E failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
			)

			projBvPath: Path = addonPath / "buildVars.py"
			self.assertTrue(projBvPath.exists())
			content: str = projBvPath.read_text(encoding="utf-8")
			self.assertIn("addon_name", content)
			self.assertIn("addon_version", content)

	def test_e2e_modern_buildvars_speech_dictionaries(self) -> None:
		"""Ensure modern buildVars.py from placeMarkers-modern fixture gets missing speechDictionaries injected via CLI."""
		modernFixture: Path = FIXTURES_DIR / "placeMarkers-modern"
		templateFixture: Path = FIXTURES_DIR / "addonTemplate"
		if not modernFixture.exists() or not templateFixture.exists():
			self.skipTest("Fixture placeMarkers-modern or addonTemplate not found.")

		with tempfile.TemporaryDirectory() as tempDir:
			tempPath: Path = Path(tempDir)
			addonPath: Path = tempPath / "placeMarkers"
			templatePath: Path = tempPath / "localTemplate"
			shutil.copytree(modernFixture, addonPath)
			shutil.copytree(templateFixture, templatePath)

			result: subprocess.CompletedProcess[str] = subprocess.run(
				[
					"uv",
					"run",
					"--no-project",
					"--with",
					"tomlkit",
					"python",
					"-m",
					"syncAddonTool",
					"-ad",
					str(addonPath),
					"-td",
					str(templatePath),
				],
				capture_output=True,
				text=True,
				check=False,
			)
			self.assertEqual(
				result.returncode,
				0,
				f"Modern buildVars speechDictionaries E2E failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
			)

			projBvPath: Path = addonPath / "buildVars.py"
			self.assertTrue(projBvPath.exists())
			content: str = projBvPath.read_text(encoding="utf-8")
			self.assertIn("SpeechDictionaries", content)

	def test_pyinstaller_executable_build(self) -> None:
		"""Verify that the standalone executable can be successfully built using PyInstaller and uv."""
		specPath: Path = Path("syncAddonTool/syncAddonTool.spec")
		if not specPath.exists():
			self.skipTest("syncAddonTool/syncAddonTool.spec not found in repository.")

		# Keep packaging outputs separate from existing developer artifacts.
		tempDirObj: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory()
		self.addCleanup(tempDirObj.cleanup)
		tempPath: Path = Path(tempDirObj.name)

		result: subprocess.CompletedProcess[str] = subprocess.run(
			[
				"uv",
				"run",
				"--with",
				"pyinstaller",
				"pyinstaller",
				"syncAddonTool/syncAddonTool.spec",
				"--noconfirm",
				"--workpath",
				str(tempPath / "build"),
				"--distpath",
				str(tempPath / "dist"),
			],
			capture_output=True,
			text=True,
			check=False,
		)
		self.assertEqual(result.returncode, 0, f"PyInstaller build failed: {result.stderr}")

		expectedExe: Path = tempPath / "dist" / "syncAddonTool.exe"
		self.assertTrue(expectedExe.exists(), f"Expected {expectedExe} to be generated")


if __name__ == "__main__":
	unittest.main()
