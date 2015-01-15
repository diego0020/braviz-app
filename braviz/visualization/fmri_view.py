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


"""Contains utilities for displaying fMRI images"""

from __future__ import division

import vtk
from braviz.readAndFilter.cache import memoize

__author__ = 'Diego'



class blend_fmri_and_mri(vtk.vtkImageBlend):
    """
    Class that blends an fMRI t-score map with a MRI image

    .. deprecated:: 3.0b
        Use :class:`fMRI_blender` instead

    Use methods *GetOutput* and *GetOutputPort* to extract the output
    """
    def __init__(self,fmri_img,mri_img,window=2000,level=1000,alfa=True,threshold=3):
        """
        Creates a blend object

        If alfa is ``True`` the opacity function will look like a "v", being zero at zero, and one at plus and
        minus threshold.

        Args:
            fmri_img (vtkImageData) : t-score image
            mri_img (vtkImageData) : Structural image
            window (float) : Window for structural image
            level (float) : level for structural image
            alfa (bool) : If True colors of t-score map will fade below *threshold*
            threshold (float) : Value at which colors start to fade (invisible at zero)
        """

        fmri_mapper = vtk.vtkImageMapToColors()
        fmri_mapper.SetInputData(fmri_img)
        fmri_lut=get_fmri_lut(alfa, threshold)
        fmri_mapper.SetLookupTable(fmri_lut)

        mri_mapper = vtk.vtkImageMapToWindowLevelColors()
        mri_mapper.SetInputData(mri_img)
        mri_lut = vtk.vtkWindowLevelLookupTable()
        mri_lut.Build()
        mri_mapper.SetLookupTable(mri_lut)

        mri_lut.SetWindow(window)
        mri_lut.SetLevel(level)

        if alfa is True:
            self.AddInputConnection(mri_mapper.GetOutputPort())
            self.AddInputConnection(fmri_mapper.GetOutputPort())
            self.SetOpacity(0, 1.0)
            self.SetOpacity(1, 0.8)
        else:
            self.AddInputConnection(fmri_mapper.GetOutputPort())
            self.AddInputConnection(mri_mapper.GetOutputPort())
            self.SetOpacity(0, 0.5)
            self.SetOpacity(1, 0.5)
        self.Update()
        self.fmri_lut=fmri_lut
        self.fmri_mapper=fmri_mapper
        self.mri_mapper=mri_mapper
        self.mri_lut = mri_lut
        self.alfa=alfa

    def change_imgs(self,mri_img, fmri_img):
        """
        Set new MRI and fMRI images

        Args:
            mri_img (vtkImageData) : Structural image data
            fmri_img (vtkImageData) : fMRI t-score image
        """
        self.fmri_mapper.SetInputData(fmri_img)
        self.mri_mapper.SetInputData(mri_img)
        self.Update()

    def change_threshold(self,threshold):
        """
        Change the threshold for displaying the fMRI scores

        Args:
            threshold (float) : Minimum magnitude at which the values are displayed
        """
        self.fmri_lut = get_fmri_lut(self.alfa,threshold)
        self.fmri_mapper.SetLookupTable(self.fmri_lut)
        self.Update()

#Usually the same function will be used throughout the application
@memoize
def get_fmri_lut(alpha=False,threshold=0,n_pts=200):
    """
    Returns a standard look up table for fMRI data

    If alpha is True, the opacity of the colors below the threshold will be less than one,
    more precisely, the opacity will be a ramp from 0 to 1 between 0 and the threshold

    Args:
        alpha (bool) : If True use a lookup table
        threshold (float) : Value at which color starts to fade (lower opacity) if alpha is True
            minimum value shown
        n_pts (int) : Number of points for the lookup table

    Returns:
        vtkLookuptable
    """

    color_interpolator = vtk.vtkColorTransferFunction()
    color_interpolator.ClampingOn()
    color_interpolator.SetColorSpaceToLab()
    color_interpolator.SetRange(-7, 7)
    color_interpolator.Build()
    #                                x   ,r   ,g   , b
    color_interpolator.AddRGBPoint(-9.0, 0.0, 1.0, 0.0)
    color_interpolator.AddRGBPoint(-4.5, 0.0, 1.0, 1.0)
    color_interpolator.AddRGBPoint(0.0, 0.2, 0.2, 0.2)
    color_interpolator.AddRGBPoint(4.5, 1.0, 0.0, 0.0)
    color_interpolator.AddRGBPoint(9.0, 1.0, 1.0, 0.0)

    if alpha is False:
        return color_interpolator

    fmri_lut = vtk.vtkLookupTable()
    fmri_lut.SetTableRange(-7.0, 7.0)
    fmri_lut.SetNumberOfColors(n_pts+1)
    fmri_lut.Build()
    for i in xrange(n_pts+1):
        s = -7 + 14 * i / n_pts
        if threshold<=0 or (abs(s)>=threshold):
            color = list(color_interpolator.GetColor(s)) + [1.0]
        else:
            color = list(color_interpolator.GetColor(s)) + [abs(s) / threshold]
        # print "%f : %s"%(s,color)
        fmri_lut.SetTableValue(i, color)

    return fmri_lut


class time_slice_viewer(vtk.vtkImageSlice):
    """
    Class for displaying a single slice of a time-moment in BOLD time series
    """
    def __init__(self,orientation=0):
        """
        Create the bold viewer

        Args:
            Orientation (int):  0:x , 1:y, 2:z
        """
        slice_mapper = vtk.vtkImageSliceMapper()
        slice_mapper.SetOrientation(orientation)
        self.SetMapper(slice_mapper)


        self.SetVisibility(0)

        image_property = vtk.vtkImageProperty()
        self.SetProperty(image_property)

        image_property.SetColorWindow(2000)
        image_property.SetColorLevel(1000)

        self.slice_mapper=slice_mapper
        self.TR=1
        self.spatial_slice=0
        self.origin=0
        self.spacing=-2
        self.orientation=orientation

    def set_time_point(self,time):
        """
        Set the time point at which the time series should be sampled

        Args:
            time (float) : Time in seconds of the volume of interest
        """
        TR=self.TR
        space_slice=self.spatial_slice
        position=[0,0,0]
        position[self.orientation]= -1 * TR * time + self.spacing * space_slice
        self.SetPosition(position)
        self.slice_mapper.SetSliceNumber(time)

    def set_input(self,input_data,spatial_pos=0,time=0,orientation=0):
        """
        Sets the input 4D image, the position across the perpendicular axis, the time point and the orientation

        Args:
            input_data (vtkImageData) : bold 4d image
            spatial_pos (int) : index of the slice along the perpendicular axis
            time (float) : time point of interest
            Orientation (int):  0:x , 1:y, 2:z

        """
        self.slice_mapper.SetInputData(input_data)
        spacing=input_data.GetSpacing()
        self.TR=spacing[orientation]
        self.spatial_slice=spatial_pos
        self.orientation=orientation
        self.slice_mapper.SetOrientation(orientation)
        self.set_time_point(time)


    def set_window_level(self,window,level):
        """
        Sets window and level for the display image

        Args:
            window (float) : window value
            level (float) : level value
        """
        image_property = self.GetProperty()
        image_property.SetColorWindow(window)
        image_property.SetColorLevel(level)

    def set_z_spacing(self,spacing):
        """
        spacing in perpendicular axis, used to position the resulting slice in the right place

        Args:
            spacing (float) : Image spacing in the perpendicular axis
        """
        self.spacing=spacing


class fMRI_blender(object):
    """
    Blend an fMRI map with an structural image
    """
    def __init__(self):
        """
        Creates the blender class
        """
        self.blend = vtk.vtkImageBlend()
        self.color_mapper2 = vtk.vtkImageMapToColors()
        self.color_mapper1 = vtk.vtkImageMapToWindowLevelColors()
        self.blend.AddInputConnection(self.color_mapper1.GetOutputPort())
        self.blend.AddInputConnection(self.color_mapper2.GetOutputPort())
        self.blend.SetOpacity(0, 1)
        self.blend.SetOpacity(1, .5)

    def set_luts(self, mri_lut, fmri_lut):
        """
        Set lookuptables for both images

        Args:
            mri_lut (vtkWindowLevelLookupTable) : Lookuptable for structural image
            fmri_lut (vtkScalarsToColors) : t-score image lookuptable

        """
        self.color_mapper1.SetLookupTable(mri_lut)
        self.color_mapper2.SetLookupTable(fmri_lut)

    def set_images(self, mri_image, fmri_image):
        """
        Sets structural and fMRI images

        Args:
            mri_image (vtkImageData) : structural image
            fmri_image (vtkImageData) : t-score image

        Returns:
            Blended vtkImageData
        """
        self.color_mapper1.SetInputData(mri_image)
        self.color_mapper2.SetInputData(fmri_image)
        self.blend.Update()
        return self.blend.GetOutput()

    def get_blended_img(self):
        """
        Get blended image

        Returns:
            Blended vtkImageData
        """
        return self.blend.GetOutput()