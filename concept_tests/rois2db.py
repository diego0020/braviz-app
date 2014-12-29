from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, geom_db
from braviz.interaction.structure_metrics import AggregateInRoi
from braviz.utilities import configure_console_logger

__author__ = 'da.angulo39'



def roi2db(roi_ids,subj):
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=1000)

    agg_fa = AggregateInRoi(reader)
    agg_md = AggregateInRoi(reader)
    measures = {"fa":agg_fa,"md":agg_md}

    agg_fa.load_image(s,"Talairach","FA")
    agg_md.load_image(s,"Talairach","MD")

    for roi_id in roi_ids:
        roi_name = geom_db.get_roi_name(roi_id)
        space = geom_db.get_roi_space(roi_id=roi_id)
        if space != "Talairach":
            print "skipping "+roi_name
            continue

        for m in measures:
            var_name = "bvz_"+roi_name+"_"+m
            try:
                vi=tabular_data.register_new_variable(var_name)
            except Exception:
                vi=tabular_data.get_var_idx(var_name)
            agg = measures[m]
            img_code = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subj)
            sphere = geom_db.load_sphere(roi_id,subj)
            if sphere is not None:
                r,x,y,z = sphere
                var_id = vi
                try:
                    v = agg.get_value((x,y,z),r)
                    print "%s(%s) \t %s \t %.3g"%(var_name,var_id,subj,v)
                    tabular_data.updata_variable_value(var_id,subj,float(v))
                except Exception as e:
                    print e.message
    reader.clear_mem_cache()

if __name__ == "__main__":
    configure_console_logger("roi2db")
    rois = range(19,31)
    subjects = (15, 19, 25, 29, 44, 51, 54, 56, 64, 65, 69, 71, 83, 107, 108, 113, 119, 121, 124, 125, 128, 138, 141, 143, 144, 145, 151, 153, 154, 156, 157, 165, 173, 175, 176, 177, 182, 185, 195, 197, 198, 201, 205, 216, 219, 221, 225, 227, 230, 231, 232, 235, 237, 253, 256, 263, 266, 277, 292, 293, 307, 310, 313, 314, 320, 327, 331, 332, 333, 344, 346, 353, 356, 357, 364, 369, 371, 390, 409, 413, 416, 417, 423, 426, 427, 429, 431, 432, 440, 452, 469, 472, 478, 480, 483, 484, 485, 491, 504, 526, 535, 536, 537, 542, 548, 549, 552, 566, 576, 579, 580, 592, 593, 595, 599, 600, 602, 610, 616, 619, 623, 625, 630, 631, 651, 665, 670, 675, 684, 686, 689, 712, 715, 734, 754, 761, 769, 783, 784, 789, 790, 791, 804, 806, 815, 818, 829, 840, 841, 848, 861, 863, 868, 869, 874, 876, 877, 878, 879, 884, 893, 894, 905, 906, 912, 918, 928, 934, 935, 939, 940, 942, 954, 966, 971, 982, 984, 1005, 1006, 1021, 1026, 1049, 1077, 1212, 1221, 1232, 1242, 1253, 1260, 1265, 1320, 1326, 1333, 1338, 1340, 1357)
    for s in subjects:
        roi2db(rois,s)



