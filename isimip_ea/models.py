import logging
import re
from functools import cached_property
from pathlib import Path

from isimip_utils.fetch import fetch_file, load_file
from isimip_utils.files import find_files
from isimip_utils.parameters import (
    apply_placeholders,
    copy_placeholders,
    get_permutations,
    get_placeholders,
)
from isimip_utils.utils import get_max_value, get_min_value

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
    def full_path(self):
        if settings.DATASETS_PATH:
            return settings.DATASETS_PATH / self.path

    @cached_property
    def files(self):
        if self.full_path:
            glob = sorted(self.full_path.parent.glob(f'{self.full_path.stem}*'))

            return [
                File(file_path, start_year, end_year)
                for file_path, start_year, end_year in find_files(glob)
            ]
        else:
            return []

    @cached_property
    def start_year(self):
        return get_min_value([file.start_year for file in self.files])

    @cached_property
    def end_year(self):
        return get_max_value([file.end_year for file in self.files])

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

    def __init__(self, path, start_year, end_year):
        self.path = path
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
        path_prefix = update_path(
            self.dataset.path, self.period, self.region, self.aggregation,
            start_year=self.dataset.start_year, end_year=self.dataset.end_year
        )

        if self.dataset.exists():
            # if the dataset exists locally, the prefix was constructed from the actual files, with the correct years
            return path_prefix.with_suffix('.nc')
        elif settings.EXTRACTIONS_PATH:
            # construct a base path for the extraction from the dataset and try to find extraction locally
            full_path_prefix = settings.EXTRACTIONS_PATH / path_prefix
            glob = sorted(full_path_prefix.parent.glob(f'{full_path_prefix.stem}*'))
            for file_path, _, _ in find_files(glob):
                return file_path.relative_to(settings.EXTRACTIONS_PATH)

            # try to find the extraction online
            if settings.EXTRACTIONS_LOCATIONS:
                for location in settings.EXTRACTIONS_LOCATIONS:
                    if isinstance(location, Path):
                        pass
                    else:
                        pattern = path_prefix.stem + r'_(?P<start_year>\d{4})_(?P<end_year>\d{4})?\.nc\d*'
                        index = fetch_file(f'{location}/{path_prefix.parent}')
                        match = re.search(pattern, index)
                        if match:
                            return path_prefix.parent / match.group()

    @cached_property
    def full_path(self):
        if self.path:
            return settings.EXTRACTIONS_PATH / self.path

    def exists(self):
        if self.path:
            return self.full_path.exists()

    def fetch(self):
        if self.path:
            if settings.EXTRACTIONS_LOCATIONS:
                for location in settings.EXTRACTIONS_LOCATIONS:
                    if isinstance(location, Path):
                        result = load_file(location / self.path, self.full_path)
                    else:
                        result = fetch_file(f'{location}/{self.path}', self.full_path)

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
        if settings.FIGURE_PATH:
            figure_path_template = settings.FIGURE_PATH / Path(self.path_template).name
        else:
            # find the  placeholder which is not in FIGS_PLACEHOLDERS or GRID_PLACEHOLDERS
            figure_path_template = self.path_template
            parts = Path(self.path_template).parts
            name = Path(self.path_template).name
            for i, part in enumerate(parts):
                match = re.match(r"^\{([^}]+)\}$", part)
                if match:
                    if match.group(1) not in settings.FIGURE_PLACEHOLDERS + settings.GRID_PLACEHOLDERS:
                        figure_path_template = Path(*parts[:i]) / name
                        break

        path = update_path(
            apply_placeholders(figure_path_template, self.placeholders),
            self.period, self.region, self.aggregation, self.plot,
            start_year=self.start_year, end_year=self.end_year
        )

        return path.with_suffix(f'.{settings.PLOT_FORMAT}')

    @cached_property
    def full_path(self):
        return settings.PLOTS_PATH / self.path

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
    def start_year(self):
        return get_min_value([dataset.start_year for dataset in self.datasets])

    @cached_property
    def end_year(self):
        return get_max_value([dataset.end_year for dataset in self.datasets])

    def exists(self):
        return self.full_path.exists()


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
