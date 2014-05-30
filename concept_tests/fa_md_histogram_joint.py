from __future__ import division
import matplotlib
matplotlib.use('Qt4Agg')


import braviz
import braviz.readAndFilter.tabular_data as braviz_tab

import numpy as np
from scipy import ndimage
from matplotlib import pyplot as plt

reader = braviz.readAndFilter.BravizAutoReader()

def load_data(image_type):
    #collect all data
    subject_codes = braviz_tab.get_data_frame_by_index(braviz_tab.IMAGE_CODE)
    scalar_list=[]
    for subj in subject_codes.index:
        code = subject_codes["Images_codes"][subj]
        code_str = "{:0>3g}".format(code)
        print code_str
        try:
            image = reader.get(image_type,code_str)
            fibers = reader.get("fibers",code_str,space="world")
        except Exception as e:
            print "not found"
            print e.message
        else:
            affine = image.get_affine()
            iaffine = np.linalg.inv(affine)
            data = image.get_data()
            npoints = fibers.GetNumberOfPoints()
            zeros = np.zeros((npoints,3))
            for i in xrange(npoints):
                coords = fibers.GetPoint(i) + (1,)
                coords = np.dot(iaffine,coords)
                coords = coords[:3]/coords[3]
                zeros[i]=coords
            image_vals = ndimage.map_coordinates(data,zeros.T,order=1)
            scalar_list.append(image_vals)
            print len(scalar_list)
    scalars_array=np.concatenate(scalar_list)
    print scalars_array.shape
    return scalars_array


def get_data(image_type):


    cache_key = "%s-histogram-in-fibers"%image_type
    #try to read from cache
    scalars_array=reader.load_from_cache(cache_key)

    #collect all data
    if scalars_array is None:
        scalars_array = load_data(image_type)
        reader.save_into_cache(cache_key,scalars_array)

    return scalars_array


fa = get_data("FA")

md = get_data("MD")
md*=1e10
sample_size = 10000
sample = np.random.choice(len(fa),sample_size,replace=False)

fa2=fa[sample]
md2=md[sample]

import seaborn as sns
print "plotting...."
sns.jointplot(fa,md,kind="hex",xlim=(0.3,0.9),ylim=(3,12))
#sns.jointplot(fa2,md2,kind="kde",xlim=(0.3,0.9),ylim=(3,12))
print "showing"
plt.show()
print "ciao"