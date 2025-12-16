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

```plain
usage: isimip-qa [-h] [--datasets-path DATASETS_PATH] [--extractions-path EXTRACTIONS_PATH]
                 [--plots-path PLOTS_PATH] [-d DATES] [-r REGIONS] [-a AGGREGATIONS] [-p PLOTS]
                 [-f] [-l] [--fetch-only] [--extractions-only] [--plots-only] [--gridarea GRIDAREA]
                 [--plots-format PLOTS_FORMAT] [--primary PRIMARY] [--grid {0,1,2}] [--figs FIGS]
                 [--color-scheme COLOR_SCHEME] [--independent-x] [--independent-y] [--shared-color]
                 [--protocol-location PROTOCOL_LOCATIONS] [--regions-location REGIONS_LOCATIONS]
                 [--extractions-locations EXTRACTIONS_LOCATIONS] [--log-level LOG_LEVEL]
                 [--log-file LOG_FILE] [-V]
                 [paths ...] [placeholders ...]

positional arguments:
  paths                 Paths of the datasets to process, can contain placeholders, e.g. {model}
  placeholders          Values for the placeholders in the from placeholder=value1,value2,...

options:
  -h, --help            show this help message and exit
  --datasets-path DATASETS_PATH
                        Base path for the input datasets
  --extractions-path EXTRACTIONS_PATH
                        Base path for the created extractions
  --plots-path PLOTS_PATH
                        Base path for the created plots
  -d, --dates DATES     Extract only specific dates or periods (comma separated, format: YYYY,
                        YYYYMMDD, YYYY-YYYY, YYYYMMDD-YYYYMMDD)
  -r, --regions REGIONS
                        Extract only specific regions (comma separated, selected from --regions-
                        locations)
  -a, --aggregations AGGREGATIONS
                        Perform aggregations when extracting (comma separated: value, mean, count,
                        meanmap, countmap)
  -p, --plots PLOTS     Select specific plots (comma separated: value, annual, dayofyear,
                        monthofyear, map)
  -f, --force           Overwrite existing files
  -l, --load            Load NetCDF datasets in memory, useful for point extractions
  --fetch-only          Only fetch extractions
  --extractions-only    Only create extractions
  --plots-only          Only create plots
  --gridarea GRIDAREA   Use a CDO gridarea file instead of computing the gridarea when computing
                        means
  --plots-format PLOTS_FORMAT
                        File format for plots [default: svg].
  --primary PRIMARY     Treat these placeholders as primary and plot them in color [default: all]
  --grid {0,1,2}        Number of dimensions of the plot grid [default: 2, i.e. 2 dimensions]
  --figs FIGS           Number of placeholders which generate separate figures [default: 0]
  --color-scheme COLOR_SCHEME
                        Color scheme to use for plots [default: category20].
  --independent-x       Use independent x axis in plots
  --independent-y       Use independent y axis in plots
  --shared-color        Use shared color scale in plots
  --protocol-location PROTOCOL_LOCATIONS
                        URL or file path to the protocol
  --regions-location REGIONS_LOCATIONS
                        Use the provided files to create the regions.
  --extractions-locations EXTRACTIONS_LOCATIONS
                        URL or file path to the locations of extractions to fetch
  --log-level LOG_LEVEL
                        Log level (ERROR, WARN, INFO, or DEBUG)
  --log-file LOG_FILE   Path to the log file
  -V, --version         show program's version number and exit
```

The only mandatory argument is the path to an ISIMIP dataset, relative to the `DATASETS_PATH`, e.g.
`ISIMIP3b/OutputData/water_global/CWatM/gfdl-esm4/historical/cwatm_gfdl-esm4_w5e5_historical_histsoc_default_qtot_global_daily`.

It makes sense to set at least `DATASETS_PATH` (location the NetCDF input files), `EXTRACTIONS_PATH`
(location of the csv extractions), and `PLOTS_PATH` (location of the plots) to different directories,
either by command line options or by a config file (in `isimip.toml` in the same directory,
`~/.isimip.toml`, or `/etc/isimip.toml`):

```toml
[isimip-qa]
datasets_path = "~/data/isimip/qa/datasets"
extractions_path = "~/data/isimip/qa/extractions"
plots_path = "~/data/isimip/qa/plots"

log_level = "INFO"

protocol_locations = "~/code/isimip/isimip-protocol-3 ~/code/isimip/isimip-protocol-2"

# files with regions: points or bbox in json or csv, masks in NetCDF or shapefiles
regions_locations = """
    ~/data/isimip/qa/share/points.json
    ~/data/isimip/qa/share/bbox.csv
    ~/data/isimip/qa/share/mask.nc
    ~/data/isimip/qa/share/shape.shp
"""

# gridarea file created with `cdo gridarea`
gridarea = "~/data/isimip/qa/share/gridarea.nc"
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
