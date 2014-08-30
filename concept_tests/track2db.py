from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, bundles_db
from braviz.interaction.structure_metrics import get_scalar_from_fiber_ploydata


__author__ = 'da.angulo39'

def track2db(track_id):
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=1000)
    track_name = bundles_db.get_bundle_name(track_id)
    measures = {"fa":("fa_p","mean_color"),
                "md":("md_p","mean_color"),
                "length":("fa_p","mean_length"),
                "count":("fa_p","number")
               }
    subjects = tabular_data.get_subjects()
    var_ids = {}
    for m in measures:
        var_name = "bvz_"+track_name+"_"+m
        vi=tabular_data.register_new_variable(var_name)
        var_ids[m]=vi
    for subj in subjects:
        img_code = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subj)
        for m in measures:
            scalar,operation = measures[m]
            var_id = var_ids[m]
            try:
                fibs = reader.get("fibers",img_code,db_id=track_id,scalars=scalar)
                v = get_scalar_from_fiber_ploydata(fibs,operation)
                print "%s \t %s \t %.3g"%(var_id,subj,v)
                tabular_data.updata_variable_value(var_id,subj,v)
            except Exception:
                pass


if __name__ == "__main__":
    tracks = (4,5,6,7,9,10,11,12,13,14,15)
    for t in tracks:
        try:
            track2db(t)
        except Exception:
            pass


