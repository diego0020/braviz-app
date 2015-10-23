##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


__author__ = 'Diego'

import cPickle

from braviz.readAndFilter.tabular_data import get_connection


def get_bundle_ids_and_names():
    """
    Available bundles

    Returns:
        A list of tuples ``(id,name)`` where id is the bundle id and name is the bundle name
    """
    conn = get_connection()
    q = "SELECT bundle_id, bundle_name FROM fiber_bundles"
    cur = conn.execute(q)
    return cur.fetchall()


def get_bundle_details(bundle_id):
    """
    Low Level, Get all data from a given bundle

    Args:
        bundle_id (int) : Bundle id

    Returns:
        ``(name,type,data)`` where name is the bundle name, type is the bundle type and data is the raw data for the
        bundle. The current types are

            ========    ==========================     ==================================
            Type        Description                    Data contents
            ========    ==========================     ==================================
            0           Alias to named fiber           str containing fiber name
            1           Waypoints ``and``              pickled waypoints list
            2           Waypoints ``or``               pickled waypoints list
            10          Hierarchical                   pickled nodes dictionary
            ========    ==========================     ==================================
    """
    conn = get_connection()
    q = "SELECT bundle_name, bundle_type, bundle_data FROM fiber_bundles WHERE bundle_id = ?"
    cur = conn.execute(q, (bundle_id,))
    res = cur.fetchone()
    return res


def get_bundle_name(bundle_id):
    """
    Name of a bundle in the database

    Args:
        bundle_id (int) : Bundle id

    Returns:
        Bundle name
    """
    conn = get_connection()
    q = "SELECT bundle_name FROM fiber_bundles WHERE bundle_id = ?"
    cur = conn.execute(q, (bundle_id,))
    res = cur.fetchone()
    return res[0]


def check_if_name_exists(name):
    """
    Check if a bundle with the given name exists in the database

    Args:
        name (str) : Bundle name

    Returns:
        ``True`` if a bundle with this name exists, ``False`` otherwise
    """
    conn = get_connection()
    q = "SELECT * FROM fiber_bundles WHERE bundle_name = ?"
    cur = conn.execute(q, (name,))
    res = cur.fetchone()
    return res is not None


def save_checkpoints_bundle(bundle_name, operation_is_and, waypoints):
    """
    Saves a bundle defined using checkpoints

    Args:
        bundle_name (str) : Name for the bundle
        operation_is_and (bool) : ``True`` if the bundle contains fibers that should
            pass through all waypoint, ``False`` if fibers may pass through any waypoint
        waypoints (list) : List of waypoints, these should be structure names.

    """
    waypoints = tuple(waypoints)
    if operation_is_and is True:
        btype = 1
    else:
        btype = 2

    data = buffer(cPickle.dumps(waypoints, 2))
    q = """INSERT OR FAIL INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,?,?) """
    conn = get_connection()
    conn.execute(q, (bundle_name, btype, data))
    conn.commit()


def get_bundles_list(bundle_type=None):
    """
    Get available bundles

    Args:
        bundle_type (int) : Optional, restrict only to a certain type, see :func:`.get_bundle_details`

    Returns:
        A list containing the names of the available bundles
    """
    con = get_connection()
    if bundle_type is None:
        q = "SELECT bundle_name FROM fiber_bundles"
        cur = con.execute(q)
        res = [x[0] for x in cur.fetchall()]
        return res
    else:
        q = "SELECT bundle_name FROM fiber_bundles WHERE bundle_type = ?"
        cur = con.execute(q, (bundle_type,))
        res = [x[0] for x in cur.fetchall()]
        return res


def save_logic_bundle(bundle_name, logic_tree_dict):
    """
    Saves a logic bundle into the database

    Args:
        bundle_name (str) : Name for the bundle
        logic_tree_dict (dict) : Dictionary describing the bundle, see :func:`.get_logic_bundle_dict`

    """
    tree_blob = buffer(cPickle.dumps(logic_tree_dict, 2))
    q = """INSERT OR FAIL INTO fiber_bundles (bundle_name, bundle_type, bundle_data) VALUES (?,10,?) """
    con = get_connection()
    con.execute(q, (bundle_name, tree_blob))
    con.commit()


def get_logic_bundle_dict(bundle_id=None, bundle_name=None):
    """
    Retrieves a logic bundle from the database

    Only one of the arguments is required, bundle_id is preferred

    Args:
        bundle_id (int) : Bundle id
        bundle_name (str) : Bundle name

    Returns
        A nested dictionary with the specification of the logic bundle. The hierarchy is represented as a tree, where
        each node is a dictionary. The returned dictionary represents the top node of this tree. There are three types
        of nodes: logical, structures and rois. All nodes are dictionaries with three keys : ``"node_type"``,
        ``"value"`` and ``"extra_data"``

        - Logic nodes: Value is a string which can take the values ``"OR"`` , ``"AND"`` or ``"NOT"``. Extra_data holds
          a list of children nodes. OR nodes represent the union from the sets returned by each child, AND
          represent an intersection, and NOT subtracts the union from the reference set (the whole tractography).

        - Structure nodes: Leaf node, its value contains the name of an structure. It represents the fibers that
          cross such structure.

        - ROI nodes: Leaf node, its extra_data contains the database id for a ROI
          (see :mod:`~braviz.readAndFilter.geom_db`). It represents fibers that cross such ROI.
    """
    con = get_connection()
    if bundle_id is None:
        q = "SELECT bundle_data FROM fiber_bundles WHERE bundle_name = ?"
        cur = con.execute(q, (bundle_name,))
    else:
        q = "SELECT bundle_data FROM fiber_bundles WHERE bundle_id = ?"
        cur = con.execute(q, (bundle_id,))
    r1 = cur.fetchone()
    if r1 is None:
        raise Exception("Fiber doesn't exist")
    data_buf = r1[0]
    data_dict = cPickle.loads(str(data_buf))
    return data_dict


def remove_bundle(bundle_id):
    """
    Deletes a fiber bundle from the database

    Args:
        bundle_id (int) : Bundle id
    """
    con = get_connection()
    q = "DELETE FROM fiber_bundles WHERE bundle_id = ?"
    with con:
        con.execute(q,(bundle_id, ))
