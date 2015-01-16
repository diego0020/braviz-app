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


from __future__ import division

import vtk
import numpy as np
from vtk.numpy_interface import dataset_adapter as dsa

import nibabel as nib


import braviz
from braviz.readAndFilter import geom_db


__author__ = 'da.angulo39'


def export_roi(subject, roi_id, space, out_file, reader=None):
    """
    Save an image from a roi into a file

    Args:
        subject : Subject id
        roi_id : ROI database id
        space (str) : Coordinate system for output image
        out_file (str) : Path for the output file
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data, if None, the
            one returned by :func:`braviz.readAndFilter.BravizAutoReader` will be used

    """

    sphere_img,affine = generate_roi_image(subject,roi_id,space,reader)
    nib_image = nib.Nifti1Image(sphere_img,affine)
    nib_image.update_header()
    nib_image.to_filename(out_file)



def generate_roi_image(subject, roi_id, space, reader=None,out_format="nii"):
    """
    Generates an image representation of an spherical ROI

    Args:
        subject : Subject id
        roi_id : ROI database id
        space (str) : Coordinate system for output image
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object used to read the data, if None, the
            one returned by :func:`braviz.readAndFilter.BravizAutoReader` will be used
        format (str) : By default a numpy array, affine matrix pair is returned. If ``out_format="vtk"``,
            a vtkImageData object is returned

    Returns:
        A numpy array and a numpy affine transform by default. If ``out_format="vtk"`` a vtkImageData
    """
    if reader is None:
        reader = braviz.readAndFilter.BravizAutoReader()

    r, x, y, z = geom_db.load_sphere(roi_id, subject)
    sphere_space = geom_db.get_roi_space(roi_id=roi_id)
    sphere_src = vtk.vtkSphereSource()
    sphere_src.SetRadius(r)
    sphere_src.SetPhiResolution(30)
    sphere_src.SetThetaResolution(30)
    sphere_src.SetCenter(x,y,z)
    sphere_src.Update()
    sphere_pd = sphere_src.GetOutput()
    sphere_world = reader.transform_points_to_space(sphere_pd,sphere_space,subject,inverse=True)
    sphere_out = reader.transform_points_to_space(sphere_world,space,subject,inverse=False)

    black_image = reader.get("MRI",subject,space=space,format="vtk")
    nimg = dsa.WrapDataObject(black_image)

    #zero the image
    zero_array=nimg.PointData['ImageScalars'].dot(0).astype(np.uint8)
    black_image.GetPointData().RemoveArray('ImageScalars')
    nimg.PointData.append(zero_array,'ImageScalars')
    black_image.GetPointData().SetActiveScalars("ImageScalars")

    pol2sten = vtk.vtkPolyDataToImageStencil()
    pol2sten.SetInputData(sphere_out)
    pol2sten.SetOutputOrigin(black_image.GetOrigin())
    pol2sten.SetOutputSpacing(black_image.GetSpacing())
    pol2sten.SetOutputWholeExtent(black_image.GetExtent())

    pol2sten.Update()

    imgstenc = vtk.vtkImageStencil()
    imgstenc.SetInputData(black_image)
    imgstenc.SetStencilConnection(pol2sten.GetOutputPort())
    imgstenc.SetBackgroundValue(255)
    imgstenc.SetReverseStencil(True)
    imgstenc.Update()

    sphere_img = imgstenc.GetOutput()

    if out_format.lower() == "vtk":
        return sphere_img

    out_nimg = dsa.WrapDataObject(sphere_img)
    out_data = np.array(out_nimg.GetPointData()["ImageScalars"].reshape(sphere_img.GetDimensions(), order="F"))
    affine=np.eye(4)
    affine[0:3,3]=sphere_img.GetOrigin()
    affine[0,0],affine[1,1],affine[2,2] = sphere_img.GetSpacing()
    return out_data, affine




if __name__ == "__main__":
    from braviz.readAndFilter import images, config_file
    from braviz.visualization import simple_vtk
    import nibabel as nib

    subj = config_file.get_apps_config().get_default_subject()
    export_roi(subj,1,"world","/home/diego/test.nii")

    nimg = nib.load("/home/diego/test.nii")
    vimg = images.nibNii2vtk(nimg)
    v = braviz.visualization.simple_vtk.SimpleVtkViewer()
    v.addImg(vimg)
    v.start()

