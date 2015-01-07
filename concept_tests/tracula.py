from __future__ import division
import braviz
import nibabel as nib
import numpy as np
import os
import vtk
import logging
import struct
from scipy import ndimage
from itertools import izip
from vtk.util import numpy_support
from braviz.readAndFilter.transforms import applyTransform

__author__ = 'Diego'

braviz.utilities.configure_console_logger("tracula")



assert braviz.readAndFilter.PROJECT == "kmc400"
SUBJ = 119
THRESHOLD = 0.2

reader = braviz.readAndFilter.BravizAutoReader()

data_dir = os.path.join(reader.get_data_root(),"freeSurfer_Tracula","%s"%SUBJ,"dpath")
tracks_file = "merged_avg33_mni_bbr.mgz"
tracks_full_file = os.path.join(data_dir,tracks_file)

tracks_img = nib.load(tracks_full_file)
affine = tracks_img.get_affine()
img_data = tracks_img.get_data()

def numpy2vtk_img(d):
    """Transform a 3d numpy array into a vtk image data object"""
    data_type = d.dtype
    importer = vtk.vtkImageImport()
    assert isinstance(d,np.ndarray)

    importer.SetDataScalarTypeToDouble()
        #======================================
    dstring = d.flatten(order='F').tostring()
    if data_type.byteorder == '>':
        #Fix byte order
        dflat_l = d.flatten(order='F').tolist()
        format_string = '<%id' % len(dflat_l)
        dstring = struct.pack(format_string, *dflat_l)
        #importer.SetDataScalarTypeToInt()
    importer.SetNumberOfScalarComponents(1)
    importer.CopyImportVoidPointer(dstring, len(dstring))
    dshape = d.shape
    importer.SetDataExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.SetWholeExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.Update()
    imgData = importer.GetOutput()
    #return imgData
    out_img = vtk.vtkImageData()
    out_img.DeepCopy(imgData)
    return out_img

#HACK to force creation of lut
reader.get("model",SUBJ,name="CSF",color=True)
labels = dict(izip(reader.free_surfer_labels.itervalues(),reader.free_surfer_labels.iterkeys()))
colors = reader.free_surfer_LUT
viewer = braviz.visualization.simpleVtkViewer()

for i in xrange(img_data.shape[3]):
    img_0 = img_data[:,:,:,i]
    vtk_img = numpy2vtk_img(img_0)
    vtk_img2 = applyTransform(vtk_img,np.linalg.inv(affine))



    smooth = vtk.vtkImageGaussianSmooth()
    smooth.SetDimensionality(3)
    smooth.SetStandardDeviation(1)
    smooth.SetInputData(vtk_img2)
    smooth.Update()

    print smooth.GetOutput().GetScalarRange()
    maxi_val=smooth.GetOutput().GetScalarRange()[1]
    thr = maxi_val*0.2
    contours = vtk.vtkContourFilter()
    contours.SetInputConnection(smooth.GetOutputPort())
    contours.SetNumberOfContours(1)
    contours.SetValue(0,thr)
    contours.Update()

    cont = contours.GetOutput()

    cont2 = reader.transform_points_to_space(cont,"diff",SUBJ,inverse=True)

    ac = viewer.addPolyData(cont)
    key = str(5100+i)
    key2 = str(5200+i)
    label = labels[key]
    label2 = labels[key2]
    col = colors[label]
    print label,col
    print label2, thr
    print

    c2 = map(lambda x:x*255,col[:3])
    mp = ac.GetMapper()
    mp.ScalarVisibilityOff()
    ac.GetProperty().SetColor((255,0,0))

#viewer.addImg(vtk_img2)

fa_img = reader.get("MRI",SUBJ,space="world",format="vtk")
viewer.addImg(fa_img)
viewer.start()