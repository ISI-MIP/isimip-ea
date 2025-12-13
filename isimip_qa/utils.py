import logging
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from isimip_utils.utils import get_permutations, get_placeholders
from isimip_utils.xarray import open_dataset

from .config import settings

logger = logging.getLogger(__name__)


def gather_datasets():
    if settings.PLACEHOLDERS:
        datasets = []
        parameters = dict(settings.PLACEHOLDERS)
        placeholder_permutations = get_permutations(parameters)

        for input_path in settings.PATHS:
            for permutations in placeholder_permutations:
                placeholders = get_placeholders(parameters, permutations)

                try:
                    path_str = str(input_path).format(**placeholders)
                except KeyError as e:
                    raise RuntimeError('Some of the placeholders are missing.') from e

                path = Path(path_str)
                path = path.parent / path.name.lower()  # ensure that the name of the path is lower case
                datasets.append(path)

        return datasets
    else:
        for input_path in settings.PATHS:
            if re.search(r'\{.*\}', str(input_path)):
                raise RuntimeError('Some of the placeholders are missing.')

        return settings.PATHS


def gather_files(dataset_path):
    files = []

    abs_path = settings.DATASETS_PATH / dataset_path
    glob = sorted(abs_path.parent.glob(f'{abs_path.stem}*'))

    for index, file_path in enumerate(glob):
        first = (index == 0)
        last = (index == len(glob) - 1)
        files.append((file_path, index, first, last))

    return files


def init_period(specifier):
    if re.match(r'\d{4}_\d{4}', specifier):
        left, right = specifier.split('_', 1)
        start_time, end_time = parse_date(left), parse_date(right, start=False)

        return {
            'type': 'period',
            'specifier': specifier,
            'start_time': start_time,
            'end_time': end_time
        }
    elif re.match(r'\d{4}', specifier):
        return {
            'type': 'date',
            'specifier': specifier,
            'time': parse_date(specifier)
        }

    # if region could not be determined, log error and return
    logger.error(f'could not determine type for period "{specifier}"')
    return {
        'type': 'unknown',
        'specifier': specifier
    }


def init_region(specifier):
    for location in settings.REGIONS_LOCATIONS:
        if not location.exists():
            raise RuntimeError(f'{location} does not exist.')

        if location.suffix in ['.json', '.csv']:
            if location.suffix == '.json':
                df = pd.read_json(location)
            else:
                df = pd.read_csv(location)

            row = find_row(df, specifier)
            if row:
                if {'west', 'east', 'south', 'north'}.issubset(df.columns):
                    return {
                        'type': 'bbox',
                        'specifier': specifier,
                        'west': float(row['west']),
                        'east': float(row['east']),
                        'south': float(row['south']),
                        'north': float(row['north'])
                    }

                if {'lat', 'lon'}.issubset(df.columns):
                    return {
                        'type': 'point',
                        'specifier': specifier,
                        'lat': float(row['lat']),
                        'lon': float(row['lon'])
                    }

        elif location.suffix == '.nc':
            ds = open_dataset(location)

            for mask_var in [specifier, f'm_{specifier}']:
                if mask_var in ds.data_vars:
                    return {
                        'type': 'mask',
                        'specifier': specifier,
                        'mask_ds': ds,
                        'mask_var': mask_var
                    }

        elif location.suffix == '.zip' or location.suffix == '.shp':
            import geopandas
            df = geopandas.read_file(location)
            row = find_row(df, specifier)
            if row:
                return {
                    'type': 'shape',
                    'specifier': f'layer-{specifier}' if specifier.isdigit() else specifier,
                    'df': df,
                    'layer': row.name
                }

    # if region could not be determined, log error and return
    logger.error(f'could not determine type for region "{specifier}"')
    return {
        'type': 'unknown',
        'specifier': specifier
    }


    rows = pd.DataFrame()  # start with empty DataFrame

    if str(specifier).isdigit():
        rows = df.loc[df.index == int(specifier)]
    elif 'specifier' in df.columns:
        rows = df[df['specifier'] == specifier]

    if not rows.empty:
        return rows.iloc[0].to_dict()  # convert the row to a dictionary
    else:
        return None


def find_row(df, specifier):
    if specifier.isdigit():
        rows = df.loc[df.index == int(specifier)]
    elif 'specifier' in df.columns:
        rows = df[df['specifier'] == specifier]
    else:
        rows = pd.DataFrame()

    if not rows.empty:
        return rows.iloc[0].to_dict()


def parse_date(string, start=True):
    try:
        return datetime.strptime(string, "%Y")
    except ValueError:
        try:
            return datetime.strptime(string, "%Y%m%d")
        except ValueError as e:
            raise RuntimeError(f"Unrecognized date format: {string}") from e


def update_file_name(path, period_specifier, region_specifier, aggregation_specifier):
    stem = path.stem

    if aggregation_specifier != 'value':
        region_specifier = f'{region_specifier}-{aggregation_specifier}'

    if '_global_' in stem:
        stem = stem.replace('_global_', f'_{region_specifier}_')
    else:
        stem = f'{stem}_{region_specifier}'

    if period_specifier != 'auto':
        stem = re.sub(r'(\d{4}_\d{4}|\d{4})', period_specifier, stem)

    return path.with_stem(stem)
