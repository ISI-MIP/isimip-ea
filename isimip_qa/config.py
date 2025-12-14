from isimip_utils.config import Settings as BaseSettings
from isimip_utils.utils import cached_property
from isimip_utils.xarray import open_dataset


class Settings(BaseSettings):

    @cached_property
    def WEIGHTS(self):
        if self.GRIDAREA:
            ds = open_dataset(self.GRIDAREA)
            ds = ds.isel(lon=0)
            return ds.cell_area


settings = Settings()
