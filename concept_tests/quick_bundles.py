__author__ = 'Diego'

import dipy
import braviz
import numpy as np
reader = braviz.readAndFilter.BravizAutoReader()
tracts = reader.get("FIBERS","093")
tracts.GetNumberOfLines()
def line_to_array(line):
    n_pts = line.GetNumberOfPoints()
    pts = line.GetPoints()
    array = np.zeros((n_pts,3))
    for i in xrange(n_pts):
        array[i,:] = pts.GetPoint(i)
    return array

n_lines = tracts.GetNumberOfCells()
np_tracts = [line_to_array(tracts.GetCell(i)) for i in xrange(n_lines)]

import dipy.segment.quickbundles
bundles = dipy.segment.quickbundles.QuickBundles(np_tracts,10,18)
print bundles.total_clusters
partitions = bundles.partitions()
in_cluster = bundles.label2tracksids(0)
bundles.remove_small_clusters(5)

