ISIMIP quality assessment
=========================

[![Python Version](https://img.shields.io/badge/python->=3.8-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://github.com/ISI-MIP/isimip-qc/blob/master/LICENSE)

A command line tool to for quality assessment within the ISIMIP project.

Using ISIMIP datasets in NetCDF format as input, the tool creates (a) extractions of the data as CSV
files using predefined regions or points, and (b) creates plots to assess the data from these regions.

**This is still work in progress.**


Setup
-----

The application is written in Python (>= 3.10) uses only dependencies, which can be installed
without administrator privileges. The installation of Python (and its developing packages), however
differs from operating system to operating system. Optional Git is needed if the application is installed
directly from GitHub. The installation of Python 3 and Git for different platforms is documented
[here](https://github.com/ISI-MIP/isimip-utils/blob/master/docs/prerequisites.md).

The tool itself can be installed via pip. Usually you want to create a
[virtual environment](https://docs.python.org/3/library/venv.html) first, but this is optional.

```bash
# setup venv on Linux/macOS/Windows WSL
python3 -m venv env
source env/bin/activate

# setup venv on Windows cmd
python -m venv env
call env\Scripts\activate.bat

# install directly from GitHub
pip install git+https://github.com/ISI-MIP/isimip-qa

# update from Github
pip install --upgrade git+https://github.com/ISI-MIP/isimip-qa
```

Usage
-----

The tool has several options which can be inspected using the help option `-h, --help`:

```bash
usage:
```

The only mandatory argument is the path to an ISIMIP dataset, relative to the `DATASETS_PATH`, e.g.
`ISIMIP3b/OutputData/water_global/CWatM/gfdl-esm4/historical/cwatm_gfdl-esm4_w5e5_historical_histsoc_default_qtot_global_daily`.

It makes sense to set at least `DATASETS_PATH` (location the NetCDF input files), `EXTRACTIONS_PATH`
(location of the csv extractions), and `PLOTS_PATH` (location of the plots) to different directories,
either by command line options or by a config file (in `isimip.toml` in the same directory,
`~/.isimip.toml`, or `/etc/isimip.toml`):

```
[isimip-qa]
datasets_path = "~/data/isimip/qa/datasets"
extractions_path = "~/data/isimip/qa/extractions"
plots_path = "~/data/isimip/qa/plots"

log_level = "INFO"
```

All other command line options can be set in the config file as well.

Datasets can be parametrized by the syntax:

```
isimip-qc path/to/dataset_with_{placeholder}.nc placeholder=value1,value2,...
```

E.g.

```
ISIMIP3b/OutputData/water_global/{model}/gfdl-esm4/historical/{model}_gfdl-esm4_w5e5_historical_histsoc_default_qtot_global_daily model=CWatM,H08
```

would process

```
ISIMIP3b/OutputData/water_global/CWatM/gfdl-esm4/historical/cwatm_gfdl-esm4_w5e5_historical_histsoc_default_qtot_global_daily
ISIMIP3b/OutputData/water_global/H08/gfdl-esm4/historical/h08_gfdl-esm4_w5e5_historical_histsoc_default_qtot_global_daily
```

Multiple identifier/specifier combinations can be used to create a grid of combinations.
