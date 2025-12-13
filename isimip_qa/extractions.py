import logging
from collections import defaultdict

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
from .utils import update_file_name

logger = logging.getLogger(__name__)


def create_extractions(datasets, periods, regions, aggregations):
    for dataset in datasets:
        # init extractions[region][period][aggregation] dict for this dataset
        extractions = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))

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
                                extractions[period.specifier][region.specifier]['value'] = (
                                    concat_extraction(
                                        extractions.get(period.specifier, {}).get(region.specifier, {}).get('value'),
                                        ds_region
                                    )
                                )
                                continue

                            # continue only if ds_region is not empty
                            if ds_region:
                                # loop over aggregations
                                for aggregation in aggregations:
                                    ds_aggregation = extract_aggregation(ds_region, aggregation)

                                    # concat extraction only if ds_aggregation is not empty
                                    if ds_aggregation:
                                        extractions[period.specifier][region.specifier][aggregation.specifier] = (
                                            concat_extraction(
                                                extractions.get(period.specifier, {})
                                                           .get(region.specifier, {})
                                                           .get(aggregation.specifier),
                                                ds_aggregation
                                            )
                                        )

        # write extraction ds for every region
        for period_specifier, period_extractions in extractions.items():
            for region_specifier, region_extractions in period_extractions.items():
                for aggregation_specifier, extraction in region_extractions.items():
                    extraction_path = (
                        settings.EXTRACTIONS_PATH /
                        update_file_name(
                            file.path, period_specifier, region_specifier, aggregation_specifier
                        ).relative_to(settings.DATASETS_PATH)
                    )

                    write_dataset(extraction, extraction_path)


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
