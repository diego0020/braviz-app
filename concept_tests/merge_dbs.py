__author__ = 'da.angulo39'

import sqlite3
import shutil
import cPickle
from braviz.readAndFilter import hierarchical_fibers

source_db = r"D:\kmc400-braviz\braviz_data\tabular_data_lavadora.sqlite"
dest_db = r"D:\kmc400-braviz\braviz_data\tabular_data_pre_merge.sqlite"

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
    low_limit = 0

    cur = source_con.execute("SELECT * FROM geom_rois")
    rois = cur.fetchall()
    for row in rois:
        if row[0]>=low_limit:
            print row
            insert_cur = dest_con.execute(
                "INSERT OR IGNORE INTO geom_rois (roi_name,roi_type,roi_desc,roi_coords) VALUES (?,?,?,?)",
                            (row[1],row[2],row[3],row[4]))
            map_roi_ids[row[0]]=insert_cur.lastrowid
    print map_roi_ids

    #merge geom_spheres
    cur = source_con.execute("SELECT * FROM geom_spheres WHERE sphere_id >= ?",(low_limit,))
    spheres = cur.fetchall()
    for row in spheres:
        new_id = map_roi_ids[row[0]]
        insert_cur = dest_con.execute(
                "INSERT OR IGNORE INTO geom_spheres VALUES (?,?,?,?,?,?)",
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
                "INSERT OR IGNORE INTO fiber_bundles (bundle_name,bundle_type,bundle_data) VALUES (?,?,?)",
                            (row[1],row[2],blob2))
            map_bundle_ids[row[0]]=insert_cur.lastrowid
        except sqlite3.IntegrityError as e:
            print "couldn't insert %s"%row[1]
            print e

    print map_bundle_ids
    #merge scenarios

    #merge variables
    dest_vars_names=set(i[0] for i in dest_con.execute("SELECT var_name from variables").fetchall())
    source_vars_names=set(i[0] for i in source_con.execute("SELECT var_name from variables").fetchall())

    missing_vars = source_vars_names - dest_vars_names
    print "There are %d missinge vars in destination db"%len(missing_vars)

    for var_name in missing_vars:
        print "copying %s"%var_name
        source_id, source_is_real = source_con.execute("SELECT var_idx, is_real from variables where var_name = ?",(var_name,)).fetchone()
        dest_id = dest_con.execute("INSERT INTO variables (var_name, is_real) VALUES (?,?)", (var_name, source_is_real)).lastrowid

        #copy meta data
        source_description = source_con.execute("select description from var_descriptions where var_idx=?",(source_id,) ).fetchone()
        if source_description is not None:
            dest_con.execute("INSERT INTO var_descriptions VALUES (?,?)", (dest_id, source_description[0]))

        #meta data
        if source_is_real:
            source_meta = source_con.execute("select * from ratio_meta where var_idx=?",(source_id,)).fetchone()
            if source_meta is not None:
                dest_con.execute("INSERT INTO ratio_meta VALUES (?,?,?,?)", (dest_id,)+source_meta[1:])
        else:
                labels = source_con.execute("Select * from nom_meta where var_idx = ? ",(source_id,)).fetchall()
                dest_con.executemany("INSERT INTO nom_meta VALUES (?,?,?)",((dest_id,)+l[1:] for l in labels))

        #copy data
        values = source_con.execute("Select * from var_values where var_idx = ? ",(source_id,)).fetchall()

        dest_con.executemany("INSERT INTO var_values VALUES (?,?,?)",((dest_id,)+v[1:] for v in values))

print "commiting"