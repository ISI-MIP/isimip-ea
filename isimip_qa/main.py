from isimip_utils.cli import ArgumentParser, parse_list, parse_locations, parse_path, setup_logs

from . import VERSION
from .cli import ArgumentAction
from .config import settings
from .extractions import create_extractions, fetch_extractions
from .models import Aggregation, Period, Plot, Region
from .plots import create_plots


def main():
    parser = ArgumentParser(prog='isimip-qa')

    parser.add_argument('-c', '--config', dest='config_path', type=parse_path,
                        help='Path to an additional config file, updating default and CLI arguments and options.')

    config_args, remaining_args = parser.parse_known_args()

    parser.add_argument('paths', nargs='*', action=ArgumentAction,
                        help='Paths of the datasets to process, can contain placeholders, e.g. {model}')
    parser.add_argument('parameters', nargs='*', action=ArgumentAction,
                        help='Values for the placeholders in the from key=value1,value2,...')

    parser.add_argument('--datasets-path', dest='datasets_path', type=parse_path,
                        help='Base path for the input datasets')
    parser.add_argument('--extractions-path', dest='extractions_path', type=parse_path,
                        help='Base path for the created extractions')
    parser.add_argument('--plots-path', dest='plots_path', type=parse_path,
                        help='Base path for the created plots')

    parser.add_argument('-d', '--dates', dest='dates', type=parse_list, default='auto',
                        help='Extract only specific dates or periods (comma separated, format: YYYY, YYYYMMDD, '
                             'YYYY-YYYY, YYYYMMDD-YYYYMMDD)')
    parser.add_argument('-r', '--regions', dest='regions', type=parse_list, default='global',
                        help='Extract only specific regions (comma separated, automatically selected '
                             'from --regions-locations)')
    parser.add_argument('-a', '--aggregations', dest='aggregations', type=parse_list, default='mean',
                        help='Perform aggregations when extracting (comma separated: value, mean, count, '
                             'meanmap, countmap)')
    parser.add_argument('-p', '--plots', dest='plots', type=parse_list, default='annual',
                        help='Select specific plots (comma separated: value, annual, dayofyear, monthofyear, map)')

    parser.add_argument('-f', '--force', dest='force', action='store_true', default=False,
                        help='Overwrite existing files')
    parser.add_argument('-l', '--load', dest='load', action='store_true', default=False,
                        help='Load NetCDF datasets in memory, useful for point extractions')

    parser.add_argument('--fetch-only', dest='fetch_only', action='store_true', default=False,
                        help='Only fetch extractions')
    parser.add_argument('--extractions-only', dest='extractions_only', action='store_true', default=False,
                        help='Only create extractions')
    parser.add_argument('--plots-only', dest='plots_only', action='store_true', default=False,
                        help='Only create plots')

    parser.add_argument('--gridarea', dest='gridarea', type=parse_path,
                        help='Use a CDO gridarea file instead of computing the gridarea when computing means')

    parser.add_argument('--plot-format', dest='plot_format', default='svg',
                        help='File format for plots [default: svg].')
    parser.add_argument('--plot-index', dest='plot_index', default=True,
                        help='Create an index.html file when creating plots.')
    parser.add_argument('--primary', dest='primary',
                        help='Treat these placeholders as primary and plot them in color [default: all]')
    parser.add_argument('--grid', dest='grid', type=parse_list, default="",
                        help='Parameters which are used as dimensions of the plot grid.')
    parser.add_argument('--figs', dest='figs', type=parse_list, default="",
                        help='Parameters for which separate figures are created')
    parser.add_argument('--color-scheme', dest='color_scheme', default='category20',
                        help='Color scheme to use for plots [default: category20].')

    parser.add_argument('--independent-x', dest='independent_x', action='store_true', default=False,
                        help='Use independent x axis in plots')
    parser.add_argument('--independent-y', dest='independent_y', action='store_true', default=False,
                        help='Use independent y axis in plots')
    parser.add_argument('--shared-color', dest='shared_color', action='store_true', default=False,
                        help='Use shared color scale in plots')

    parser.add_argument('--protocol-location', dest='protocol_locations', type=parse_locations,
                        default='https://protocol.isimip.org https://protocol2.isimip.org',
                        help='URL or file path to the protocol')
    parser.add_argument('--regions-location', dest='regions_locations', type=parse_locations,
                        help='Use the provided files to create the regions.')
    parser.add_argument('--extractions-locations', dest='extractions_locations', type=parse_locations,
                        default='https://files.isimip.org/qa/extractions/',
                        help='URL or file path to the locations of extractions to fetch')

    parser.add_argument('--log-level', dest='log_level', default='WARN',
                        help='Log level (ERROR, WARN, INFO, or DEBUG)')
    parser.add_argument('--log-file', dest='log_file',
                        help='Path to the log file')
    parser.add_argument('-V', '--version', action='version', version=VERSION)

    args = parser.parse_args(remaining_args, config_path=config_args.config_path)

    setup_logs(log_level=args.log_level, log_file=args.log_file)

    settings.from_dict(vars(args))

    if not settings.PATHS:
        parser.error('You need to provide at least one path.')

    periods = [Period(value) for value in settings.DATES]
    regions = [Region(specifier) for specifier in settings.REGIONS]
    aggregations = [Aggregation(value) for value in settings.AGGREGATIONS]
    plots = [Plot(value) for value in settings.PLOTS]

    # fetch extractions
    if not settings.EXTRACTIONS_ONLY and not settings.PLOTS_ONLY:
        fetch_extractions(periods, regions, aggregations)

    # create the extractions
    if not settings.FETCH_ONLY and not settings.PLOTS_ONLY:
        create_extractions(periods, regions, aggregations)

    # create the plots
    if not settings.FETCH_ONLY and not settings.EXTRACTIONS_ONLY:
        create_plots(periods, regions, aggregations, plots)
