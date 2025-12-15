import logging
import re
from pathlib import Path

from isimip_utils.fetch import fetch_file, load_file
from isimip_utils.utils import (
    apply_placeholders,
    cached_property,
    copy_placeholders,
    get_permutations,
    get_placeholders,
)

from .config import settings
from .utils import init_period, init_region

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
                datasets.append(cls(path, placeholders))

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

    @cached_property
    def path(self):
        stem = self.dataset.path.stem

        if self.aggregation.specifier == 'value':
            region_specifier = self.region.specifier
        else:
            region_specifier = f'{self.region.specifier}-{self.aggregation.specifier}'

        if '_global_' in stem:
            stem = stem.replace('_global_', f'_{region_specifier}_')
        else:
            stem = f'{stem}_{region_specifier}'

        if self.period.specifier != 'auto':
            stem = re.sub(r'(\d{4}_\d{4}|\d{4})', self.period.specifier, stem)

        if self.dataset.start_year:
            stem += f'_{self.dataset.start_year}'

        if self.dataset.end_year:
            stem += f'_{self.dataset.end_year}'

        return self.dataset.path.with_stem(stem).with_suffix('.nc')

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
    def gather(cls, dataset):
        return [
            cls(dataset, period, region, aggregation)
            for period in Period.all()
            for region in Region.all()
            for aggregation in Aggregation.all()
        ]


class Figure:

    def __init__(self, path_template, placeholders, plot):
        self.path_template = path_template
        self.placeholders = placeholders
        self.plot = plot

    @cached_property
    def path(self):
        path = apply_placeholders(self.path_template, self.placeholders)
        stem = path.stem

        if self.start_year:
            stem += f'_{self.start_year}'
        if self.end_year:
            stem += f'_{self.end_year}'

        stem += f'_{self.plot}'

        return path.with_stem(stem).with_suffix(f'.{settings.PLOTS_FORMAT}')

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

    def __init__(self, specifier):
        if specifier == 'auto':
            self.type = self.specifier = specifier
        else:
            self.__dict__.update(init_period(specifier))

    def  __repr__(self):
        return self.specifier

    @classmethod
    def all(cls):
        return [cls(specifier) for specifier in settings.PERIODS]


class Region:

    def __init__(self, specifier):

        if specifier == 'global':
            self.type = self.specifier = specifier
        else:
            self.__dict__.update(init_region(specifier))

    def  __repr__(self):
        return self.specifier

    @classmethod
    def all(cls):
        return [cls(specifier) for specifier in settings.REGIONS]


class Aggregation:

    def __init__(self, specifier):
        self.type = self.specifier = specifier

    def  __repr__(self):
        return self.specifier

    @classmethod
    def all(cls):
        return [cls(specifier) for specifier in settings.AGGREGATIONS]


class Plot:

    def __init__(self, specifier):
        self.type = self.specifier = specifier

        if specifier == 'map':
            self.columns = {'lat', 'lon'}
        else:
            self.columns = {'time'}

    def  __repr__(self):
        return self.specifier

    @classmethod
    def all(cls):
        return [cls(specifier) for specifier in settings.PLOTS]
