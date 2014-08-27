__author__ = 'da.angulo39'

import sqlite3
import shutil
import cPickle
from braviz.readAndFilter import hierarchical_fibers

source_db = r"D:\kmc400-braviz\braviz_data\tabular_data.sqlite"
dest_db = r"D:\kmc400-braviz\braviz_data\tabular_data - lavadora.sqlite"

dest_db_2 = dest_db[:-7]+"temp.sqlite"

print dest_db_2
shutil.copyfile(dest_db,dest_db_2)

map_roi_ids = {}
map_bundle_ids = {}

source_con = sqlite3.connect(source_db)
dest_con = sqlite3.connect(dest_db_2)


#only commit if all goes well
with dest_con:
    #merge geom_rois
    low_limit = 12

    cur = source_con.execute("SELECT * FROM geom_rois")
    rois = cur.fetchall()
    for row in rois:
        if row[0]>=low_limit:
            print row
            insert_cur = dest_con.execute(
                "INSERT OR FAIL INTO geom_rois (roi_name,roi_type,roi_desc,roi_coords) VALUES (?,?,?,?)",
                            (row[1],row[2],row[3],row[4]))
            map_roi_ids[row[0]]=insert_cur.lastrowid
    print map_roi_ids

    #merge geom_spheres
    cur = source_con.execute("SELECT * FROM geom_spheres WHERE sphere_id >= ?",(low_limit,))
    spheres = cur.fetchall()
    for row in spheres:
        new_id = map_roi_ids[row[0]]
        insert_cur = dest_con.execute(
                "INSERT OR FAIL INTO geom_spheres VALUES (?,?,?,?,?,?)",
                            (new_id,row[1],row[2],row[3],row[4],row[5]))

    #merge fiber_bundles
    cur = source_con.execute("SELECT * FROM fiber_bundles WHERE bundle_type = 10")
    bundles = cur.fetchall()
    def map_tree(root):
        n_type = root["node_type"]
        if n_type == hierarchical_fibers.ROI:
            roi_id = root["extra_data"]
            new_roi_id = map_roi_ids[roi_id]
            root["extra_data"]=new_roi_id
        for c in root["children"]:
            map_tree(c)

    for row in bundles:
        print row[:3]
        tree = cPickle.loads(str(row[3]))
        print
        print tree
        map_tree(tree)
        print tree
        blob2 = buffer(cPickle.dumps(tree,-1))
        try :
            insert_cur = dest_con.execute(
                "INSERT OR FAIL INTO fiber_bundles (bundle_name,bundle_type,bundle_data) VALUES (?,?,?)",
                            (row[1],row[2],blob2))
            map_bundle_ids[row[0]]=insert_cur.lastrowid
        except sqlite3.IntegrityError as e:
            print "couldn't insert %s"%row[1]
            print e

    print map_bundle_ids
    #merge scenarios
print "commiting"