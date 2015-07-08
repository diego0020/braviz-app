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

from __future__ import division, print_function
from braviz.utilities import set_pyqt_api_2
set_pyqt_api_2()

import braviz
import braviz.utilities
from braviz.interaction import descriptors, structure_metrics
import sqlite3
import os
import logging
from multiprocessing import Pool
__author__ = 'Diego'


def create_db(path):
    conn = sqlite3.connect(path)
    q = """CREATE TABLE IF NOT EXISTS descriptors
        (subject integer not null,
        structure text not null,
        volume real,
        area real,
        d1 real,
        d2 real,
        d3 real,
        primary key (subject,structure)
        )
        """
    conn.execute(q)
    conn.commit()


def get_descriptor(subj, structure, aseg, reader):
    vol = reader.get("MODEL", subj, volume=True, name=structure)
    area = structure_metrics.get_struct_metric(reader, structure, subj, "area")
    label = int(reader.get("MODEL", subj, name=structure, label=True))
    d1, d2, d3 = descriptors.get_descriptors(aseg, (label,))
    return vol, area, d1, d2, d3


def get_agg_descriptor(subj, structures, aseg, reader):
    vols = []
    labels = []
    for s in structures:
        vols.append(reader.get("MODEL", subj, volume=True, name=s))
        labels.append(int(reader.get("MODEL", subj, name=s, label=True)))
    d1, d2, d3 = descriptors.get_descriptors(aseg, labels)
    vol = sum(vols)
    return vol, float("nan"), d1, d2, d3


def save_descs_in_db(conn, subj, name, descs):
    vals = (int(subj), name, descs[0], descs[1], descs[2], descs[3], descs[4])
    q = "INSERT OR REPLACE into descriptors VALUES (?,?, ?,?, ?,?,?)"
    conn.execute(q, vals)
    conn.commit()


def save_subj_descs(subj):
    print("subject = %s" % subj)
    braviz.utilities.configure_console_logger("descriptors")
    log = logging.getLogger(__name__)
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=1000)
    db_name = os.path.join(reader.get_dyn_data_root(), "descriptors.sqlite")
    try:
        structs = reader.get("MODEL", subj, index=True)
        aseg = reader.get("LABEL",subj, name="APARC", space="world")
        #wmaseg = reader.get("WMPARC",subj,space="world")
    except Exception as e:
        log.exception(e.message)
        return
    for s in structs:

        try:
            if s.startswith("wm-"):
                descs = None
                # skip wm
                #d1 =  get_descriptor(subj,s,wmaseg,reader)
            elif s.startswith("ctx-"):
                # continue
                # not skip ctx
                descs = get_descriptor(subj, s, aseg, reader)
            else:
                descs = get_descriptor(subj, s, aseg, reader)

        except Exception as e:
            log.exception(e.message)
            descs = None

        if descs is not None:
            try:
                conn = sqlite3.connect(
                    db_name, timeout=600, isolation_level="EXCLUSIVE")
                save_descs_in_db(conn, subj, s, descs)
                conn.close()
            except Exception as e:
                log.exception(e)

    cc = ['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior',
          'CC_Mid_Posterior', 'CC_Posterior']
    try:
        d2 = get_agg_descriptor(subj, cc, aseg, reader)
        conn = sqlite3.connect(
            db_name, timeout=600, isolation_level="EXCLUSIVE")
        save_descs_in_db(conn, subj, "CC-Full", d2)
        conn.close()
    except Exception as e:
        log.exception(e)
    reader.clear_mem_cache()


def save_for_all(processes=1):
    reader = braviz.readAndFilter.BravizAutoReader(max_cache=500)
    ids = reader.get('ids')
    #ids = [150, 155, 382, 441, 758, 820, 932]
    create_db(os.path.join(reader.get_dyn_data_root(), "descriptors.sqlite"))
    del reader
    if processes <= 1:
        for s in ids:
            save_subj_descs(s)
    else:
        proc_pool = Pool(processes=processes)
        proc_pool.map(save_subj_descs, ids)

if __name__ == "__main__":
    import sys
    braviz.utilities.configure_logger_from_conf("descriptors")
    procs = 2
    if len(sys.argv) >= 2:
        procs = int(sys.argv[1])
    save_for_all(procs)
