import logging
import re
from datetime import datetime

import pandas as pd

from isimip_utils.xarray import open_dataset

from .config import settings

logger = logging.getLogger(__name__)


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
