from braviz.readAndFilter import geom_db,tabular_data
import logging
#from logic_bundle_model
from braviz.readAndFilter import extract_poly_data_subset
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere

LOGIC = 0
STRUCT = 1
ROI = 2

def read_logical_fibers(subj,tree_dict,reader,**kwargs):
    log = logging.getLogger(__file__)
    if "space" in kwargs:
        space = kwargs.pop("space")
    else:
        space = "World"

    try:
        valid_lines = get_valid_lines_from_node(subj,tree_dict,reader)
        fibers=reader.get("FIBERS",subj,space=space,**kwargs)
    except Exception as e:
        log.error(e.message)
        raise
    fibers2 = extract_poly_data_subset(fibers, valid_lines)
    return fibers2

def get_valid_lines_from_node(subj,tree_node,reader):
    node_type = tree_node["node_type"]
    if node_type == LOGIC:
        lines = get_valid_lines_from_logical(subj,tree_node,reader)
    elif node_type == STRUCT:
        lines = get_valid_lines_from_struct(subj,tree_node["value"],reader)
    elif node_type == ROI:
        lines = get_valied_lines_from_roi(subj,tree_node["extra_data"],reader)
    else:
        raise Exception("Unknown data type")
    return lines


def get_valid_lines_from_logical(subj,tree_node,reader):
    subsets = [(get_valid_lines_from_node(subj,c,reader)) for c in tree_node["children"]]
    value = tree_node["value"]
    if value == "OR":
        if len(subsets) == 0:
            ans = set()
        else:
            ans = set.union(*subsets)
    elif value == "AND":
        if len(subsets) == 0:
            ans = get_all_lines(subj,reader)
        else:
            ans = set.intersection(*subsets)
    elif value == "NOT":
        all_lines = get_all_lines(subj,reader)
        ans = all_lines - set.union(*subsets)
    else:
        raise Exception("Invalid logical value")
    return ans

def get_all_lines(subj,reader):
    pd = reader.get("FIBERS",subj)
    assert pd.GetNumberOfCells() == pd.GetNumberOfLines()
    all_lines = set(xrange(pd.GetNumberOfCells()))
    return all_lines


def get_valid_lines_from_struct(subj,struct,reader):
    img_subj = str(tabular_data.get_var_value(tabular_data.IMAGE_CODE,subj))
    valid_ids = reader.filter_fibers(img_subj,struct)
    return set(valid_ids)

def get_valied_lines_from_roi(subj,roi_id,reader):
    space = geom_db.get_roi_space(roi_id=roi_id)
    sphere_data = geom_db.load_sphere(roi_id,subj)
    if sphere_data is None:
        raise Exception("Sphere not found")
    r,x,y,z = sphere_data
    key="roi_fibers_%s_%s_%f_%f_%f_%f"%(subj,roi_id,r,x,y,z)
    cached = reader.load_from_cache(key)

    if cached is None:

        fibers = reader.get("Fibers",subj,space=space)
        filterer = FilterBundleWithSphere()
        filterer.set_bundle(fibers)

        valid_ids = filterer.filter_bundle_with_sphere((x,y,z),r,get_ids=True)
        reader.save_into_cache(key,valid_ids)
        return valid_ids
    else:
        return cached
