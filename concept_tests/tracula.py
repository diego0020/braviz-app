from __future__ import division
import braviz
import nibabel as nib
import numpy as np
import os
import vtk
import logging
import struct
from itertools import izip
from braviz.readAndFilter import numpy_support

__author__ = 'Diego'

braviz.utilities.configure_console_logger("tracula")



assert braviz.readAndFilter.PROJECT == "kmc400"
SUBJ = 119
THRESHOLD = 30

reader = braviz.readAndFilter.BravizAutoReader()

data_dir = os.path.join(reader.getDataRoot(),"freeSurfer_Tracula","%s"%SUBJ,"dpath")
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
    vtk_img2 = braviz.readAndFilter.applyTransform(vtk_img,np.linalg.inv(affine))

    contours = vtk.vtkContourFilter()
    contours.SetInputData(vtk_img2)
    contours.SetNumberOfContours(1)
    contours.SetValue(0,THRESHOLD)
    contours.Update()

    cont = contours.GetOutput()
    ac = viewer.addPolyData(cont)
    key = str(5100+i)
    label = labels[key]
    col = colors[label]
    print label,col
    c2 = map(lambda x:x*255,col[:3])
    mp = ac.GetMapper()
    mp.ScalarVisibilityOff()
    ac.GetProperty().SetColor(col[:3])

#viewer.addImg(vtk_img2)

fa_img = reader.get("fa",SUBJ,space="diff",format="vtk")
viewer.addImg(fa_img)
viewer.start()