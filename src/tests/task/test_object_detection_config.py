import unittest
from google.protobuf import json_format
import json

import rastervision as rv
from rastervision.protos.task_pb2 import TaskConfig as TaskConfigMsg

class TestObjectDetectionConfig(unittest.TestCase):
    def test_build_task(self):
        classes = ["one", "two"]
        expected  = { "one" : (0, None),
                      "two"  : (1, None) }

        t = rv.TaskConfig.builder(rv.OBJECT_DETECTION) \
                   .with_classes(classes) \
                   .build()

        self.assertEqual(t.task_type, rv.OBJECT_DETECTION)
        self.assertDictEqual(t.classes, expected)

    def test_build_task_from_proto(self):
        task_config = {
            "task_type": rv.OBJECT_DETECTION,
            "object_detection_config": {
                    "chip_size": 500,
                "class_items": [
                    {
                        "id": 1,
                        "name": "car",
                        "color": "red"
                    },
                    {
                        "id": 2,
                        "name": "building",
                        "color": "blue"
                    },
                    {
                        "id": 3,
                        "name": "background",
                        "color": "black"
                    }
                ]
            }
        }
        msg = json_format.Parse(json.dumps(task_config),
                                TaskConfigMsg())
        task = rv.TaskConfig.from_proto(msg)

        self.assertEqual(task.classes['building'][0], 2)
        self.assertEqual(task.chip_size, 500)

    def test_create_proto_from_task(self):
        t = rv.TaskConfig.builder(rv.OBJECT_DETECTION) \
                         .with_classes(["car", "boat"]) \
                         .with_chip_size(500) \
                         .build()

        msg = t.to_proto()

        expected_classes = [TaskConfigMsg.ClassItem(name="car",
                                                    id=0),
                            TaskConfigMsg.ClassItem(name="boat",
                                                    id=1)]

        self.assertEqual(msg.task_type, rv.OBJECT_DETECTION)
        self.assertEqual(msg.object_detection_config.chip_size, 500)

        actual_class_items = dict([(i.id, i) for i in msg.object_detection_config.class_items])
        expected_class_items = dict([(i.id, i) for i in expected_classes])

        self.assertDictEqual(actual_class_items, expected_class_items)


if __name__ == "__main__":
    unittest.main()
