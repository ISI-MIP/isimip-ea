import logging
from collections import defaultdict

import numpy as np
from isimip_utils.pandas import compute_average, create_label, group_by_day, group_by_month, normalize
from isimip_utils.parameters import copy_placeholders, get_placeholders, join_parameters
from isimip_utils.plot import (
    check_plots,
    format_legend,
    format_title,
    plot_grid,
    plot_line,
    plot_map,
    save_index,
    save_plot,
)
from isimip_utils.xarray import open_dataset, to_dataframe

from .config import settings
from .models import Dataset, Extraction, Figure

logger = logging.getLogger(__name__)


def create_plots(periods, regions, aggregations, plots):
    logger.info('Creating plots')

    index_paths = defaultdict(list)

    for period in periods:
        for region in regions:
            for aggregation in aggregations:
                for plot in plots:
                    for path in settings.PATHS:
                        for figs_permutation in settings.FIGS_PERMUTATIONS:
                            figure_placeholders = copy_placeholders(
                                get_placeholders(settings.FIGS_PARAMETERS, figs_permutation),
                                join_parameters(settings.GRID_PARAMETERS, max_count=4),
                                join_parameters(settings.PLOT_PARAMETERS, max_count=4),
                            )

                            figure = Figure(path, figure_placeholders, period, region, aggregation, plot)

                            if settings.FORCE or not figure.exists():
                                charts = {}
                                chart_permutations = set()
                                for grid_permutation in settings.GRID_PERMUTATIONS:
                                    for plot_permutation in settings.PLOT_PERMUTATIONS:
                                        dataset_placeholders = copy_placeholders(
                                            get_placeholders(settings.FIGS_PARAMETERS, figs_permutation),
                                            get_placeholders(settings.GRID_PARAMETERS, grid_permutation),
                                            get_placeholders(settings.PLOT_PARAMETERS, plot_permutation),
                                        )
                                        dataset = Dataset(path, dataset_placeholders)

                                        extraction = Extraction(dataset, period, region, aggregation)
                                        if extraction.exists():
                                            with open_dataset(extraction.full_path) as ds:
                                                df = get_dataframe(ds, plot, plot_permutation)
                                                if df is not None:
                                                    chart = get_chart(df, plot, labels=plot_permutation)
                                                    charts[grid_permutation + plot_permutation] = chart
                                                    chart_permutations.add(plot_permutation)

                                if charts:
                                    empty_chart = get_chart(df, plot, empty=True)

                                    if check_plots(charts, figure.full_path):
                                        chart = plot_grid(
                                            settings.GRID_PERMUTATIONS,
                                            settings.PLOT_PERMUTATIONS,
                                            charts,
                                            empty_chart,
                                            **settings.PLOT_RESOLVE_SCALE,
                                        ).properties(
                                            title=get_title(figs_permutation, period, region, aggregation, plot)
                                        )

                                        chart = chart.configure_legend(**get_legend(chart, chart_permutations, plot))

                                        save_plot(chart, figure.full_path)

                                        index_paths[figure.full_path.parent].append(figure.full_path)

    if settings.PLOT_INDEX:
        for parent_path, paths in index_paths.items():
            save_index(parent_path, paths)


def get_dataframe(ds, plot, labels):
    try:
        df = to_dataframe(ds)
    except ValueError as e:
        logger.error(f'error converting dataset: "{e}"')
        return

    columns = set(df.attrs['coords'].keys())

    if plot.type == 'value':
        if columns.intersection(plot.columns):
            df = df.replace(0, np.nan)
            df = create_label(df, labels)
            return df
        else:
            logger.warn(f'incorrect columns {columns} for plot "{plot.specifier}"')

    elif plot.type == 'annual':
        if columns.intersection(plot.columns):
            df = compute_average(df, area=False)
            df = create_label(df, labels)
            return df
        else:
            logger.warn(f'incorrect columns {columns} for plot "{plot.specifier}"')

    elif plot.type == 'dayofyear':
        if columns.intersection(plot.columns):
            df = group_by_day(df)
            df = normalize(df)
            df = create_label(df, labels)
            return df
        else:
            logger.warn(f'incorrect columns {columns} for plot "{plot.specifier}"')

    elif plot.type == 'monthofyear':
        if columns.intersection(plot.columns):
            df = group_by_month(df)
            df = normalize(df)
            df = create_label(df, labels)
            return df
        else:
            logger.warn(f'incorrect columns {columns} for plot "{plot.specifier}"')

    elif plot.type == 'map':
        if columns.intersection(plot.columns):
            df = create_label(df, labels)
            return df
        else:
            logger.warn(f'incorrect columns {columns} for plot "{plot.specifier}"')

    else:
        logger.error(f'unknown type "{plot.type}" for plot "{plot.specifier}"')


def get_chart(df, plot, labels=None, **kwargs):
    kwargs = dict(legend=bool(labels), color_scheme=settings.COLOR_SCHEME, **kwargs)

    if settings.PRIMARY and labels:
        if set(settings.PRIMARY).intersection(set(labels)):
            kwargs.update(strokeWidth=3)
        else:
            kwargs.update(strokeWidth=0.5)

    if plot.type == 'value':
        return plot_line(df, y_format='.1e', **kwargs)

    elif plot.type == 'annual':
        return plot_line(df, x_type='Q', x_format='d', y_format='.1e', interpolate='step-after', **kwargs)

    elif plot.type == 'dayofyear':
        return plot_line(df, **kwargs)

    elif plot.type == 'monthofyear':
        return plot_line(df, **kwargs)

    elif plot.type == 'map':
        return plot_map(df, color_format='.1e', **kwargs)


def get_title(permutation, period, region, aggregation, plot):
    args = list(permutation)

    if period.type != 'auto':
        args.append(period.specifier)

    args.append(region.specifier)

    if aggregation.type != 'value':
        args.append(aggregation.specifier)

    if plot.type != 'value':
        args.append(plot.specifier)

    return format_title(' · '.join(args))


def get_legend(chart, chart_permutations, plot):
    kwargs = {}

    n_rows = len(chart.vconcat[0].hconcat)
    n_legend = len(chart_permutations)

    if plot.type == 'map':
        kwargs['direction'] = 'horizontal'

    if n_legend > 16 or n_rows > 4:
        kwargs['orient'] = 'bottom'
        kwargs['columns'] = min(n_legend // 8, n_rows)

    return format_legend(**kwargs)
