import os
import json
import xml.etree.ElementTree as ET
from tqdm import tqdm
import re


def get_label2id(labels_path):
    """id is 1 start"""
    with open(labels_path, "r") as f:
        labels_str = f.read().split()
    labels_ids = list(range(1, len(labels_str) + 1))
    return dict(zip(labels_str, labels_ids))


def get_annpaths(ann_dir_path=None, ann_ids_path=None, ext="", annpaths_list_path=None):
    # If use annotation paths list
    if annpaths_list_path is not None:
        with open(annpaths_list_path, "r") as f:
            ann_paths = f.read().split()
        return ann_paths

    # If use annotaion ids list
    ext_with_dot = "." + ext if ext != "" else ""
    with open(ann_ids_path, "r") as f:
        ann_ids = f.read().split()
    ann_paths = [os.path.join(ann_dir_path, aid + ext_with_dot)
                 for aid in ann_ids]
    return ann_paths


def get_image_info(annotation_root):
    filename = annotation_root.findtext("filename")
    # NOTE: here we make a custom ID
    img_id = filename[0:-4]  # removes the .png or .jpg path of the image
    size = annotation_root.find("size")
    width = int(size.findtext("width"))
    height = int(size.findtext("height"))

    image_info = {"file_name": filename,
                  "height": height, "width": width, "id": img_id}
    return image_info


def get_coco_annotation_from_obj(obj, label2id):
    label = obj.findtext("name")
    assert label in label2id, "Error: {} is not in label2id !".format(label)
    category_id = label2id[label]
    bndbox = obj.find("bndbox")
    xmin = int(bndbox.findtext("xmin")) - 1
    ymin = int(bndbox.findtext("ymin")) - 1
    xmax = int(bndbox.findtext("xmax"))
    ymax = int(bndbox.findtext("ymax"))
    assert (
        xmax > xmin and ymax > ymin
    ), "Box size error !: (xmin, ymin, xmax, ymax): {}, {}, {}, {}".format(
        xmin, ymin, xmax, ymax
    )
    o_width = xmax - xmin
    o_height = ymax - ymin
    ann = {
        "area": o_width * o_height,
        "iscrowd": 0,
        "bbox": [xmin, ymin, o_width, o_height],
        "category_id": category_id,
        "ignore": 0,
        "segmentation": [],  # This script is not for segmentation
    }
    return ann


def convert_xmls_to_cocojson(annotation_paths, label2id, output_jsonpath):
    output_json_dict = {
        "images": [],
        "type": "instances",
        "annotations": [],
        "categories": [],
    }
    bnd_id = 1  # START_BOUNDING_BOX_ID, TODO input as args ?
    for a_path in tqdm(annotation_paths):
        ann_tree = ET.parse(a_path)
        ann_root = ann_tree.getroot()

        img_info = get_image_info(annotation_root=ann_root)
        img_id = img_info["id"]
        output_json_dict["images"].append(img_info)

        for obj in ann_root.findall("object"):
            ann = get_coco_annotation_from_obj(obj=obj, label2id=label2id)
            ann.update({"image_id": img_id, "id": bnd_id})
            output_json_dict["annotations"].append(ann)
            bnd_id = bnd_id + 1

    for label, label_id in label2id.items():
        category_info = {"supercategory": "none",
                         "id": label_id, "name": label}
        output_json_dict["categories"].append(category_info)

    with open(output_jsonpath, "w") as f:
        output_json = json.dumps(output_json_dict)
        f.write(output_json)


def main(prefix_path):
    annot_xml_dir = os.path.join(prefix_path, "labels_xml")
    label_file = os.path.join(prefix_path, "classes.txt")
    output_path = os.path.join(prefix_path, "annotation.json")
    all_paths = [
        os.path.join(annot_xml_dir, i)
        for i in os.listdir(annot_xml_dir)
        if i.endswith("xml")
    ]
    label2id = get_label2id(labels_path=label_file)
    convert_xmls_to_cocojson(
        annotation_paths=all_paths, label2id=label2id, output_jsonpath=output_path,
    )


if __name__ == "__main__":
    prefix_path = "path_to/udacity-nd/ImageDataset/annotated_dataset/simulator_dataset_rgb"
    main(prefix_path)
