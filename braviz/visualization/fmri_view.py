"""Contains utilities for displaying fMRI images"""

from __future__ import division
import functools

import vtk

__author__ = 'Diego'

def memoize(obj):
    """A wrapper that saves the return values for a function,
    and returns them if the funcion is called again with the same arguments"""
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer

class blend_fmri_and_mri(vtk.vtkImageBlend):
    """Class that blends an fMRI t-score map with a matchin MRI image"""
    def __init__(self,fmri_img,mri_img,window=2000,level=1000,alfa=True,threshold=3):
        """Returns a blend object, to which you can apply
        GetOutput: To get the resulting image
        GetOutputPort: To connect to a vtk pipeline"""

        fmri_mapper = vtk.vtkImageMapToColors()
        fmri_mapper.SetInputData(fmri_img)
        fmri_lut=get_fmri_lut(threshold,alfa)
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

    def change_imgs(self,mri_img,fmri_img):
        """Set new MRI and fMRI images"""
        self.fmri_mapper.SetInputData(fmri_img)
        self.mri_mapper.SetInputData(mri_img)
        self.Update()
    def change_threshold(self,threshold):
        """Change the threshold for displaying the fMRI scores"""
        self.fmri_lut=get_fmri_lut(threshold,self.alfa)
        self.fmri_mapper.SetLookupTable(self.fmri_lut)
        self.Update()

#Usually the same function will be used throughout the application
@memoize
def get_fmri_lut(threshold=0,alpha=False,n_pts=200):
    """Returns a standard look up table for fMRI data
    If alpha is True, the opacity of the colors below the threshold will be less than one,
    more precisely, the opacity will be a line from 0 to 1 between 0 and the threshold"""

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
    """Class for displaying a single slice of a time-moment in BOLD time series"""
    def __init__(self,orientation=0):
        """Orientation is 0:x , 1:y, 2:z """
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
        """
        TR=self.TR
        space_slice=self.spatial_slice
        position=[0,0,0]
        position[self.orientation]= -1 * TR * time + self.spacing * space_slice
        self.SetPosition(position)
        self.slice_mapper.SetSliceNumber(time)

    def set_input(self,input_data,spatial_pos=0,time=0,orientation=0):
        """Sets the input 4D image, the position across the perpendicular axis, the time point and the orientation """
        self.slice_mapper.SetInputData(input_data)
        spacing=input_data.GetSpacing()
        self.TR=spacing[orientation]
        self.spatial_slice=spatial_pos
        self.orientation=orientation
        self.slice_mapper.SetOrientation(orientation)
        self.set_time_point(time)


    def set_window_level(self,window,level):
        """Sets window and level for the display image"""
        image_property = self.GetProperty()
        image_property.SetColorWindow(window)
        image_property.SetColorLevel(level)
    def set_z_spacing(self,spacing):
        """spacing in perpendicular axis, used to position the resulting slice in the right place"""
        self.spacing=spacing
