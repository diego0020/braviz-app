from __future__ import division
import braviz
from braviz.readAndFilter import tabular_data, bundles_db, user_data
from braviz.interaction.structure_metrics import get_scalar_from_fiber_ploydata
from braviz.utilities import configure_console_logger
from multiprocessing import Pool
import sqlite3
import logging
import time

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

    tuples = []
    measures = {"fa":("fa_p","mean_color"),
                "md":("md_p","mean_color"),
                "length":("fa_p","mean_length"),
                "count":("fa_p","number")
               }

    var_ids = {}
    var_names = {}

    for track_id in tracks:
        track_name = bundles_db.get_bundle_name(track_id)
        for m in measures:
            var_name = "bvz_"+track_name+"_"+m
            vi=tabular_data.get_var_idx(var_name)
            var_ids[(track_id,m)]=vi
            var_names[(track_id,m)]=var_name

    for subj in subjects:
        for m in measures:
            for track_id in tracks:
                img_code = subj
                scalar,operation = measures[m]
                var_id = var_ids[(track_id,m)]
                var_name=var_names[(track_id,m)]
                try:
                    fibs = reader.get("fibers",img_code,db_id=track_id,scalars=scalar)
                    v = get_scalar_from_fiber_ploydata(fibs,operation)
                    print "%s \t %s \t %.3g"%(var_name,subj,v)
                    tuples.append((var_id,subj,v))
                except Exception as e:
                    log.exception(e)
        reader.clear_mem_cache()

    written = False
    while not written:
        try:
            tabular_data.update_multiple_variable_values(tuples)
        except Exception as e:
            log.exception(e)
            print "sleeping"
            time.sleep(10)
        else:
            written = True

def proc_batch(tracks, b):
    log = logging.getLogger(__name__)

    try:
        track2db(tracks,b)
    except Exception as e:
        log.exception(e)
        return 1
    return 0

def get_variables(tracks):
    name2code = {}
    for t in tracks:
        track_name = bundles_db.get_bundle_name(t)
        measures = {"fa":("fa_p","mean_color"),
                    "md":("md_p","mean_color"),
                    "length":("fa_p","mean_length"),
                    "count":("fa_p","number")
                   }
        for m in measures:
            var_name = "bvz_"+track_name+"_"+m
            vi=tabular_data.get_var_idx(var_name)
            name2code[var_name]=vi
            if vi is None:
                print "-\t %s"%var_name
            else:
                print "%d:\t %s"%(vi,var_name)
    return name2code

def reset_variables(vars):
    for var_name,var_code in vars.iteritems():
        if var_code is not None:
            #delete old variable
            tabular_data.recursive_delete_variable(var_code)
        tabular_data.register_new_variable(var_name)

if __name__ == "__main__":

    configure_console_logger("tracks2db")
    #all_sample = [ 8, 9, 15, 19, 25, 29, 31, 35, 44, 51, 53, 54, 56, 64, 65, 69, 71, 72, 73, 75, 83, 90, 93, 95, 107, 108, 113, 119, 121, 123, 124, 125, 128, 129, 134, 138, 141, 143, 144, 145, 149, 151, 153, 154, 156, 157, 161, 165, 172, 173, 175, 176, 177, 182, 185, 186, 195, 197, 198, 201, 202, 205, 208, 210, 212, 216, 219, 221, 225, 227, 230, 231, 232, 235, 237, 253, 256, 259, 261, 263, 264, 266, 277, 288, 292, 293, 300, 301, 304, 307, 310, 312, 313, 314, 319, 320, 322, 327, 331, 332, 333, 344, 346, 348, 353, 355, 356, 357, 358, 364, 369, 371, 374, 381, 390, 396, 399, 402, 409, 413, 416, 417, 423, 424, 426, 427, 429, 431, 432, 440, 452, 456, 458, 464, 469, 472, 478, 480, 483, 484, 485, 491, 496, 499, 504, 517, 526, 532, 535, 536, 537, 542, 544, 545, 547, 548, 549, 552, 566, 568, 576, 577, 579, 580, 592, 593, 595, 598, 599, 600, 602, 610, 611, 615, 616, 619, 623, 625, 630, 631, 645, 650, 651, 662, 665, 670, 675, 678, 684, 686, 689, 691, 694, 696, 712, 715, 734, 739, 748, 752, 754, 761, 765, 769, 783, 784, 786, 789, 790, 791, 795, 799, 804, 806, 815, 818, 821, 829, 840, 841, 848, 850, 861, 863, 868, 869, 874, 876, 877, 878, 879, 884, 891, 892, 893, 894, 898, 905, 906, 912, 913, 914, 918, 928, 934, 935, 939, 940, 942, 953, 954, 965, 966, 971, 982, 984, 992, 994, 996, 1005, 1006, 1021, 1026, 1039, 1049, 1063, 1076, 1077, 1212, 1213, 1218, 1221, 1224, 1227, 1232, 1234, 1237, 1239, 1242, 1244, 1247, 1249, 1251, 1253, 1260, 1262, 1265, 1267, 1268, 1269, 1271, 1278, 1283, 1291, 1304, 1318, 1320, 1322, 1326, 1333, 1336, 1337, 1338, 1340, 1357, ]
    #tracks = [4,5,6,7,8,9,10,11,12,13,14,15,19,20,21,22,23,24,28]
    all_sample = tabular_data.get_subjects()
    tracks=[13,14,15,16,18,20,21,22,23,24,25,26,27,28,29,30,31,36,37,38,39,40,43,44,45,46]
    old_vars=get_variables(tracks)
    reset_variables(old_vars)
    new_vars = get_variables(tracks)
    # exit(0)
    log = logging.getLogger(__name__)
    n=6
    n_batches = len(all_sample)//n+1
    batches = [all_sample[i*n:n*(i+1)] for i in xrange(n_batches)]
    from functools import partial
    ini_log = partial(configure_console_logger,"tracks2db")
    proc_tracks_batches = partial(proc_batch,tracks)
    pool = Pool(processes=2,initializer=ini_log)
    pool.map(proc_tracks_batches,batches)


