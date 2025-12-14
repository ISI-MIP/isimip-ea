import logging

from isimip_utils.extractions import (
    compute_spatial_average,
    compute_temporal_average,
    concat_extraction,
    count_values,
    mask_bbox,
    mask_mask,
    select_period,
    select_point,
    select_time,
)
from isimip_utils.xarray import create_mask, get_attrs, open_dataset, set_attrs, set_fill_value_to_nan, write_dataset

from .config import settings
from .utils import fetch_extraction, gather_extractions, get_extraction_path

logger = logging.getLogger(__name__)


def fetch_extractions(datasets, periods, regions, aggregations):
    if not settings.FORCE:
        for dataset in datasets:
            for extraction_path in gather_extractions(dataset, periods, regions, aggregations):
                if not (settings.EXTRACTIONS_PATH / extraction_path).exists():
                    fetch_extraction(extraction_path)


def create_extractions(datasets, periods, regions, aggregations):
    for dataset in datasets:
        # init extractions dict for this dataset
        extractions = {}

        # continue only if extractions are missing for this dataset
        if settings.FORCE or not all(
            (settings.EXTRACTIONS_PATH / extraction_path).exists()
            for extraction_path in gather_extractions(dataset, periods, regions, aggregations)
        ):
            for file in dataset.files:
                with open_dataset(file.path, decode_cf=False, load=settings.LOAD) as ds_file:
                    # loop over periods
                    for period in periods:
                        ds_period = extract_period(ds_file, period)

                        # continue only if at least one time step is selected (ds_period is not empty)
                        if ds_period:
                            # loop over regions
                            for region in regions:
                                ds_region = extract_region(ds_period, region)

                                # point extraction does not allow for additional aggregations
                                if region.type == 'point':
                                    extraction_path = get_extraction_path(dataset, period, region, 'value')
                                    extractions[extraction_path] = concat_extraction(
                                        extractions.get(extraction_path), ds_region
                                    )
                                    continue

                                # continue only if ds_region is not empty
                                if ds_region:
                                    # loop over aggregations
                                    for aggregation in aggregations:
                                        ds_aggregation = extract_aggregation(ds_region, aggregation)

                                        # concat extraction only if ds_aggregation is not empty
                                        if ds_aggregation:
                                            extraction_path = get_extraction_path(dataset, period, region, aggregation)
                                            extractions[extraction_path] = concat_extraction(
                                                extractions.get(extraction_path), ds_aggregation
                                            )

        # write extractions
        for extraction_path, extraction in extractions.items():
            write_dataset(extraction, settings.EXTRACTIONS_PATH / extraction_path)


def extract_period(ds, period):
    if period.type == 'auto':
        return ds

    elif period.type == 'period':
        return select_period(ds, period.start_time, period.end_time)

    elif period.type == 'date':
        return select_time(ds, period.time)

    else:
        logger.error(f'unknown type "{period.type}" for period "{period.specifier}"')


def extract_region(ds, region):
    if region.type == 'global':
        return ds

    elif region.type == 'bbox':
        return mask_bbox(ds, region.west, region.east, region.south, region.north)

    elif region.type == 'mask':
        return mask_mask(ds, region.mask_ds, region.mask_var)

    elif region.type == 'shape':
        mask = create_mask(ds, region.df, region.layer)
        return mask_mask(ds, mask)

    elif region.type == 'point':
        return select_point(ds, region.lat, region.lon)

    else:
        logger.error(f'unknown type "{region.type}" for region "{region.specifier}"')


def extract_aggregation(ds, aggregation):
    if aggregation.type == 'value':
        return ds

    elif aggregation.type == 'mean':
        attrs = get_attrs(ds)
        ds = set_fill_value_to_nan(ds)
        ds = compute_spatial_average(ds, weights=settings.WEIGHTS)
        ds = set_attrs(ds, attrs)
        return ds

    elif aggregation.type == 'count':
        attrs = get_attrs(ds)
        ds = set_fill_value_to_nan(ds)
        ds = count_values(ds)
        ds = set_attrs(ds, attrs)
        return ds

    elif aggregation.type == 'meanmap':
        attrs = get_attrs(ds)
        ds = set_fill_value_to_nan(ds)
        ds = compute_temporal_average(ds)
        ds = set_attrs(ds, attrs)
        return ds

    elif aggregation.type == 'countmap':
        attrs = get_attrs(ds)
        ds = set_fill_value_to_nan(ds)
        ds = count_values(ds, dim=('time', ))
        ds = set_attrs(ds, attrs)
        return ds

    else:
        logger.error(f'unknown type "{aggregation.type}" for aggregation "{aggregation.specifier}"')
