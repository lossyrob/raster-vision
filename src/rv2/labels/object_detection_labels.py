import numpy as np

from object_detection.utils.np_box_list import BoxList
from object_detection.utils.np_box_list_ops import (
    prune_non_overlapping_boxes, clip_to_window, change_coordinate_frame,
    concatenate, scale, multi_class_non_max_suppression, _copy_extra_fields)

from rv2.core.box import Box
from rv2.core.labels import Labels


def geojson_to_labels(geojson, crs_transformer):
    """Extract boxes and related info from GeoJSON file."""
    features = geojson['features']
    boxes = []
    class_ids = []
    scores = []

    for feature in features:
        # Convert polygon to pixel coords and then convert to bounding box.
        polygon = feature['geometry']['coordinates'][0]
        polygon = [crs_transformer.web_to_pixel(p) for p in polygon]
        xmin, ymin = np.min(polygon, axis=0)
        xmax, ymax = np.max(polygon, axis=0)
        boxes.append(Box(ymin, xmin, ymax, xmax))

        properties = feature.get('properties', {})
        class_ids.append(properties.get('class_id', 1))
        scores.append(properties.get('score', 1.0))

    boxes = np.array([box.npbox_format() for box in boxes], dtype=float)
    class_ids = np.array(class_ids)
    scores = np.array(scores)
    labels = ObjectDetectionLabels(boxes, class_ids, scores=scores)
    return labels


def labels_to_geojson(labels, crs_transformer, class_map):
    boxes = labels.get_boxes()
    class_ids = labels.get_class_ids().tolist()
    scores = labels.get_scores().tolist()

    features = []
    for box_ind, box in enumerate(boxes):
        polygon = box.geojson_coordinates()
        polygon = [crs_transformer.pixel_to_web(p) for p in polygon]

        class_id = class_ids[box_ind]
        class_name = class_map.get_by_id(class_id).name
        score = scores[box_ind]

        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Polygon',
                'coordinates': [polygon]
            },
            'properties': {
                'class_id': class_id,
                'class_name': class_name,
                'score': score
            }
        }
        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features
    }


def inverse_change_coordinate_frame(boxlist, window):
    scaled_boxlist = scale(boxlist, window.get_height(), window.get_width())
    npboxes = np.round(scaled_boxlist.get())
    npboxes += [window.ymin, window.xmin, window.ymin, window.xmin]
    boxlist_new = BoxList(npboxes)
    _copy_extra_fields(boxlist_new, boxlist)
    return boxlist_new


class ObjectDetectionLabels(Labels):
    def __init__(self, npboxes, class_ids, scores=None):
        self.boxlist = BoxList(npboxes)
        self.boxlist.add_field('classes', class_ids)
        if scores is not None:
            self.boxlist.add_field('scores', scores)

    @staticmethod
    def from_boxlist(boxlist):
        scores = boxlist.get_field('scores') \
                 if boxlist.has_field('scores') else None
        return ObjectDetectionLabels(
            boxlist.get(), boxlist.get_field('classes'), scores)

    @staticmethod
    def from_geojson(geojson, crs_transformer):
        return geojson_to_labels(geojson, crs_transformer)

    @staticmethod
    def make_empty():
        npboxes = np.empty((0, 4))
        labels = np.empty((0,))
        scores = np.empty((0,))
        return ObjectDetectionLabels(npboxes, labels, scores)

    def get_subset(self, window, ioa_thresh=1.0):
        window_npbox = window.npbox_format()
        window_boxlist = BoxList(np.expand_dims(window_npbox, axis=0))
        boxlist = prune_non_overlapping_boxes(
            self.boxlist, window_boxlist, minoverlap=ioa_thresh)
        boxlist = clip_to_window(boxlist, window_npbox)
        boxlist = change_coordinate_frame(boxlist, window_npbox)
        return ObjectDetectionLabels.from_boxlist(boxlist)

    def get_boxes(self):
        return [Box.from_npbox(npbox) for npbox in self.boxlist.get()]

    def get_coordinates(self):
        return self.boxlist.get_coordinates()

    def get_npboxes(self):
        return self.boxlist.get()

    def get_scores(self):
        if self.boxlist.has_field('scores'):
            return self.boxlist.get_field('scores')
        return None

    def get_class_ids(self):
        return self.boxlist.get_field('classes')

    def __len__(self):
        return self.boxlist.get().shape[0]

    def concatenate(self, window, labels):
        boxlist_new = concatenate([
            self.boxlist,
            inverse_change_coordinate_frame(labels.boxlist, window)])
        return ObjectDetectionLabels.from_boxlist(boxlist_new)

    def prune_duplicates(self, score_thresh, merge_thresh):
        max_output_size = 1000000
        boxlist_new = multi_class_non_max_suppression(
            self.boxlist, score_thresh, merge_thresh, max_output_size)
        # Add one because multi_class_nms outputs labels that start at zero
        # instead of one like in the rest of the system. This is a kludge.
        class_ids = boxlist_new.get_field('classes')
        class_ids += 1
        return ObjectDetectionLabels.from_boxlist(boxlist_new)

    def to_geojson(self, crs_transformer, class_map):
        return labels_to_geojson(self, crs_transformer, class_map)
