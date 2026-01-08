# Copyright (C) 2020-2025 NV Access Limited, Noelia Ruiz Martínez
# This file may be used under the terms of the GNU General Public License, version 2 or later.
# For more details see: https://www.gnu.org/licenses/gpl-2.0.html

import argparse
import hashlib
import typing

#: The read size for each chunk read from the file, prevents memory overuse with large files.
BLOCK_SIZE = 65536


def sha256_checksum(binaryReadModeFiles: list[typing.BinaryIO], blockSize: int = BLOCK_SIZE):
	"""
	:param binaryReadModeFiles: A list of files (mode=='rb'). Calculate its sha256 hash.
	:param blockSize: The size of each read.
	:return: The Sha256 hex digest.
	"""
	sha256 = hashlib.sha256()
	for f in binaryReadModeFiles:
		with open(f, "rb") as file:
			assert file.readable() and file.mode == "rb"
			for block in iter(lambda: file.read(blockSize), b""):
				sha256.update(block)
	return sha256.hexdigest()


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument(
		type=argparse.FileType("rb"),
		dest="file",
		help="The NVDA addon (*.nvda-addon) to use when computing the sha256.",
	)
	args = parser.parse_args()
	checksum = sha256_checksum(args.file)
	print(f"Sha256:\t {checksum}")


if __name__ == "__main__":
	main()
