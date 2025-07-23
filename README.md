# Matsuzaki lab Python tools

[![DOI](https://zenodo.org/badge/1024604455.svg)](https://doi.org/10.5281/zenodo.16350118)

A set of python scripts for the ease of data transfer to MATLAB

## Tools for DeepLabCut

These tools are intended to be located inside each DeepLabCut project directory,
and used from there. Refer to the command-line reference by typing:

```bash
# assuming the DeepLabCut project directory
# to be the current directory
python <script_name>.py --help
```

- `convert.py`: recursively searches the specified directory and attempts to convert
  all the files that appear to be DeepLabCut output files.
