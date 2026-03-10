import logging
import re
from datetime import datetime

import pandas as pd
from isimip_utils.xarray import open_dataset

from .config import settings

logger = logging.getLogger(__name__)


def init_period(option):
    if re.match(r'\d{4}-\d{4}', option):
        left, right = option.split('-', 1)
        start_time, end_time = parse_date(left), parse_date(right, start=False)

        return {
            'type': 'period',
            'specifier': f'{start_time}_{end_time}',
            'start_time': start_time,
            'end_time': end_time
        }
    elif re.match(r'\d{4}', option):
        return {
            'type': 'date',
            'specifier': option,
            'time': parse_date(option)
        }

    # if region could not be determined, log error and return
    logger.error(f'could not determine type for period "{option}"')
    return {
        'type': 'unknown',
        'specifier': option
    }


def init_region(value):
    if settings.REGIONS_LOCATIONS:
        for location in settings.REGIONS_LOCATIONS:
            if not location.exists():
                raise RuntimeError(f'{location} does not exist.')

            if location.suffix in ['.json', '.csv']:
                if location.suffix == '.json':
                    df = pd.read_json(location)
                else:
                    df = pd.read_csv(location)

                row = find_row(df, value)
                if row:
                    if {'west', 'east', 'south', 'north'}.issubset(df.columns):
                        return {
                            'type': 'bbox',
                            'specifier': value,
                            'west': float(row['west']),
                            'east': float(row['east']),
                            'south': float(row['south']),
                            'north': float(row['north'])
                        }

                    if {'lat', 'lon'}.issubset(df.columns):
                        return {
                            'type': 'point',
                            'specifier': value,
                            'lat': float(row['lat']),
                            'lon': float(row['lon'])
                        }

            elif location.suffix == '.nc':
                ds = open_dataset(location, load=settings.LOAD)

                for mask_var in [value, f'm_{value}']:
                    if mask_var in ds.data_vars:
                        return {
                            'type': 'mask',
                            'specifier': value,
                            'mask_ds': ds,
                            'mask_var': mask_var
                        }

            elif location.suffix == '.zip' or location.suffix == '.shp':
                import geopandas
                df = geopandas.read_file(location)
                row = find_row(df, value)
                if row:
                    return {
                        'type': 'shape',
                        'specifier': f'layer-{value}' if value.isdigit() else value,
                        'df': df,
                        'layer': row.name
                    }

    # if region could not be determined, log error and return
    logger.warning(f'could not determine type for region "{value}"')
    return {
        'type': 'unknown',
        'specifier': value
    }


def find_row(df, value):
    if value.isdigit():
        rows = df.loc[df.index == int(value)]
    elif 'specifier' in df.columns:
        rows = df[df['specifier'] == value]
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


def update_path(path, period, region, aggregation, plot=None, start_year=None, end_year=None):
    stem = path.stem

    if aggregation.specifier == 'value':
        region_specifier = region.specifier
    else:
        region_specifier = f'{region.specifier}-{aggregation.specifier}'

    if '_global_' in stem:
        stem = stem.replace('_global_', f'_{region_specifier}_')
    else:
        stem = f'{stem}_{region_specifier}'

    if period.specifier != 'auto':
        stem = re.sub(r'(\d{4}_\d{4}|\d{4})', period.specifier, stem)

    if plot:
        stem += f'_{plot}'

    if start_year:
        stem += f'_{start_year}'

    if end_year:
        stem += f'_{end_year}'

    return path.with_stem(stem)
