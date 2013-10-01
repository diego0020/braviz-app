from __future__ import division
import vtk
from vtk import vtkImagePlaneWidget
from braviz.interaction import compute_volume_and_area,get_fiber_bundle_descriptors


class simpleVtkViewer():
    """A very simple windows with vtk renderers and interactors.
    Use addPolyData to add polydata objects and addImg to add a vtkImagePlaneWidget
    Finally, use start() to start the interaction
    """
    def __init__(self):
        self.ren=vtk.vtkRenderer()
        self.renWin=vtk.vtkRenderWindow()
        self.iren=vtk.vtkRenderWindowInteractor()
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.iren.SetRenderWindow(self.renWin)
        self.renWin.AddRenderer(self.ren)
        self.renWin.SetSize(600,400)
        self.ren.Render()
        self.renWin.Initialize()
        self.iren.Initialize()
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.005)
        cam1 = self.ren.GetActiveCamera()
        cam1.Elevation(80)
        cam1.Azimuth(80)
        cam1.SetViewUp(0, 0, 1)
        print "call addPolyData or addImg to add data to the viewer\n call start to interact"
    def addPolyData(self,polyData, LUT=None):
        """Adds a poly data to the viewer, a LUT can be set. 
        It returns the actor that is created, which you can use to change its properties"""
        mapper=vtk.vtkPolyDataMapper()
        mapper.SetInputData(polyData)
        if LUT:
            mapper.UseLookupTableScalarRangeOn()
            mapper.SetLookupTable(LUT)
            mapper.SetColorModeToMapScalars()
            print "lut set"
        actor=vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)
        #self.ren.ResetCameraClippingRange()
        #self.ren.ResetCamera()
        self.ren.Render()
        return actor
    def start(self):
        "Call this method to start the interaction, interaction can stop by pressing 'q' on the main window"
        print "press 'Q' on viewer window to stop"
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()
        self.ren.Render()
        self.iren.Start()
    def addImg(self,img):
        "Use this method to show an image inside an image plane widget. The newly created imagePlaneWidget is returned"
        planeWidget=persistentImagePlane()
        planeWidget.SetInputData(img)
        planeWidget.SetPlaneOrientationToXAxes()
        planeWidget.SetSlicePosition(0.5)
        planeWidget.UpdatePlacement()
        planeWidget.DisplayTextOn()
        # An outline is shown for context.
        outline = vtk.vtkOutlineFilter()
        outline.SetInputData(img)
        outlineMapper = vtk.vtkPolyDataMapper()
        outlineMapper.SetInputConnection(outline.GetOutputPort())
        outlineActor = vtk.vtkActor()
        outlineActor.SetMapper(outlineMapper)
        self.ren.AddActor(outlineActor)
        planeWidget.SetPicker(self.picker)
        planeWidget.SetInteractor(self.renWin.GetInteractor())
        planeWidget.PickingManagedOn()
        planeWidget.On()
        #self.ren.ResetCameraClippingRange()
        #self.ren.ResetCamera()
        self.ren.Render()
        return planeWidget
class persistentImagePlane(vtkImagePlaneWidget):
    """A vtkImagePlaneWidget which can keep its state between calls to SetInputData.
    It also adds a second text message showing the world coordinates of the cursors"""
    def __init__(self,orientation=0):
        "Orientation is x:0 , y:1, z:2"
        #vtkImagePlaneWidget.__init__()
        self.SetMarginSizeX(0)
        self.SetMarginSizeY(0)
        self.SetDisplayText(1)
        self.Initialized=False
        self.Orientation=orientation
        self.MiddleButton=False
        self.Labels_set=False
        self.labels_dict=None
        self.slice_change_event=vtk.vtkCommand.UserEvent+1
        self.alternative_text1=False
    def SetInputData(self,img):
        "Changes the input data por the plane widget"
        if self.Initialized:
            window_level=[0,0]
            old_slice=self.GetSlicePosition()
            self.GetWindowLevel(window_level)
            vtkImagePlaneWidget.SetInputData(self,img)
            self.SetSlicePosition(old_slice)
            self.SetWindowLevel(*window_level)
            
        else:
            self.Initialized=True
            vtkImagePlaneWidget.SetInputData(self,img)
            self.SetPlaneOrientation(self.Orientation)
            mid_slice=img.GetDimensions()[self.Orientation]//2
            self.SetSliceIndex(mid_slice)
    def SetInteractor(self,iact):
        "Initializes the second text message, and performs normal vtkImagePlaneWidget initialization"
        vtkImagePlaneWidget.SetInteractor(self,iact)
        text2=vtk.vtkTextActor()
        cor=text2.GetPositionCoordinate()
        cor.SetCoordinateSystemToNormalizedViewport()
        text2.SetPosition([0.99,0.01])
        text2.SetInput('probando')
        tprop=text2.GetTextProperty()
        tprop.SetJustificationToRight()
        tprop.SetFontSize(18)
        text2.SetVisibility(0)
        def interactTest(obj,event):
            #print event
            text2.SetVisibility(1)
            x,y,z=self.GetCurrentCursorPosition()
            img2=self.GetInput()
            x0,y0,z0=img2.GetOrigin()
            dx,dy,dz=img2.GetSpacing()
            x1=x0+dx*x
            y1=y0+dy*y
            z1=z0+dz*z
            if self.MiddleButton:
                message='Slice: %d'%self.GetSliceIndex()
                self.InvokeEvent(self.slice_change_event)
            else:
                message='(%d, %d, %d)' % (x1,y1,z1)
                if self.Labels_set:
                    label=self.get_label(x1,y1,z1)
                    message=message+': %s'%label
                if self.alternative_text1:
                    ix,iy,iz=map(int,(x,y,z))
                    value=self.alternative_img.GetScalarComponentAsDouble(ix,iy,iz,0)
                    message2='( %d, %d, %d ) : %f'%(x,y,z,value)
                    self.text1.SetInput(message2)
                    self.text1.SetVisibility(1)
                
            text2.SetInput(message)
        def endInteract(obj,event):
            text2.SetVisibility(0)
            if self.alternative_text1:
                self.text1.SetVisibility(0)
        def detectMiddleButton(obj,event):
            if event=='MiddleButtonPressEvent':
                self.MiddleButton=True
            else:
                self.MiddleButton=False

            
        self.GetInteractor().AddObserver('MiddleButtonPressEvent',detectMiddleButton,1000)
        self.GetInteractor().AddObserver('MiddleButtonReleaseEvent',detectMiddleButton,1000)
        self.AddObserver('InteractionEvent',interactTest)
        self.AddObserver('StartInteractionEvent',interactTest)
        self.AddObserver('EndInteractionEvent',endInteract)
        self.text2=text2
    def On(self):
        "Adds the second text actor to the current renderer"
        vtkImagePlaneWidget.On(self)
        ren=self.GetCurrentRenderer()
        ren.AddActor(self.text2)
    def setLabelsLut(self,lut):
        "A lookup table can be used to translate numeric lables into text labels"
        self.labels_dict={}
        self.aparc_lut=lut
    def addLabels(self,label_img):
        "A second image can be used to get labels for image coordinates (ex. aparc)"
        self.label_img=label_img
        self.Labels_set=True
    def get_label(self,x,y,z):
        "Auxiliary function to get the label in a given coordinate (in mm)"
        img2=self.label_img
        x0,y0,z0=img2.GetOrigin()
        dx,dy,dz=img2.GetSpacing()
        x1=(x-x0)/dx
        y1=(y-y0)/dy
        z1=(z-z0)/dz
        
        x1=int(round(x1))
        y1=int(round(y1))
        z1=int(round(z1))
        
        l=int(img2.GetScalarComponentAsDouble(x1,y1,z1,0))
        if self.labels_dict==None:
            return l
        
        if not self.labels_dict.has_key(l):
            idx=self.aparc_lut.GetAnnotatedValueIndex(l)
            label=self.aparc_lut.GetAnnotation(idx)
            self.labels_dict[l]=label
        return self.labels_dict[l]
    def text1_value_from_img(self,img2):
        "Text 1 value can be read from a different image than the one been shown, useful for composed images"
        self.SetDisplayText(0)
        text1=vtk.vtkTextActor()
        cor=text1.GetPositionCoordinate()
        cor.SetCoordinateSystemToNormalizedViewport()
        text1.SetPosition([0.01,0.01])
        text1.SetInput('probando')
        tprop=text1.GetTextProperty()
        tprop.SetJustificationToLeft()
        tprop.SetFontSize(18)
        text1.SetVisibility(0)
        self.alternative_text1=True
        self.alternative_img=img2
        self.text1=text1
        ren=self.GetCurrentRenderer()
        ren.AddActor(self.text1)
    def text1_to_std(self):
        "Turn text1 behaviour back to standard, reverts the effects of text1_value_from_img"
        if not self.alternative_text1:
            return
        ren=self.GetCurrentRenderer()
        ren.RemoveActor(self.text1)
        self.SetDisplayText(1)
        self.alternative_text1=False
        self.alternative_img=None
        self.text1=None
        
def add_solid_balloon(balloon_widget,solid_actor,name=None):
    "Adds a standard balloon for models"
    mapper=solid_actor.GetMapper()
    poly_data=mapper.GetInput()
    (volume,area)=compute_volume_and_area(poly_data)
    message="Volume = %.2f mm3 \nSurface Area = %.2f mm2 "%(volume,area)
    if name!=None:
        message="%s \n"%name+message
    balloon_widget.AddBalloon(solid_actor,message)
    return
def fibers_balloon_message(fib_actor,name=None):
    "Gets a standard message for fiber balloons"
    mapper=fib_actor.GetMapper()
    try:
        fib=mapper.GetInput()
    except AttributeError:
        print "No fibers available"
        return "No fibers available"
    d=get_fiber_bundle_descriptors(fib)
    message="""Number of fibers: %d
Mean Length (mm) : %.2f
    Max: %.2f
    Min: %.2f
    Std: %.2f"""%d
    if name != None:
        message=name+'\n'+message
    else:
        message='Fiber Bundle\n'+message
    return message
def add_fibers_balloon(balloon_widget,fib_actor,name=None):
    "Adds a standard balloon for models"
    message=fibers_balloon_message(fib_actor, name)
    balloon_widget.AddBalloon(fib_actor,message)
    