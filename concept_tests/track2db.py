from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, bundles_db, user_data
from braviz.interaction.structure_metrics import get_scalar_from_fiber_ploydata
from braviz.utilities import configure_console_logger
from multiprocessing import Pool
import sqlite3
import logging

__author__ = 'da.angulo39'

def track2db(tracks,sample=None):
    log = logging.getLogger(__name__)
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=2000)
    if sample is None:
        subjects = tabular_data.get_subjects()
    elif type(sample) == int:
        subjects = user_data.get_sample_data(sample)
    else:
        subjects = sample

    for track_id in tracks:
        track_name = bundles_db.get_bundle_name(track_id)
        measures = {"fa":("fa_p","mean_color"),
                    "md":("md_p","mean_color"),
                    "length":("fa_p","mean_length"),
                    "count":("fa_p","number")
                   }

        var_ids = {}
        var_names = {}
        for m in measures:
            var_name = "bvz_"+track_name+"_"+m
            try:
                vi=tabular_data.register_new_variable(var_name)
            except sqlite3.IntegrityError:
                vi=tabular_data.get_var_idx(var_name)
            var_ids[m]=vi
            var_names[m]=var_name
        for subj in subjects:
            print "================"
            print subj
            try:
                img_code = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subj)
            except Exception:
                img_code = subj
            for m in measures:
                scalar,operation = measures[m]
                var_id = var_ids[m]
                var_name=var_names[m]
                try:
                    fibs = reader.get("fibers",img_code,db_id=track_id,scalars=scalar)
                    v = get_scalar_from_fiber_ploydata(fibs,operation)
                    print "%s \t %s \t %.3g"%(var_name,subj,v)
                    tabular_data.updata_variable_value(var_id,subj,v)
                except Exception as e:
                    log.exception(e)
    reader.clear_cache()

def proc_batch(b):
    log = logging.getLogger(__name__)
    tracks = range(19,26)
    try:
        track2db(tracks,b)
    except Exception as e:
        log.exception(e)
        return 1
    return 0

if __name__ == "__main__":
    configure_console_logger("tracks2db")
    #sample = 8
    #sample = [1026, 939, 517, 526, 15, 19, 535, 536, 537, 29, 542, 544, 545, 548, 549, 689, 552, 44, 861, 51, 1077, 566, 56, 576, 65, 579, 580, 69, 71, 592, 593, 83, 599, 600, 868, 602, 1039, 357, 610, 616, 619, 108, 623, 113, 630, 631, 121, 124, 125, 789, 128, 107, 876, 138, 651, 141, 143, 144, 145, 25, 665, 154, 156, 157, 670, 197, 675, 165, 625, 684, 173, 686, 175, 176, 177, 182, 185, 1212, 195, 1221, 198, 712, 201, 715, 205, 1232, 216, 804, 1242, 219, 221, 734, 225, 227, 1253, 230, 231, 232, 235, 1260, 237, 1265, 754, 761, 253, 256, 769, 263, 266, 783, 784, 984, 1049, 277, 790, 791, 964, 292, 293, 806, 1320, 1326, 815, 818, 307, 1333, 310, 313, 314, 1340, 829, 320, 480, 54, 327, 840, 841, 331, 332, 1357, 848, 344, 346, 1338, 863, 353, 356, 869, 874, 364, 877, 878, 879, 369, 371, 884, 891, 892, 893, 894, 64, 390, 905, 906, 151, 912, 918, 153, 409, 413, 416, 417, 934, 423, 426, 427, 940, 429, 942, 431, 432, 935, 440, 953, 954, 928, 452, 966, 971, 333, 469, 982, 472, 478, 992, 483, 484, 485, 491, 1005, 1006, 765, 595, 504, 119, 1021]
    all_sample = [1026, 939, 517, 526, 15, 535, 536, 537, 29, 542,
              544, 545, 548, 549, 689, 552, 44, 861, 51, 1077,
              566, 56, 576, 65, 579, 580, 69, 71, 592, 593,
              83, 599, 600, 868, 602, 1039, 357, 610, 616, 619,
              108, 623, 113, 630, 631, 121, 124, 125, 789, 128,
              107, 876, 138, 651, 141, 143, 144, 145, 25, 665,
              154, 156, 157, 670, 197, 675, 165, 625, 684, 173,
              686, 175, 176, 177, 182, 185, 1212, 195, 1221, 198,
              712, 201, 715, 205, 1232, 216, 804, 1242, 219, 221,
              734, 225, 227, 1253, 230, 231, 232, 235, 1260, 237,
              1265, 754, 761, 253, 256, 769, 263, 266, 783, 784,
              984, 1049, 277, 790, 791, 964, 292, 293, 806, 1320,
              1326, 815, 818, 307, 1333, 310, 313, 314, 1340, 829,
              320, 480, 54, 327, 840, 841, 331, 332, 1357, 848,
              344, 346, 1338, 863, 353, 356, 869, 874, 364, 877,
              878, 879, 369, 371, 884, 891, 892, 893, 894, 64,
              390, 905, 906, 151, 912, 918, 153, 409, 413, 416,
              417, 934, 423, 426, 427, 940, 429, 942, 431, 432,
              935, 440, 953, 954, 928, 452, 966, 971, 333, 469,
              982, 472, 478, 992, 483, 484, 485, 491, 1005, 1006,
              765, 595, 504, 119, 1021]
    #tracks = (17,18,19,20)

    log = logging.getLogger(__name__)
    n=6
    n_batches = len(all_sample)//n+1
    batches = [all_sample[i*n:n*(i+1)] for i in xrange(n_batches)]
    from functools import partial
    ini_log = partial(configure_console_logger,"tracks2db")
    pool = Pool(processes=3,initializer=ini_log)
    pool.map(proc_batch,batches)


