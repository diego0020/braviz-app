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


import sys
from multiprocessing import Pool

import braviz
from braviz.readAndFilter import BravizAutoReader
from braviz.utilities import ignored, configure_logger_from_conf


def clear_cache():
    reader = BravizAutoReader(max_cache=500)
    reader.clear_mem_cache(True)


def populate_cache(subj):
    print "creating cache for subject %s"%subj    
    reader2=BravizAutoReader(max_cache=500)
    #Dartel Transform
    print " %s: Dartel"%subj
    with ignored(Exception):
        reader2.get('MRI',subj,format='vtk',space='dartel')
    with ignored(Exception):
        reader2.get('fibers',subj,space='dartel')
    reader2.clear_mem_cache()


    #FreeSurferSurface
    print " %s: Surfaces"%subj
    surfaces=('pial','white','orig','inflated','sphere')
    #surfaces = []
    hemis=('l','r')
    for s in surfaces:
        for h in hemis:
            with ignored(Exception):
                reader2.get('SURF',subj,name=s,hemi=h)
    #Fibers
    print " %s: Colored Fibers"%subj
    #with ignored(Exception):
    #    reader2.get('fibers',subj,color='fa')
    # with ignored(Exception):
    #     reader2.get('fibers',subj,color='orient')
    # with ignored(Exception):
    #     reader2.get('fibers',subj,color='curv')
    # with ignored(Exception):
    #     reader2.get('fibers',subj,color='y')
    with ignored(Exception):
        reader2.get('fibers',subj,scalars="fa_p")
    with ignored(Exception):
        reader2.get('fibers',subj,scalars="fa_l")
    with ignored(Exception):
        reader2.get('fibers',subj,scalars="md_l")
    with ignored(Exception):
        reader2.get('fibers',subj,scalars="md_p")
    with ignored(Exception):
        reader2.get('fibers',subj,scalars="length")

    waypoints=( 'Brain-Stem','CC_Anterior','CC_Central','CC_Mid_Anterior','CC_Mid_Posterior','CC_Posterior',
                'Left-Cerebellum-Cortex', 'Left-Cerebellum-White-Matter', 'Left-Cerebral-White-Matter',
                'Right-Cerebellum-Cortex', 'Right-Cerebellum-White-Matter', 'Right-Cerebral-White-Matter',
                'ctx-lh-precentral','ctx-rh-precentral','wm-lh-precentral','wm-rh-precentral')
    print " %s: Waypoints"%subj
    for w in waypoints:
        print " %s: Waypoints - %s"%(subj,w)
        with ignored(Exception):
            reader2.get('fibers',subj,waypoint=w)
    print " %s: Done"%subj
    
    #fMRI
    paradigms=reader2.get("fmri",None,index=True)
    for p in paradigms:
        print p
        with ignored(Exception):
            reader2.get('fMRI',subj,format='vtk',name=p,space='world')
        with ignored(Exception):
            reader2.get('MRI',subj,format='vtk',name=p,space='fmri_%s'%p)

    del reader2


def populate_all(processes=1):
    reader=braviz.readAndFilter.BravizAutoReader(max_cache=500)
    ids=reader.get('ids')
    del reader
    if processes<=1:
        for i in ids:
            populate_cache(i)
    else:
        proc_pool=Pool(processes=processes)
        proc_pool.map(populate_cache,ids)

if __name__=='__main__':
    configure_logger_from_conf("populate_cache")
    if len(sys.argv)<2:
        processes=1
    else:
        processes=int(sys.argv[1])
    print "using %d processes"%processes
    populate_all(processes)        