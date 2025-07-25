# MIT License
#
# Copyright (c) 2025 Keisuke Sehara
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from typing import Union, Optional
from typing_extensions import Self
from pathlib import Path
from collections import namedtuple
from dataclasses import dataclass
from enum import Enum
from argparse import ArgumentParser
from traceback import print_exc
import sys

import pandas as pd

PathLike = Union[str, Path]
DLC_OUTPUT_SUFFIX = '.h5'


class Status(Enum):
    SUCCESS = 0
    SKIPPED = -1
    FAILED = 1


class Result(
    namedtuple('Result', ('dstfile', 'status', 'message'))
):
    @classmethod
    def success(
        cls,
        dstfile: PathLike,
        message: Optional[str] = None,
    ) -> Self:
        return cls(str(dstfile), Status.SUCCESS, message)

    @classmethod
    def skipped(
        cls,
        dstfile: PathLike,
        message: str,
    ) -> Self:
        return cls(str(dstfile), Status.SKIPPED, message)

    @classmethod
    def failed(
        cls,
        dstfile: PathLike,
        message: str,
    ) -> Self:
        return cls(str(dstfile), Status.FAILED, message)

    def is_success(self) -> bool:
        return (self.status == Status.SUCCESS)

    def is_skipped(self) -> bool:
        return (self.status == Status.SKIPPED)

    def is_failed(self) -> bool:
        return (self.status == Status.FAILED)


@dataclass
class Conversion:
    srcfile: Path

    def __post_init__(self):
        self.srcfile = Path(self.srcfile)

    @property
    def dstfile(self) -> Path:
        raise NotImplementedError()

    def convert(
        self,
        tab: pd.DataFrame,
        dstfile: Path,
    ):
        raise NotImplementedError


@dataclass
class CSVConversion(Conversion):
    def __post_init__(self):
        super().__post_init__()

    @property
    def dstfile(self) -> Path:
        return self.srcfile.with_name(f"{self.srcfile.stem}.csv")

    def convert(
        self,
        tab: pd.DataFrame,
        dstfile: Path,
    ):
        tab.to_csv(dstfile, header=True, index=False)


FORMATS: dict[str, type[Conversion]] = {
    'csv': CSVConversion,
}


PARSER = ArgumentParser(
    description='searches for DeepLabCut output HDF5 files and converts them'
)
PARSER.add_argument(
    'directory',
    nargs='?',
    help='the directory to recursively search for HDF5 files from.',
)
PARSER.add_argument(
    '--fileformat', '-F',
    default='csv',
    help="the output file format. currently only supports 'csv'",
)
PARSER.add_argument(
    '--output-dir', '-D',
    default=None,
    dest='dstdir',
    help="the output directory to write the converted files to. defaults to the same directory as the original file.",
)
PARSER.add_argument(
    '--overwrite',
    action='store_true',
    help="tells the program to overwrite the data when the output file already exists.",
)


def is_DLC_output(
    filepath: Path,
) -> bool:
    if filepath.suffix != DLC_OUTPUT_SUFFIX:
        return False
    elif ('DLC_' not in filepath.name) and ('DeepLabCut_' not in filepath.name):
        return False
    elif ('shuffle' not in filepath.name):
        return False
    return True


def convert(
    srcfile: PathLike,
    fileformat: str = 'csv',
    dstdir: Optional[PathLike] = None,
    overwrite: bool = False,
) -> Result:
    """converts a single file based on the specified `fileformat`.
    the file format must have been registered to the `FORMATS` dictionary."""
    Converter = FORMATS.get(fileformat, None)
    if Converter is None:
        raise KeyError(f"file format not found: '{fileformat}'")
    conversion: Conversion = Converter(srcfile)
    dstfile = conversion.dstfile
    if dstdir is not None:
        dstfile = Path(dstdir) / dstfile.name
    try:
        if not dstfile.parent.exists():
            dstfile.parent.mkdir(parents=True)
        elif dstfile.exists() and (bool(overwrite) is False):
            return Result.skipped(dstfile, "the converted file already exists")
        tab = pd.read_hdf(srcfile)
        conversion.convert(tab, dstfile)
        return Result.success(dstfile)
    except Exception as e:
        print_exc(file=sys.stderr)
        return Result.failed(dstfile, f"failed to convert: {e}")


def convert_recursive(
    directory: Optional[PathLike] = None,
    fileformat: str = 'csv',
    dstdir: Optional[PathLike] = None,
    overwrite: bool = False,
):
    """searches the file tree recursively from `directory`, and
    converts all the files that appear to be DeepLabCut output files."""
    def _recurse_single(
        current: Path
    ):
        for child in current.iterdir():
            if child.is_dir():
                _recurse_single(child)
            elif is_DLC_output(child):
                result = convert(
                    child,
                    fileformat=fileformat,
                    dstdir=dstdir,
                    overwrite=overwrite,
                )
                if result.is_success():
                    print(child.name, file=sys.stdout, flush=True)
                else:
                    print(
                        f"***{result.message}: {child.name}",
                        file=sys.stderr,
                        flush=True,
                    )
            else:
                pass
    if directory is None:
        directory = Path()
    else:
        directory = Path(directory)
    _recurse_single(directory)


if __name__ == '__main__':
    args = vars(PARSER.parse_args())
    convert_recursive(**args)
