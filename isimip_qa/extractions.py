import logging
from collections import defaultdict

from isimip_utils.extractions import concat_extraction, select_period, select_point, select_time
from isimip_utils.xarray import open_dataset, write_dataset

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
                                extractions[region.specifier][period.specifier]['values'] = (
                                    concat_extraction(
                                        extractions.get(region.specifier, {}).get(period.specifier, {}).get('values'),
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
                                        extractions[region.specifier][period.specifier][aggregation.specifier] = (
                                            concat_extraction(
                                                extractions.get(region.specifier, {})
                                                           .get(period.specifier, {})
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
    elif region.type == 'mask':
        pass
    elif region.type == 'shape':
        pass
    elif region.type == 'point':
        return select_point(ds, region.lat, region.lon)
    else:
        logger.error(f'unknown type "{region.type}" for region "{region.specifier}"')


def extract_aggregation(ds, aggregation):
    if aggregation.type == 'value':
        return ds
    elif aggregation.type == 'count':
        pass
    elif aggregation.type == 'mean':
        pass
    else:
        logger.error(f'unknown type "{aggregation.type}" for aggregation "{aggregation.specifier}"')
        pass
