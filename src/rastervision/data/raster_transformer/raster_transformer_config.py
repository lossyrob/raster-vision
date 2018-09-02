from abc import abstractmethod

import rastervision as rv
from rastervision.core.config import (Config, ConfigBuilder)

class RasterTransformerConfig(Config):
    def  __init__(self, transformer_type):
        self.transformer_type = transformer_type

    @abstractmethod
    def create_transformer(self):
        """Create the Transformer that this configuration represents
        """
        pass

    @staticmethod
    def builder(transformer_type):
        return rv._registry.get_config_builder(rv.RASTER_TRANSFORMER, transformer_type)()

    @staticmethod
    def from_proto(msg):
        """Creates a TaskConfig from the specificed protobuf message
        """
        return rv._registry.get_config_builder(rv.RASTER_TRANSFORMER, msg.transformer_type)() \
                           .from_proto(msg) \
                           .build()


class RasterTransformerConfigBuilder(ConfigBuilder):
    pass
