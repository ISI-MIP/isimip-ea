from isimip_utils.config import Settings as BaseSettings
from isimip_utils.parameters import get_permutations
from isimip_utils.utils import cached_property
from isimip_utils.xarray import open_dataset


class Settings(BaseSettings):

    @cached_property
    def WEIGHTS(self):
        if self.GRIDAREA:
            ds = open_dataset(self.GRIDAREA, load=self.LOAD)
            ds = ds.isel(lon=0)
            return ds.cell_area

    @cached_property
    def FIGS_PARAMETERS(self):
        return dict(list(self.PARAMETERS.items())[:settings.FIGS]) if self.PARAMETERS else {}

    @cached_property
    def GRID_PARAMETERS(self):
        return dict(list(self.PARAMETERS.items())[settings.FIGS:]) if self.PARAMETERS else {}

    @cached_property
    def FIGS_PERMUTATIONS(self):
        return get_permutations(settings.FIGS_PARAMETERS) if self.PARAMETERS else [()]

    @cached_property
    def GRID_PERMUTATIONS(self):
        return get_permutations(settings.GRID_PARAMETERS) if self.PARAMETERS else [()]

    @cached_property
    def PLOT_RESOLVE_SCALE(self):
        return {
            'x': 'independent' if settings.INDEPENDENT_X else 'shared',
            'y': 'independent' if settings.INDEPENDENT_Y else 'shared',
            'color': 'shared' if settings.SHARED_COLOR else 'independent',
        }


settings = Settings()
