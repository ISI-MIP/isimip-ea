import logging

from isimip_utils.extractions import (
    compute_aggregation,
    concat_extraction,
    count_values,
    mask_bbox,
    mask_mask,
    select_period,
    select_point,
    select_time,
)
from isimip_utils.xarray import create_mask, open_dataset, write_dataset

from .config import settings
from .models import Dataset, Extraction

logger = logging.getLogger(__name__)


def fetch_extractions(periods, regions, aggregations):
    logger.info('Fetching extractions')

    if not settings.FORCE:
        for dataset in Dataset.all():
            for extraction in Extraction.gather(dataset, periods, regions, aggregations):
                if not extraction.exists():
                    extraction.fetch()


def create_extractions(periods, regions, aggregations):
    logger.info('Creating extractions')

    for dataset in Dataset.all():
        # init extractions dict for this dataset
        extractions = {}

        # continue only if extractions are missing for this dataset
        if settings.FORCE or not all(
            extraction.exists() for extraction in Extraction.gather(dataset, periods, regions, aggregations)
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
                                    extraction = Extraction(dataset, period, region, 'value')
                                    extractions[extraction.path] = concat_extraction(
                                        extractions.get(extraction.path), ds_region
                                    )
                                    continue

                                # continue only if ds_region is not empty
                                if ds_region:
                                    # loop over aggregations
                                    for aggregation in aggregations:
                                        ds_aggregation = extract_aggregation(ds_region, aggregation)

                                        # concat extraction only if ds_aggregation is not empty
                                        if ds_aggregation:
                                            extraction = Extraction(dataset, period, region, aggregation)
                                            extractions[extraction.path] = concat_extraction(
                                                extractions.get(extraction.path), ds_aggregation
                                            )

        # write extractions
        for extraction_path, extraction_ds in extractions.items():
            write_dataset(extraction_ds, settings.EXTRACTIONS_PATH / extraction_path)


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

    elif aggregation.type in ('mean', 'std', 'sum', 'min', 'max'):
        return compute_aggregation(ds, aggregation.type, weights=settings.WEIGHTS)

    elif aggregation.type == 'count':
        return count_values(ds)

    elif aggregation.type == 'meanmap':
        return compute_aggregation(ds, 'mean', dim=('time', ))

    elif aggregation.type == 'countmap':
        return count_values(ds, dim=('time', ))

    else:
        logger.error(f'unknown type "{aggregation.type}" for aggregation "{aggregation.specifier}"')
