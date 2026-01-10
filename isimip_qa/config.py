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
        return {key: self.PARAMETERS[key] for key in self.FIGS} if self.PARAMETERS else {}

    @cached_property
    def GRID_PARAMETERS(self):
        return {key: self.PARAMETERS[key] for key in self.GRID} if self.PARAMETERS else {}

    @cached_property
    def PLOT_PARAMETERS(self):
        return {
            key: values for key, values in self.PARAMETERS.items() if key not in self.FIGS + self.GRID
        } if self.PARAMETERS else {}

    @cached_property
    def FIGS_PERMUTATIONS(self):
        return get_permutations(self.FIGS_PARAMETERS) if self.PARAMETERS else [()]

    @cached_property
    def GRID_PERMUTATIONS(self):
        return get_permutations(self.GRID_PARAMETERS) if self.PARAMETERS else [()]

    @cached_property
    def PLOT_PERMUTATIONS(self):
        return get_permutations(self.PLOT_PARAMETERS) if self.PARAMETERS else [()]

    @cached_property
    def PLOT_RESOLVE_SCALE(self):
        return {
            'x': 'independent' if self.INDEPENDENT_X else 'shared',
            'y': 'independent' if self.INDEPENDENT_Y else 'shared',
            'color': 'shared' if self.SHARED_COLOR else 'independent',
        }


settings = Settings()
