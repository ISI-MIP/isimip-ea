import logging
from pathlib import Path

from .utils import gather_files, init_period, init_region

logger = logging.getLogger(__name__)


class Dataset:

    def __init__(self, dataset_path):
        self.path = Path(dataset_path).with_suffix('')
        self.files = [File(*file_args) for file_args in gather_files(dataset_path)]

    def  __repr__(self):
        return str(self.path)


class File:

    def __init__(self, file_path, index, first, last):
        self.path = file_path
        self.index = index
        self.first = first
        self.last = last

    def  __repr__(self):
        return str(self.path)


class Period:

    def __init__(self, specifier):
        self.specifier = specifier

        if specifier == 'auto':
            self.type = 'auto'
        else:
            self.__dict__.update(init_period(specifier))

    def  __repr__(self):
        return self.specifier


class Region:

    def __init__(self, specifier):
        self.specifier = specifier

        if specifier == 'global':
            self.type = 'global'
        else:
            self.__dict__.update(init_region(specifier))

    def  __repr__(self):
        return self.specifier


class Aggregation:

    def __init__(self, specifier):
        self.specifier = specifier
        self.type = specifier

    def  __repr__(self):
        return self.specifier
