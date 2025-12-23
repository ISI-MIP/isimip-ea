import logging
import re
from pathlib import Path

from isimip_utils.fetch import fetch_file, load_file
from isimip_utils.parameters import (
    apply_placeholders,
    copy_placeholders,
    get_permutations,
    get_placeholders,
)
from isimip_utils.utils import cached_property

from .config import settings
from .utils import init_period, init_region, update_path

logger = logging.getLogger(__name__)


class Dataset:

    def __init__(self, path_template, placeholders):
        self.path = apply_placeholders(path_template, placeholders)
        self.path_template = path_template
        self.placeholders = placeholders

    def  __repr__(self):
        return str(self.path)

    @cached_property
    def files(self):
        files = []

        abs_path = settings.DATASETS_PATH / self.path
        glob = sorted(abs_path.parent.glob(f'{abs_path.stem}*'))

        for index, file_path in enumerate(glob):
            first = (index == 0)
            last = (index == len(glob) - 1)

            m = re.search(r'_(\d{4})_*(\d{4})?$', file_path.stem)
            if m:
                try:
                    start_year = int(m.group(1))
                except TypeError:
                    start_year = None

                try:
                    end_year = int(m.group(2))
                except TypeError:
                    end_year = None
            else:
                start_year = end_year = None

            files.append(File(file_path, index, first, last, start_year, end_year))

        return files

    @cached_property
    def start_year(self):
        return min([file.start_year for file in self.files if file.start_year], default=None)

    @cached_property
    def end_year(self):
        return max([file.end_year for file in self.files if file.end_year], default=None)

    def exists(self):
        return bool(self.files)

    @classmethod
    def all(cls):
        datasets = []

        if settings.PARAMETERS:
            placeholder_permutations = get_permutations(settings.PARAMETERS)

            for path in settings.PATHS:
                for permutations in placeholder_permutations:
                    placeholders = get_placeholders(settings.PARAMETERS, permutations)
                    datasets.append(cls(path, placeholders))

            return datasets
        else:
            for path in settings.PATHS:
                if re.search(r'\{.*\}', str(path)):
                    raise RuntimeError('Some of the placeholders are missing.')
                datasets.append(cls(path, {}))

        return datasets


class File:

    def __init__(self, path, index, first, last, start_year, end_year):
        self.path = path
        self.index = index
        self.first = first
        self.last = last
        self.start_year = start_year
        self.end_year = end_year

    def  __repr__(self):
        return str(self.path)


class Extraction:

    def __init__(self, dataset, period, region, aggregation):
        self.dataset = dataset
        self.period = period
        self.region = region
        self.aggregation = aggregation

    def  __repr__(self):
        return str(self.path)

    @cached_property
    def path(self):
        path = update_path(
            self.dataset.path, self.period, self.region, self.aggregation,
            start_year=self.dataset.start_year, end_year=self.dataset.end_year
        )
        return path.with_suffix('.nc')

    @cached_property
    def abspath(self):
        return settings.EXTRACTIONS_PATH / self.path

    def exists(self):
        return self.abspath.exists()

    def fetch(self):
        for location in settings.EXTRACTIONS_LOCATIONS:
            if isinstance(location, Path):
                result = load_file(location / self.path, self.abspath)
            else:
                result = fetch_file(f'{location}/{self.path}', self.abspath)

            if result:
                logger.info(f'Extraction "{self.path}" downloaded')
                return

    @classmethod
    def gather(cls, dataset, periods, regions, aggregations):
        return [
            cls(dataset, period, region, aggregation)
            for period in periods
            for region in regions
            for aggregation in aggregations
        ]


class Figure:

    def __init__(self, path_template, placeholders, period, region, aggregation, plot):
        self.path_template = path_template
        self.placeholders = placeholders
        self.period = period
        self.region = region
        self.aggregation = aggregation
        self.plot = plot

    def  __repr__(self):
        return str(self.path)

    @cached_property
    def path(self):
        path = update_path(
            apply_placeholders(self.path_template, self.placeholders),
            self.period, self.region, self.aggregation, self.plot,
            start_year=self.start_year, end_year=self.end_year
        )
        return path.with_suffix(f'.{settings.PLOTS_FORMAT}')

    @cached_property
    def start_year(self):
        return min([dataset.start_year for dataset in self.datasets if dataset.start_year], default=None)

    @cached_property
    def end_year(self):
        return max([dataset.end_year for dataset in self.datasets if dataset.end_year], default=None)

    @cached_property
    def datasets(self):
        datasets = []
        for grid_permutation in settings.GRID_PERMUTATIONS:
            dataset_placeholders = copy_placeholders(
                self.placeholders,
                get_placeholders(settings.GRID_PARAMETERS, grid_permutation)
            )
            datasets.append(Dataset(self.path_template, dataset_placeholders))
        return datasets

    @cached_property
    def abspath(self):
        return settings.PLOTS_PATH / self.path

    def exists(self):
        return self.abspath.exists()


class Period:

    def __init__(self, value):
        if value == 'auto':
            self.type = self.specifier = value
        else:
            self.__dict__.update(init_period(value))

    def  __repr__(self):
        return self.specifier


class Region:

    def __init__(self, value):
        if value == 'global':
            self.type = self.specifier = value
        else:
            self.__dict__.update(init_region(value))

    def  __repr__(self):
        return self.specifier


class Aggregation:

    def __init__(self, value):
        self.type = self.specifier = value

    def  __repr__(self):
        return self.specifier


class Plot:

    def __init__(self, value):
        self.type = self.specifier = value

        if value == 'map':
            self.columns = {'lat', 'lon'}
        else:
            self.columns = {'time'}

    def  __repr__(self):
        return self.specifier
