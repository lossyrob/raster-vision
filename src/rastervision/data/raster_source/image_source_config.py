from copy import deepcopy

import rastervision as rv
from rastervision.data.raster_source.image_source import ImageSource
from rastervision.data.raster_source.raster_source_config \
    import (RasterSourceConfig, RasterSourceConfigBuilder)
from rastervision.protos.raster_source2_pb2 import RasterSourceConfig as RasterSourceConfigMsg
from rastervision.utils.files import file_exists


class ImageSourceConfig(RasterSourceConfig):
    def __init__(self,
                 uri,
                 transformers=[],
                 channel_order=None):
        super().__init__(source_type=rv.IMAGE_SOURCE,
                         transformers=transformers,
                         channel_order=channel_order)
        self.uri = uri

    def to_proto(self):
        msg = super().to_proto()
        msg.image_file = RasterSourceConfigMsg.ImageFile(uri=self.uri)
        return msg

    def create_source(self, tmp_dir):
        transformers = self.create_transformers()
        return ImageSource(self.uri, transformers, tmp_dir, self.channel_order)

class ImageSourceConfigBuilder(RasterSourceConfigBuilder):
    def __init__(self, prev=None):
        config = {}
        if prev:
            config = { "uri": prev.uri,
                       "transformers": prev.transformers,
                       "channel_order": prev.channel_order }

        super().__init__(ImageSourceConfig, config)

    def from_proto(self, msg):
        b = super().from_proto(msg)

        return b \
            .with_uri(msg.image_file.uri)

    def with_uri(self, uri):
        b = deepcopy(self)
        b.config['uri'] = uri
        return b
