from isimip_utils.config import Settings as BaseSettings
from isimip_utils.utils import cached_property, get_permutations
from isimip_utils.xarray import open_dataset


class Settings(BaseSettings):

    @cached_property
    def WEIGHTS(self):
        if self.GRIDAREA:
            ds = open_dataset(self.GRIDAREA)
            ds = ds.isel(lon=0)
            return ds.cell_area

    @cached_property
    def PARAMETERS(self):
        return dict(self.PLACEHOLDERS)

    @cached_property
    def FIGS_PARAMETERS(self):
        return dict(self.PLACEHOLDERS[:settings.FIGS])

    @cached_property
    def GRID_PARAMETERS(self):
        return dict(self.PLACEHOLDERS[settings.FIGS:])

    @cached_property
    def FIGS_PERMUTATIONS(self):
        return get_permutations(settings.FIGS_PARAMETERS)

    @cached_property
    def GRID_PERMUTATIONS(self):
        return get_permutations(settings.GRID_PARAMETERS)


settings = Settings()
