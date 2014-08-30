from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, geom_db
from braviz.interaction.structure_metrics import aggregate_in_roi


__author__ = 'da.angulo39'

def roi2db(roi_id):
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=1000)
    roi_name = geom_db.get_roi_name(roi_id)
    measures = {"fa":"FA","md":"MD"}
    subjects = tabular_data.get_subjects()[:10]
    var_ids = {}
    space = geom_db.get_roi_space(roi_id=roi_id)

    for m in measures:
        var_name = "bvz_"+roi_name+"_"+m
        #vi=tabular_data.register_new_variable(var_name)
        #var_ids[m]=vi
    for subj in subjects:
        img_code = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subj)
        sphere = geom_db.load_sphere(roi_id,subj)
        if sphere is None:
            continue
        r,x,y,z = sphere
        for m in measures:
            img = measures[m]
            #var_id = var_ids[m]
            try:
                v = aggregate_in_roi(reader,img_code,(x,y,z),r,space,img)
                print "%s \t %s \t %.3g"%(var_name,subj,v)
                #tabular_data.updata_variable_value(var_id,subj,v)
            except Exception as e:
                print e.message


if __name__ == "__main__":
    roi2db(25)



