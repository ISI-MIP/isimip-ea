import logging

import numpy as np

from isimip_utils.pandas import compute_average, create_label, group_by_day, group_by_month, normalize
from isimip_utils.plot import get_plot_title, plot_grid, plot_line, plot_map, save_plot
from isimip_utils.utils import copy_placeholders, get_placeholders, join_parameters
from isimip_utils.xarray import open_dataset, to_dataframe

from .config import settings
from .models import Aggregation, Dataset, Extraction, Figure, Period, Plot, Region

logger = logging.getLogger(__name__)


def create_plots():
    logger.info('Creating plots')

    for period in Period.all():
        for region in Region.all():
            for aggregation in Aggregation.all():
                for plot in Plot.all():
                    for path in settings.PATHS:
                        for figs_permutation in settings.FIGS_PERMUTATIONS:
                            figure_placeholders = copy_placeholders(
                                get_placeholders(settings.FIGS_PARAMETERS, figs_permutation),
                                join_parameters(settings.GRID_PARAMETERS)
                            )
                            figure_title = get_plot_title(figs_permutation)
                            figure = Figure(path, figure_placeholders, plot)

                            if settings.FORCE or not figure.exists():
                                charts = {}
                                for grid_permutation in settings.GRID_PERMUTATIONS:
                                    dataset_placeholders = copy_placeholders(
                                        get_placeholders(settings.FIGS_PARAMETERS, figs_permutation),
                                        get_placeholders(settings.GRID_PARAMETERS, grid_permutation),
                                    )
                                    dataset = Dataset(path, dataset_placeholders)

                                    extraction = Extraction(dataset, period, region, aggregation)
                                    if extraction.exists():
                                        with open_dataset(extraction.abspath) as ds:
                                            df = get_dataframe(ds, plot, grid_permutation)
                                            if df is not None:
                                                chart = get_chart(df, plot, grid_permutation)
                                                charts[grid_permutation] = chart

                                if charts:
                                    empty_chart = get_chart(df, plot, grid_permutation, empty=True)

                                    chart = plot_grid(
                                        settings.GRID_PARAMETERS, charts, empty_chart,
                                        x='independent' if 'x' in settings.INDEPENDENT else 'shared',
                                        y='independent' if 'y' in settings.INDEPENDENT else 'shared',
                                        color='independent' # if 'color' in settings.INDEPENDENT else 'shared',
                                    ).properties(title=figure_title)

                                    save_plot(chart, figure.abspath)


def get_dataframe(ds, plot, grid_permutation):
    df = to_dataframe(ds)
    columns = set(df.attrs['coords'].keys())
    labels = grid_permutation[settings.GRID:]

    if plot.type == 'value':
        if columns.intersection(plot.columns):
            df.attrs['coords']['time']['long_name'] = 'Time'
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


def get_chart(df, plot, grid_permutation, empty=False):
    kwargs = {
        'empty': empty
    }
    if settings.PRIMARY and settings.PRIMARY not in grid_permutation:
        kwargs.update(strokeWidth=1)

    if plot.type == 'value':
        return plot_line(df, y_format='.1e', **kwargs)

    elif plot.type == 'annual':
        return plot_line(df, y_format='.1e', interpolate='step-after', **kwargs)

    elif plot.type == 'dayofyear':
        return plot_line(df, **kwargs)

    elif plot.type == 'monthofyear':
        return plot_line(df, interpolate='step', **kwargs)

    elif plot.type == 'map':
        return plot_map(df, color_format='.1e', **kwargs)
