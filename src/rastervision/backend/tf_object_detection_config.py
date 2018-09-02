from copy import deepcopy
from tempfile import TemporaryDirectory
from google.protobuf import (text_format, json_format)
import json

import rastervision as rv
from .backend_config import (BackendConfig, BackendConfigBuilder)
from ..core.config import set_nested_keys
from ..protos.backend_pb2 import BackendConfig as BackendConfigMsg
from ..utils.files import file_to_str


class TFObjectDetectionConfig(BackendConfig):
    def __init__(self, backend_config, pretrained_model_uri=None):
        super().__init__(rv.TF_OBJECT_DETECTION, pretrained_model_uri)
        self.backend_config = backend_config

    def create_backend(self):
        return TFObjectDetectionBackend(self)

    def builder(self):
        return TFObjectDetectionConfigBuilder(self)

    def to_proto(self):
        d = {"backend_type": rv.TF_OBJECT_DETECTION,
             "config": self.backend_config}
        if self.pretrained_model_uri:
            d["pretrained_model_uri"] = self.pretrained_model_uri
        return json_format.ParseDict(d,  BackendConfigMsg())

# TODO: Handle pretrained model config.

class TFObjectDetectionConfigBuilder(BackendConfigBuilder):
    def __init__(self, prev=None):
        config = { }
        if prev:
            config = { "backend_config": prev.backend_config }
        super().__init__(rv.TF_OBJECT_DETECTION, TFObjectDetectionConfig, config)
        self.config_mods = []
        self.require_task = True

    def from_proto(self, msg):
        conf = json_format.MessageToDict(msg.config)
        b = TFObjectDetectionConfigBuilder()
        # Since this is coming from a serialized message,
        # assume the task has already been set and do not
        # require it during validation.
        b.require_task = False
        if self.config.get('pretrained_model_uri'):
            b = b.with_pretrained_model_uri(self.config.pretarined_model_uri)
        return b.with_template(conf)

    def validate(self):
        super().validate()
        if not self.config.get('backend_config'):
            raise rv.ConfigError("You must specify a template for the backend"
                                      "configuration - use 'with_template'.")
        if self.require_task and not self.task:
            raise rv.ConfigError("You must specify the task this backend"
                                     "is for - use 'with_task'.")
        return True

    def build(self):
        """Build this configuration, setting any values into the
           TF object detection pipeline config as necessary.
        """
        self.validate()
        for config_mod, ignore_missing_keys in self.config_mods:
            set_nested_keys(self.config['backend_config'], config_mod, ignore_missing_keys)
        return super().build()

    def _applicable_tasks(self):
        return [rv.OBJECT_DETECTION]

    def _process_task(self):
        return self.with_config({
            "numClasses": len(self.task.classes.items()),
            "imageResizer": {
                "fixedShapeResizer": {
                    "height": self.task.chip_size,
                    "width": self.task.chip_size
                },
                "keepAspectRatioResizer": {
                    "minDimension": self.task.chip_size,
                    "maxDimension": self.task.chip_size
                }
            }
        }, ignore_missing_keys=True)

    def _load_model_defaults(self, model_defaults):
        """Loads defaults. Expected keys are "pretrained_model_uri" and "backend_config_uri",
           neither of which is required.
        """
        expected_keys = ["pretrained_model_uri", "backend_config_uri"]
        unknown_keys = set(model_defaults.keys()) - set(expected_keys)
        if unknown_keys:
            raise rv.ConfigError(("Unexpected keys in model defaults:"
                                  " {}. Expected keys: {}") \
                                 .format(unknown_keys, expected_keys))

        b = self
        if "pretrained_model_uri" in model_defaults:
            b = b.with_pretrained_model(model_defaults["pretrained_model_uri"])
        if "backend_config_uri" in model_defaults:
            b = b.with_template(model_defaults["backend_config_uri"])
        return b

    def with_template(self, template):
        """Use a template from the dict, string or uri as the base for the tensorflow object
           detection API model training pipeline, for example those found
          here: https://github.com/tensorflow/models/tree/eef6bb5bd3b3cd5fcf54306bf29750b7f9f9a5ea/research/object_detection/samples/configs
        """
        from object_detection.protos.pipeline_pb2 import TrainEvalPipelineConfig

        template_json = None
        if type(template) is dict:
            template_json = template
        else:
            # Try parsing the string as a message, on fail assume it's a URI
            msg = None
            try :
                msg = text_format.Parse(template, TrainEvalPipelineConfig())
            except text_format.ParseError:
                msg = text_format.Parse(file_to_str(template), TrainEvalPipelineConfig())
            template_json = json_format.MessageToDict(msg)

        b = deepcopy(self)
        b.config['backend_config'] = template_json
        return b

    def with_batch_size(self, batch_size):
        return self.with_config({
            "trainConfig": {
                "batchSize": batch_size
            }
        })

    def with_num_steps(self, num_steps):
        return self.with_config({
            "trainConfig": {
                "numSteps": num_steps
            }
        })

    def with_config(self, config_mod, ignore_missing_keys=False):
        """Given a dict, modify the tensorflow pipeline configuration
           such that keys that are found recursively in the configuration
           are replaced with those values. TODO: better explination.
        """
        b = deepcopy(self)
        b.config_mods.append((config_mod, ignore_missing_keys))
        return b
