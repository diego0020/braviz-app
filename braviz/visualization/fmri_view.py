from __future__ import division
import vtk
import functools
__author__ = 'Diego'

def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        if args not in cache:
            cache[args] = obj(*args, **kwargs)
        return cache[args]
    return memoizer

def blend_fmri_and_mri(fmri_img,mri_img,window=2000,level=1000,alfa=True,threshold=3):
    """Retruns a blend object, to which you can apply
    GetOutput: To get the resulting image
    GetOutputPort: To connect to a vtk pipeline"""
    blend = vtk.vtkImageBlend()

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
        blend.AddInputConnection(mri_mapper.GetOutputPort())
        blend.AddInputConnection(fmri_mapper.GetOutputPort())
        blend.SetOpacity(0, 1.0)
        blend.SetOpacity(1, 0.8)
    else:
        blend.AddInputConnection(fmri_mapper.GetOutputPort())
        blend.AddInputConnection(mri_mapper.GetOutputPort())
        blend.SetOpacity(0, 0.5)
        blend.SetOpacity(1, 0.5)
    blend.Update()
    return blend

@memoize
def get_fmri_lut(threshold=0,alpha=False,n_pts=200):

    color_interpolator = vtk.vtkColorTransferFunction()
    color_interpolator.ClampingOn()
    color_interpolator.SetColorSpaceToLab()
    color_interpolator.SetRange(-7, 7)
    color_interpolator.Build()
    #                           x   ,r   ,g   , b
    color_interpolator.AddRGBPoint(-7.0, 0.0, 1.0, 1.0)
    if alpha is False:
        color_interpolator.AddRGBPoint(-1*threshold ,0.5 ,0.5 ,0.5)
    color_interpolator.AddRGBPoint(0.0, 0.5, 0.5, 0.5)
    if alpha is False:
        color_interpolator.AddRGBPoint( threshold ,0.5 ,0.5 ,0.5)
    color_interpolator.AddRGBPoint(7.0, 1.0, 0.27, 0.0)

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

class slice_viewer(vtk.vtkImageSlice):
    def __init__(self):
        slice_mapper = vtk.vtkImageSliceMapper()
        slice_mapper.SetOrientationToX()
        self.SetMapper(slice_mapper)


        self.SetVisibility(0)

        image_property = vtk.vtkImageProperty()
        self.SetProperty(image_property)

        image_property.SetColorWindow(2000)
        image_property.SetColorLevel(1000)

        self.slice_mapper=slice_mapper
        self.TR=1
        self.spatial_slice=0
        self.cursor=None
        self.current_x_coord=0
        self.current_y_coord=0

    def set_time_point(self,time):
        TR=self.TR
        space_slice=self.spatial_slice
        self.SetPosition(-1 * TR * time - 2 * space_slice, 0, 0)
        self.slice_mapper.SetSliceNumber(time)
    def add_cursor(self,cursor):
        self.cursor=cursor

    def get_cursor_position(self):
        return self.spatial_slice,self.current_x_coord,self.current_y_coord

    def set_interactor(self):
        pass
    def set_input(self,input_data,spatial_pos=0):
        self.slice_mapper.SetInputData(input_data)
        spacing=input_data.GetSpacing()
        self.TR=spacing[0]
        self.spatial_slice=spatial_pos
    def set_window_level(self,window,level):
        image_property = self.GetProperty()
        image_property.SetColorWindow(window)
        image_property.SetColorLevel(level)
