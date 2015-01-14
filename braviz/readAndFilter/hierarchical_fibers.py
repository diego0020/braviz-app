##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

from braviz.readAndFilter import geom_db,tabular_data
import logging
import numpy as np

from braviz.readAndFilter import extract_poly_data_subset
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere

#from logic_bundle_model
LOGIC = 0
STRUCT = 1
ROI = 2

def read_logical_fibers(subj,tree_dict,reader,**kwargs):
    """
    Gets a :obj:`vtkPolyData` for a bundle described using a logical hierarchy

    Args:
        subj : Id of subject
        tree_dict (dict) : Dictionary describing the logical tree,
            see :func:`braviz.readAndFilter.bundles_db.get_logic_bundle_dict`
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
    """
    log = logging.getLogger(__file__)
    if "space" in kwargs:
        space = kwargs.pop("space")
    else:
        space = "World"

    try:
        valid_lines = get_valid_lines_from_node(subj,tree_dict,reader)
        fibers=reader.get("FIBERS",subj,space=space,**kwargs)
    except Exception as e:
        log.exception(e)
        raise
    fibers2 = extract_poly_data_subset(fibers, valid_lines)
    return fibers2

def get_valid_lines_from_node(subj,tree_node,reader):
    """
    Get ids of polylines that match the condition described in a tree node

    Args:
        subj : Id of subject
        tree_node (braviz.interaction.logic_bundle_model.LogicBundleNode) : Tree node
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
    """
    node_type = tree_node["node_type"]
    if node_type == LOGIC:
        lines = get_valid_lines_from_logical(subj,tree_node,reader)
    elif node_type == STRUCT:
        lines = get_valid_lines_from_struct(subj,tree_node["value"],reader)
    elif node_type == ROI:
        lines = get_valid_lines_from_roi(subj,tree_node["extra_data"],reader)
    else:
        raise Exception("Unknown data type")
    return lines


def get_valid_lines_from_logical(subj,tree_node,reader):
    """
    Get polyline ids that match the condition in a logical node

    Args:
        subj : Id of subject
        tree_node (braviz.interaction.logic_bundle_model.LogicBundleNode) : Tree node, must have logical type
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
    """
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
    """
    Gets a list of the polyline ids of the whole tractography

    Args:
        subj : Subject id
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
    """
    pd = reader.get("FIBERS",subj)
    assert pd.GetNumberOfCells() == pd.GetNumberOfLines()
    all_lines = set(xrange(pd.GetNumberOfCells()))
    return all_lines


def get_valid_lines_from_struct(subj,struct,reader):
    """
    Get polyline ids that match the condition in a structure node

    Args:
        subj : Id of subject
        struct (str) : Name of a freesufer model
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
    """
    img_subj = subj
    valid_ids = reader.get('fibers',img_subj,waypoint=struct,ids=True)
    return set(valid_ids)

def get_valid_lines_from_roi(subj,roi_id,reader):
    """
    Get polyline ids that match the condition in a roi node

    Args:
        subj : Id of subject
        roi_id : Database id of a ROI (see :mod:`braviz.readAndFilter.geom_db`)
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
    """
    space = geom_db.get_roi_space(roi_id=roi_id)
    sphere_data = geom_db.load_sphere(roi_id,subj)
    if sphere_data is None:
        raise Exception("Sphere not found")
    r,x,y,z = sphere_data
    key="roi_fibers_%s_%s"%(subj,roi_id)
    cached = reader.load_from_cache(key)
    if cached is not None:
        valid_ids, sphere_data_c = cached
        if sphere_data_c == sphere_data:
            return valid_ids

    fibers = reader.get("Fibers",subj,space=space)
    filterer = FilterBundleWithSphere()
    #Maybe overkill for only one sphere, but still fater than brute force
    filterer.set_bundle(fibers)

    valid_ids = filterer.filter_bundle_with_sphere((x,y,z),r,get_ids=True)
    reader.save_into_cache(key,(valid_ids,(r,x,y,z)))
    return valid_ids



def _brute_force_lines_in_sphere(fibers,ctr,radius):
    #TODO try by loading first all points into a numpy array
    ans = set()
    c = np.array(ctr)
    n_lines = fibers.GetNumberOfLines()
    n_cells = fibers.GetNumberOfCells()
    r2 = radius**2
    assert n_lines == n_cells


    for i in xrange(n_lines):
        l = fibers.GetCell(i)
        pts = l.GetPoints()
        n_pts = l.GetNumberOfPoints()
        for j in xrange(n_pts):
            p = pts.GetPoint(j)
            if np.dot((p-c),(p-c)) <= r2:
                ans.add(i)
                break
    return ans