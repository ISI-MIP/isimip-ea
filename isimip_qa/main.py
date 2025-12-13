from isimip_utils.cli import ArgumentParser, parse_list, parse_locations, parse_path, setup_logs

from . import VERSION
from .cli import ArgumentAction
from .config import settings
from .extractions import create_extractions
from .models import Aggregation, Dataset, Period, Region
from .plots import create_plots
from .utils import gather_datasets


def main():
    parser = ArgumentParser(prog='isimip-qa')

    parser.add_argument('paths', nargs='*', action=ArgumentAction,
                        help='Paths of the datasets to process, can contain placeholders, e.g. {model}')
    parser.add_argument('placeholders', nargs='*', action=ArgumentAction,
                        help='Values for the placeholders in the from placeholder=value1,value2,...')

    parser.add_argument('--datasets-path', dest='datasets_path', type=parse_path,
                        help='Base path for the input datasets')
    parser.add_argument('--extractions-path', dest='extractions_path', type=parse_path,
                        help='Base path for the created extractions')
    parser.add_argument('--plots-path', dest='plots_path', type=parse_path,
                        help='Base path for the created plots')


    parser.add_argument('-p', '--periods', dest='periods', type=parse_list, default='auto',
                        help='Extract only specific periods (comma separated, format: YYYY, YYYYMMDD, '
                             'YYYY-YYYY, YYYYMMDD-YYYYMMDD)')
    parser.add_argument('-r', '--regions', dest='regions', type=parse_list, default='global',
                        help='Extract only specific regions (comma separated)')
    parser.add_argument('-a', '--aggregations', dest='aggregations', type=parse_list, default='value',
                        help='Perform aggregations when extracting (comma separated)')

    parser.add_argument('-f', '--force', dest='force', action='store_true', default=False,
                        help='Always run extractions')
    parser.add_argument('-l', '--load', dest='load', action='store_true', default=False,
                        help='Load NetCDF datasets completely in memory')

    parser.add_argument('--extractions-only', dest='extractions_only', action='store_true', default=False,
                        help='Only create extractions')
    parser.add_argument('--extractions-locations', dest='extractions_locations', type=parse_locations,
                        default='https://files.isimip.org/qa/extractions/',
                        help='URL or file path to the locations of extractions to fetch')
    parser.add_argument('--plots-only', dest='plots_only', action='store_true', default=False,
                        help='Only create plots')
    parser.add_argument('--plots-format', dest='plots_format', default='svg',
                        help='File format for plots [default: svg].')
    parser.add_argument('--primary', dest='primary', default=None,
                        help='Treat these placeholders as primary and plot them in color [default: all]')
    parser.add_argument('--gridarea', dest='gridarea', default=None,
                        help='Use a CDO gridarea file instead of computing the gridarea when computing means')
    parser.add_argument('--grid', type=int, dest='grid', default=0, choices=[0, 1, 2],
                        help='Number of dimensions of the plot grid [default: 0, i.e. no grid]')
    parser.add_argument('--figs', type=int, dest='figs', default=0,
                        help='Number of placeholders which generate separate figures [default: 0]')

    parser.add_argument('--ymin', type=float, dest='ymin', default=None,
                        help='Fixed minimal y value for plots.')
    parser.add_argument('--ymax', type=float, dest='ymax', default=None,
                        help='Fixed maximum y value for plots.')

    parser.add_argument('--vmin', type=float, dest='vmin', default=None,
                        help='Fixed minimal colormap value for maps.')
    parser.add_argument('--vmax', type=float, dest='vmax', default=None,
                        help='Fixed maximum colormap value for maps.')
    parser.add_argument('--cmap', dest='cmap', default='viridis',
                        help='Colormap to use for maps.')

    parser.add_argument('--row-ranges', dest='row_ranges', action='store_true', default=False,
                        help='Compute separate plot ranges for each row.')
    parser.add_argument('--column-ranges', dest='column_ranges', action='store_true', default=False,
                        help='Compute separate plot ranges for each column.')

    parser.add_argument('--protocol-location', dest='protocol_locations', type=parse_locations,
                        default='https://protocol.isimip.org https://protocol2.isimip.org',
                        help='URL or file path to the protocol')
    parser.add_argument('--regions-location', dest='regions_locations', type=parse_locations, default=[],
                        help='Use the provided files to create the regions.')
    parser.add_argument('--log-level', dest='log_level', default='WARN',
                        help='Log level (ERROR, WARN, INFO, or DEBUG)')
    parser.add_argument('--log-file', dest='log_file',
                        help='Path to the log file')
    parser.add_argument('-V', '--version', action='version', version=VERSION)

    args = parser.parse_args()

    setup_logs(log_level=args.log_level, log_file=args.log_file)

    settings.from_dict(vars(args))

    if not settings.PATHS:
        parser.error('You need to provide at least one path.')

    # create list of datasets
    datasets = [Dataset(path) for path in gather_datasets()]

    # create list of regions and periods
    regions = [Region(specifier) for specifier in settings.REGIONS]
    periods = [Period(specifier) for specifier in settings.PERIODS]
    aggregations = [Aggregation(specifier) for specifier in settings.AGGREGATIONS]

    # run the extractions
    if not settings.PLOTS_ONLY:
        create_extractions(datasets, periods, regions, aggregations)

    # create the plots
    if not settings.EXTRACTIONS_ONLY:
        create_plots(datasets, periods, regions, aggregations)
