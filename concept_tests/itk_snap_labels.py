from __future__ import division
__author__ = 'Diego'

import os

FREE_SURFER_LUT=r"C:\Users\Diego\Documents\kmc40-db\KAB-db\FreeSurferColorLUT.txt"
BASE_LABELS=r"C:\Users\Diego\Documents\itk_snap_test\snap3b.txt"

os.chdir(os.path.dirname(BASE_LABELS))


out_labels=os.path.basename(BASE_LABELS)[:-4]+"_out.txt"


#build free surfer labels dict
labels_dict={}

with open(FREE_SURFER_LUT) as luts_file:
    for l in luts_file:
        if l.startswith('#'):
            continue
        words=l.split()
        if len(words)==6:
            num, label, r,g,b,a = words
            labels_dict[num]=(num,r,g,b,label)



#translate labels file
with open(out_labels,'w') as out_file:
    with open(BASE_LABELS) as base_file:
        for l in base_file:
            if l.startswith('#'):
                out_file.write(l)
            else:
                words=l.split()
                num=words[0]
                info=labels_dict.get(num)
                if info is None:
                    out_file.write(l)
                else:
                    #  n  r  g  b  a v i l
                    s='%s %s %s %s 1 1 1 "%s"\n'%info
                    out_file.write(s)

