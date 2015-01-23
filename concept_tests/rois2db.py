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
    subjects = [ 8, 9, 15, 19, 25, 29, 31, 35, 44, 51, 53, 54, 56, 64, 65, 69, 71, 72, 73, 75, 83, 90, 93, 95, 107, 108, 113, 119, 121, 123, 124, 125, 128, 129, 134, 138, 141, 143, 144, 145, 149, 151, 153, 154, 156, 157, 161, 165, 172, 173, 175, 176, 177, 182, 185, 186, 195, 197, 198, 201, 202, 205, 208, 210, 212, 216, 219, 221, 225, 227, 230, 231, 232, 235, 237, 253, 256, 259, 261, 263, 264, 266, 277, 288, 292, 293, 300, 301, 304, 307, 310, 312, 313, 314, 319, 320, 322, 327, 331, 332, 333, 344, 346, 348, 353, 355, 356, 357, 358, 364, 369, 371, 374, 381, 390, 396, 399, 402, 409, 413, 416, 417, 423, 424, 426, 427, 429, 431, 432, 440, 452, 456, 458, 464, 469, 472, 478, 480, 483, 484, 485, 491, 496, 499, 504, 517, 526, 532, 535, 536, 537, 542, 544, 545, 547, 548, 549, 552, 566, 568, 576, 577, 579, 580, 592, 593, 595, 598, 599, 600, 602, 610, 611, 615, 616, 619, 623, 625, 630, 631, 645, 650, 651, 662, 665, 670, 675, 678, 684, 686, 689, 691, 694, 696, 712, 715, 734, 739, 748, 752, 754, 761, 765, 769, 783, 784, 786, 789, 790, 791, 795, 799, 804, 806, 815, 818, 821, 829, 840, 841, 848, 850, 861, 863, 868, 869, 874, 876, 877, 878, 879, 884, 891, 892, 893, 894, 898, 905, 906, 912, 913, 914, 918, 928, 934, 935, 939, 940, 942, 953, 954, 965, 966, 971, 982, 984, 992, 994, 996, 1005, 1006, 1021, 1026, 1039, 1049, 1063, 1076, 1077, 1212, 1213, 1218, 1221, 1224, 1227, 1232, 1234, 1237, 1239, 1242, 1244, 1247, 1249, 1251, 1253, 1260, 1262, 1265, 1267, 1268, 1269, 1271, 1278, 1283, 1291, 1304, 1318, 1320, 1322, 1326, 1333, 1336, 1337, 1338, 1340, 1357, ]
    for s in subjects:
        roi2db(rois,s)



