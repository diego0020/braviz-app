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

from __future__ import print_function
import numpy as np
import vtk
from vtk import vtkImagePlaneWidget
from braviz.interaction import get_fiber_bundle_descriptors, compute_volume_and_area
import logging

__author__ = 'diego'


def _test_arrow(head, tail):
    """A test for the arrow polydata"""
    renWin = vtk.vtkRenderWindow()
    ren = vtk.vtkRenderer()
    ren.SetRenderWindow(renWin)
    renWin.AddRenderer(ren)
    renWin.SetInteractor(vtk.vtkRenderWindowInteractor())
    renWin.GetInteractor().Initialize()
    iren = renWin.GetInteractor()
    iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
    head_sphere = vtk.vtkSphereSource()
    head_sphere.SetRadius(1)
    head_sphere.SetCenter(*head)
    tail_sphere = vtk.vtkSphereSource()
    tail_sphere.SetRadius(1)
    tail_sphere.SetCenter(*tail)
    head_mapper = vtk.vtkPolyDataMapper()
    head_mapper.SetInputConnection(head_sphere.GetOutputPort())
    tail_mapper = vtk.vtkPolyDataMapper()
    tail_mapper.SetInputConnection(tail_sphere.GetOutputPort())
    head_actor = vtk.vtkActor()
    tail_actor = vtk.vtkActor()
    head_actor.SetMapper(head_mapper)
    tail_actor.SetMapper(tail_mapper)
    head_actor.GetProperty().SetColor(0.0, 1.0, 0.0)
    tail_actor.GetProperty().SetColor(1.0, 0.0, 0.0)
    ren.AddActor(head_actor)
    ren.AddActor(tail_actor)

    arrow = get_arrow(head, tail)
    arrow_mapper = vtk.vtkPolyDataMapper()
    arrow_mapper.SetInputData(arrow)
    arrow_actor = vtk.vtkActor()
    arrow_actor.SetMapper(arrow_mapper)
    ren.AddViewProp(arrow_actor)
    iren.Start()


def estimate_window_level(image):
    """
    Estimates appropriate window and level values for the given image
    """
    hist = vtk.vtkImageHistogramStatistics()
    hist.SetInputData(image)
    hist.Update()
    x0, xf = hist.GetAutoRange()
    window = xf - x0
    level = (xf + x0)*0.5
    return window, level

class SimpleVtkViewer(object):

    """A very simple windows with vtk renderers and interactors.

    This class is intended for interactive work and fast prototyping. As such it is very simple and limited.
    For full interactive applications consider using :mod:`~braviz.visualization.subject_viewer`
    """

    def __init__(self):
        """Initialized the internal renderer, render window and intereactor"""
        self.ren = vtk.vtkRenderer()
        self.renWin = vtk.vtkRenderWindow()
        self.iren = vtk.vtkRenderWindowInteractor()
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.iren.SetRenderWindow(self.renWin)
        self.renWin.AddRenderer(self.ren)
        self.renWin.SetSize(600, 400)
        # self.renWin.Initialize()
        self.iren.Initialize()
        self.ren.Render()
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.005)
        cam1 = self.ren.GetActiveCamera()
        cam1.Elevation(80)
        cam1.Azimuth(80)
        cam1.SetViewUp(0, 0, 1)
        self.pd_actors = []
        print("call addPolyData or addImg to add data to the viewer\n call start to interact")

    def addPolyData(self, polyData, LUT=None):
        """
        Adds a poly data to the viewer, a LUT can be set.

        Args:
            polyData (vtkPolyData) : Polydata object to add to the scene
            LUT (vtkScalarsToColors) : A lookup table to apply to the polydata

        Returns:
            The vtkActor instance created, it may be used to change the visual properties

        """
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polyData)
        if LUT:
            mapper.UseLookupTableScalarRangeOn()
            mapper.SetLookupTable(LUT)
            mapper.SetColorModeToMapScalars()
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        self.ren.AddActor(actor)
        # self.ren.ResetCameraClippingRange()
        # self.ren.ResetCamera()
        self.pd_actors.append(actor)
        self.ren.Render()
        return actor

    def start(self, reset=True):
        """
        Call this method to start the interaction, interaction can be stopped by pressing 'q' on the main window

        Args:
            reset (bool) : If True the camera will be reset
        """
        print("press 'Q' on viewer window to stop")
        import sys
        sys.stdout.flush()
        if reset is True:
            self.ren.ResetCameraClippingRange()
            self.ren.ResetCamera()
        self.renWin.Render()
        self.iren.Start()

    def addImg(self, img):
        """
        Use this method to show an image inside an image plane widget.

        Args:
            img (vtkImageData) : Image

        Returns:
            The created imagePlaneWidget
        """
        planeWidget = persistentImagePlane()
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
        # self.ren.ResetCameraClippingRange()
        # self.ren.ResetCamera()
        self.ren.Render()
        return planeWidget

    def clear_poly_data(self):
        """Removes all polydata from the viewer"""
        for actor in self.pd_actors:
            self.ren.RemoveViewProp(actor)
        self.pd_actors = []


def save_ren_win_picture(ren_win, file_name):
    """
    Saves an screenshot of a render window

    Args:
        ren_win (vtkRenderWindow) : Render Window
        file_name (str) : Path to save screenshot
    """
    ren2img = vtk.vtkWindowToImageFilter()
    ren2img.SetInput(ren_win)
    ren2img.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(file_name)
    writer.SetInputConnection(ren2img.GetOutputPort())
    writer.Write()


def remove_nan_from_grid(grid):
    """
    Remove missing values from a grid, it is necessary in some version of vtk to avoid crash

    Args:
        grid (vtkPolyData) : Should only contain lines
    """
    out = vtk.vtkPolyData()
    points = grid.GetPoints()
    out.SetPoints(points)
    lines = vtk.vtkCellArray()
    lines.Initialize()
    for ic in xrange(grid.GetNumberOfCells()):
        c = grid.GetCell(ic)
        pids = c.GetPointIds()
        l = []
        for ip in xrange(pids.GetNumberOfIds()):
            pid = pids.GetId(ip)
            pt = grid.GetPoint(pid)
            if np.all(np.isfinite(pt)):
                l.append(pid)
        if len(l) > 0:
            lines.InsertNextCell(len(l))
            for p in l:
                lines.InsertCellPoint(p)
    out.SetLines(lines)
    return out


class persistentImagePlane(vtkImagePlaneWidget):

    """A vtkImagePlaneWidget which can keep its state between calls to SetInputData.

    It adds a second text message showing the world coordinates of the cursors
    This message can be further enhanced by using a label image and a label dictionary
    Additionally the values displayed in the first message can be replaced by values taken from another image, this
    is useful when the displayed image contains colors or other contexts that are not the main value (ex, fmri)
    Finally, this class generates custom events when moving the cursor and when changing the slice."""

    def __init__(self, orientation=0):
        """
        Construct a persistent image plane

        Args:
            Orientation (int) :  x:0 , y:1, z:2"""
        self.SetMarginSizeX(0)
        self.SetMarginSizeY(0)
        self.SetDisplayText(1)
        self.Initialized = False
        self.Orientation = orientation
        self.MiddleButton = False
        self.labels_set = False
        self.labels_dict = None
        self.slice_change_event = vtk.vtkCommand.UserEvent + 1
        self.cursor_change_event = vtk.vtkCommand.UserEvent + 2
        self.window_level_change_event = vtk.vtkCommand.UserEvent + 3
        self.alternative_text1 = False
        self.last_cursor_position = None
        self.alternative_img = None

    def SetInputData(self, img):
        """
        Changes the input data por the plane widget

        Args:
            img (vtkImageData) : New image data
        """
        if self.Initialized:
            window_level = [0, 0]
            old_slice = self.GetSlicePosition()
            self.GetWindowLevel(window_level)
            vtkImagePlaneWidget.SetInputData(self, img)
            self.SetSlicePosition(old_slice)
            self.SetWindowLevel(*window_level)
            self.InvokeEvent(self.slice_change_event)
        else:
            self.Initialized = True
            vtkImagePlaneWidget.SetInputData(self, img)
            self.SetPlaneOrientation(self.Orientation)
            mid_slice = img.GetDimensions()[self.Orientation] // 2
            self.SetSliceIndex(mid_slice)
            self.InvokeEvent(self.slice_change_event)

    def SetInteractor(self, iact):
        """
        Links the widget to an interactor

        Args:
            iact (vtkRenderWindowInteractor) : Render window interactor
        """
        # Initializes the second text message, and performs normal
        # vtkImagePlaneWidget initialization

        vtkImagePlaneWidget.SetInteractor(self, iact)
        text2 = vtk.vtkTextActor()
        cor = text2.GetPositionCoordinate()
        cor.SetCoordinateSystemToNormalizedViewport()
        text2.SetPosition([0.99, 0.01])
        text2.SetInput('probando')
        tprop = text2.GetTextProperty()
        tprop.SetJustificationToRight()
        tprop.SetFontSize(18)
        text2.SetVisibility(0)

        def mouse_interaction(obj, event):
            """

            Handles StartInteractionEvent and InteractionEvent

            Displays the appropriate messages in the corner
            When the mouse button is pressed displays the current slice
            Otherwise displays the coordinates in mm, and the associated label if available
            The message in the left corner may be changed so that the value is taken from a second image,
            this is usefurl for example to display a composed fmri image but showing in the message only the z-score
            """
            if (not self.GetDisplayText()) and (not self.alternative_text1):
                self.last_cursor_position = None
                if self.MiddleButton:
                    self.InvokeEvent(self.slice_change_event)
                else:
                    self.InvokeEvent(self.cursor_change_event)
                return
            text2.SetVisibility(1)
            x, y, z = self.GetCurrentCursorPosition()
            img2 = self.GetInput()
            x0, y0, z0 = img2.GetOrigin()
            dx, dy, dz = img2.GetSpacing()
            x1 = x0 + dx * x
            y1 = y0 + dy * y
            z1 = z0 + dz * z
            self.last_cursor_position = (x1, y1, z1)
            if self.MiddleButton:
                message = 'Slice: %d' % self.GetSliceIndex()
                # create event, an observer can listen to this
                self.InvokeEvent(self.slice_change_event)
            else:
                message = '(%d, %d, %d)' % (x1, y1, z1)
                self.InvokeEvent(self.cursor_change_event)
                if self.labels_set:
                    label = self.get_label(x1, y1, z1)
                    message += ': %s' % label
                if self.alternative_text1:
                    ix, iy, iz = map(int, (x, y, z))
                    value = self.alternative_img.GetScalarComponentAsDouble(
                        ix, iy, iz, 0)
                    message2 = '( %d, %d, %d ) : %f' % (x, y, z, value)
                    self.text1.SetInput(message2)
                    self.text1.SetVisibility(1)

            text2.SetInput(message)

        def end_interact(obj, event):
            """Handles EndInteractionEvent"""
            text2.SetVisibility(0)
            if self.alternative_text1:
                self.text1.SetVisibility(0)
            self.MiddleButton = False

        def detect_middle_button(obj, event):
            """Helps in detecting when the middle button is pressed"""
            if event == 'MiddleButtonPressEvent':
                self.MiddleButton = True
            else:
                self.MiddleButton = False

        # def detect_window_level_event(obj, event):
        #    print self.GetWindow(), self.GetLevel()

        self.GetInteractor().AddObserver(
            'MiddleButtonPressEvent', detect_middle_button, 1000)
        self.GetInteractor().AddObserver(
            'MiddleButtonReleaseEvent', detect_middle_button, 1000)
        self.AddObserver('InteractionEvent', mouse_interaction)
        self.AddObserver('StartInteractionEvent', mouse_interaction)
        self.AddObserver('EndInteractionEvent', end_interact)
        # self.AddObserver('WindowLevelEvent',detect_window_level_event)
        self.text2 = text2

    def On(self):
        """
        Turn the widget on
        """
        # Adds the second text actor to the current renderer
        vtkImagePlaneWidget.On(self)
        ren = self.GetCurrentRenderer()
        ren.AddActor(self.text2)
        ren.Render()

    def setLabelsLut(self, lut):
        """
        A lookup table can be used to translate numeric labels into text labels

        Args:
            lut (vtkLookupTable) : Lookup table
        """
        self.labels_dict = {}
        self.aparc_lut = lut

    def addLabels(self, label_img):
        """
        A second image can be used to get labels for image coordinates (ex. aparc)

        Args:
            label_img (vtkImageData) : Image to use as reference for labels
        """

        self.label_img = label_img
        if label_img is not None:
            self.labels_set = True
        else:
            self.labels_set = False

    def get_label(self, x, y, z):
        """
        Auxiliary function to get the label in a given coordinate (in mm)

        Args:
            x (float) : x coordinate
            y (float) : y coordinate
            z (float) : z coordinate

        Returns:
            If a lookuptable is set returns the text label, otherwise the numeric label
        """
        img2 = self.label_img
        x0, y0, z0 = img2.GetOrigin()
        dx, dy, dz = img2.GetSpacing()
        x1 = (x - x0) / dx
        y1 = (y - y0) / dy
        z1 = (z - z0) / dz

        x1 = int(round(x1))
        y1 = int(round(y1))
        z1 = int(round(z1))

        l = int(img2.GetScalarComponentAsDouble(x1, y1, z1, 0))
        if self.labels_dict is None:
            return l

        if not l in self.labels_dict:
            idx = self.aparc_lut.GetAnnotatedValueIndex(l)
            label = self.aparc_lut.GetAnnotation(idx)
            self.labels_dict[l] = label
        return self.labels_dict[l]

    def text1_value_from_img(self, img2):
        """
        Text 1 value can be read from a different image than the one been shown, useful for composed images

        Args:
            img2 (vtkImageData) : Image to get values for lower left corner text
        """
        self.SetDisplayText(0)
        text1 = vtk.vtkTextActor()
        cor = text1.GetPositionCoordinate()
        cor.SetCoordinateSystemToNormalizedViewport()
        text1.SetPosition([0.01, 0.01])
        text1.SetInput('probando')
        tprop = text1.GetTextProperty()
        tprop.SetJustificationToLeft()
        tprop.SetFontSize(18)
        text1.SetVisibility(0)
        self.alternative_text1 = True
        self.alternative_img = img2
        self.text1 = text1
        ren = self.GetCurrentRenderer()
        if ren is not None:
            ren.AddActor(self.text1)

    def text1_to_std(self):
        """
        Turn text1 behaviour back to standard, reverts the effects of text1_value_from_img
        """
        if not self.alternative_text1:
            return
        ren = self.GetCurrentRenderer()
        if ren is not None:
            ren.RemoveActor(self.text1)
        self.SetDisplayText(1)
        self.alternative_text1 = False
        self.alternative_img = None
        self.text1 = None

    def set_orientation(self, orientation):
        """
        Sets image plane orientation

        Args:
            orientation (int)  :  x:0 , y:1, z:2
        """
        self.Orientation = orientation
        self.SetPlaneOrientation(self.Orientation)
        image = self.GetInput()
        if image is None:
            return
        mid_slice = image.GetDimensions()[self.Orientation] // 2
        self.SetSliceIndex(mid_slice)
        self.InvokeEvent(self.slice_change_event)


class OutlineActor(vtk.vtkActor):

    """A simple shortcut for displaying the outline of an object

    Encapsulates an outline filter, a mapper and an actor"""

    def __init__(self):
        """
        Creates internal mapper, and filter, and performs the connections
        """
        outline = vtk.vtkOutlineFilter()

        outlineMapper = vtk.vtkPolyDataMapper()
        outlineMapper.SetInputConnection(outline.GetOutputPort())

        self.SetMapper(outlineMapper)
        self.outline = outline

    def set_input_data(self, input_data):
        """
        Sets the input data for the outline

        Args:
            input_data (vtkDataObject) : Object whose outline we want

        """
        self.outline.SetInputData(input_data)

    def SetInputData(self, input_data):
        """
        For better compatibility with vtk methods style

        Args:
            input_data (vtkDataObject) : Object whose outline we want
        """
        self.outline.SetInputData(input_data)


class OrientationAxes(object):

    """
    An orientation cube with faces labeled for Right, Left, Anterior, Posterior, Superior and Inferior
    """

    def __init__(self):
        axes_actor = vtk.vtkAnnotatedCubeActor()
        axes_actor.SetXPlusFaceText("R")
        axes_actor.SetXMinusFaceText("L")
        axes_actor.SetYPlusFaceText("A")
        axes_actor.SetYMinusFaceText("P")
        axes_actor.SetZPlusFaceText("S")
        axes_actor.SetZMinusFaceText("I")

        axes_actor.GetTextEdgesProperty().SetColor(1, 1, 1)
        axes_actor.GetTextEdgesProperty().SetLineWidth(2)
        axes_actor.GetCubeProperty().SetColor(0.3, 0.3, 0.3)

        axes = vtk.vtkOrientationMarkerWidget()
        axes.SetOrientationMarker(axes_actor)
        axes.SetViewport(0.9, 0.9, 1, 1)

        self.axes = axes

    def initialize(self, render_window_interactor):
        """
        Link the orientation cube with an interactor

        render_window_interactor (vtkRenderWindowInteractor) : vtk interactor
        """
        self.axes.SetInteractor(render_window_interactor)
        self.axes.EnabledOn()
        self.axes.InteractiveOn()


def get_arrow(head, tail):
    """
    create a polydata arrow, consider using vtkArrowSource

    Args:
        head (tuple) : coordinates for arrow head
        tail (tuple) : coordinates for arrow tail

    """
    arrow_pd = vtk.vtkPolyData()
    points_array = vtk.vtkPoints()
    triangle_array = vtk.vtkCellArray()
    line_array = vtk.vtkCellArray()
    arrow_points = [
        (-0.1, 0, 0), (-0.1, -0.5, 0), (0, 0, 0), (-0.1, 0.5, 0), (-1, 0, 0)]
    for i, p in enumerate(arrow_points):
        points_array.InsertPoint(i, p)

    triangle_array.InsertNextCell(4)
    for p in (0, 1, 2, 3):
        triangle_array.InsertCellPoint(p)
    line_array.InsertNextCell(2)
    line_array.InsertCellPoint(0)
    line_array.InsertCellPoint(4)
    arrow_pd.SetPoints(points_array)
    arrow_pd.SetLines(line_array)
    arrow_pd.SetPolys(triangle_array)

    #---adjust to tail and head

    t = vtk.vtkTransform()
    t.Identity()
    t.PostMultiply()
    head = np.array(head)
    tail = np.array(tail)
    length = np.linalg.norm(head - tail)
    if length > 0:
        t.Scale(length, length / 20, 1)
        rot_axis = np.cross(head - tail, (1, 0, 0))
        rot_angle = np.arcsin(np.linalg.norm(rot_axis) / length)
        if np.isnan(rot_angle):  # handles legendary rounding errors
            log = logging.getLogger(__name__)
            log.warning("please check output closely")
            if np.linalg.norm((head - tail) / length - (1, 0, 0)) < length / 1000:
                rot_angle = 0
            else:
                rot_angle = np.pi
        deg_angle = 180 / np.pi * rot_angle
        if np.dot(head - tail, (1, 0, 0)) < 0:
            deg_angle = 180 - deg_angle
        t.RotateWXYZ(-1 * deg_angle, rot_axis[0], rot_axis[1], rot_axis[2])

    t.Translate(*head)
    transfor_filter = vtk.vtkTransformPolyDataFilter()
    transfor_filter.SetInputData(arrow_pd)
    transfor_filter.SetTransform(t)
    transfor_filter.Update()
    return transfor_filter.GetOutput()


def fibers_balloon_message(fib_actor, name=None):
    """Gets a standard message for fiber bundle balloons
    This message contains the number of fibers in the bundle,
    their mean length, max length, min length, and standard deviation of length"""
    mapper = fib_actor.GetMapper()
    try:
        fib = mapper.GetInput()
    except AttributeError:
        log = logging.getLogger(__name__)
        log.warning("No fibers available")
        return "No fibers available"
    d = get_fiber_bundle_descriptors(fib)
    message = """Number of fibers: %d
Mean Length (mm) : %.2f
    Max: %.2f
    Min: %.2f
    Std: %.2f""" % d
    if name is not None:
        message = name + '\n' + message
    else:
        message = 'Fiber Bundle\n' + message
    return message


class cursors(vtk.vtkPropAssembly):

    """
    Emulates the cursors in vtkImagePlaneWidget

    There will be two copies of the cursors polydata, one in front and one at the back of the
    image plane, the separation between them is controlled by the :meth:`set_delta` method
    """

    def __init__(self, axis=0):
        """The perpendicular axis is x:0 , y:1, z:2

        Notice that for the cursor to work properly the spacing, dimensions and origin
        of the underlying image must be set"""
        actor_delta = 1.0  # Space within the cursor and the image, notice there are cursors on both sides
        cursor_x = vtk.vtkLineSource()
        cursor_x_mapper = vtk.vtkPolyDataMapper()
        cursor_x_mapper.SetInputConnection(cursor_x.GetOutputPort())
        cursor_x_actor = vtk.vtkActor()
        cursor_x_actor2 = vtk.vtkActor()
        cursor_x_actor.SetMapper(cursor_x_mapper)
        cursor_x_actor2.SetMapper(cursor_x_mapper)

        cursor_y = vtk.vtkLineSource()
        cursor_y_mapper = vtk.vtkPolyDataMapper()
        cursor_y_mapper.SetInputConnection(cursor_y.GetOutputPort())
        cursor_y_actor = vtk.vtkActor()
        cursor_y_actor2 = vtk.vtkActor()
        cursor_y_actor.SetMapper(cursor_y_mapper)
        cursor_y_actor2.SetMapper(cursor_y_mapper)

        actors_spacing1 = [0, 0, 0]
        actors_spacing2 = [0, 0, 0]

        actors_spacing1[axis] = -1 * actor_delta
        actors_spacing2[axis] = 1 * actor_delta

        cursor_x_actor.SetPosition(actors_spacing1)
        cursor_x_actor2.SetPosition(actors_spacing2)

        cursor_y_actor.SetPosition(actors_spacing1)
        cursor_y_actor2.SetPosition(actors_spacing2)

        for act in [cursor_x_actor, cursor_x_actor2, cursor_y_actor, cursor_y_actor2]:
            act.GetProperty().SetColor(1.0, 0, 0)
            self.AddPart(act)
        self.delta = actor_delta
        self.cursor_x = cursor_x
        self.cursor_y = cursor_y
        self.spacing = (1, 1, 1)
        self.dimensions = (10, 95, 68)
        self.origin = (0, 0, 0)
        self.axis = axis
        self.actor_x1 = cursor_x_actor
        self.actor_x2 = cursor_x_actor2
        self.actor_y1 = cursor_y_actor
        self.actor_y2 = cursor_y_actor2

    def set_spacing(self, dx, dy, dz):
        """
        Sets the spacing of the underlying image

        Args:
            dx (float) : x spacing
            dy (float) : y spacing
            dz (float) : z spacing
        """
        self.spacing = (dx, dy, dz)

    def set_dimensions(self, nx, ny, nz):
        """
        Sets the dimensions of the underlying image

        Args:
            nx (float) : x dimension
            ny (float) : y dimension
            nz (float) : z dimension
        """
        self.dimensions = (nx, ny, nz)

    def set_origin(self, x, y, z):
        """
        Sets the origin of the underlying image

        Args:
            x (float) : x origin
            y (float) : y origin
            z (float) : z origin
        """
        self.origin = (x, y, z)

    def set_cursor(self, x, y, z):
        """
        Set the position of the cursor

        Args:
            x (float) : x position
            y (float) : y position
            z (float) : z position


        """
        # current_slice=slice_mapper.GetSliceNumber()
        # Attention to change in variables, now XY define the plane
        dx, dy, dz = self.spacing
        ox, oy, oz = self.origin
        nx, ny, nz = self.dimensions
        if self.axis == 0:
            self.cursor_x.SetPoint1((ox + dx * x, oy + dy * y, oz + dz * 0))
            self.cursor_x.SetPoint2((ox + dx * x, oy + dy * y, oz + dz * nz))
            self.cursor_y.SetPoint1((ox + dx * x, oy + dy * 0, oz + dz * z))
            self.cursor_y.SetPoint2((ox + dx * x, oy + dy * ny, oz + dz * z))
        elif self.axis == 1:
            self.cursor_x.SetPoint1((ox + dx * x, oy + dy * y, oz + dz * 0))
            self.cursor_x.SetPoint2((ox + dx * x, oy + dy * y, oz + dz * nz))
            self.cursor_y.SetPoint1((ox + dx * 0, oy + dy * y, oz + dz * z))
            self.cursor_y.SetPoint2((ox + dx * nx, oy + dy * y, oz + dz * z))
        else:
            self.cursor_x.SetPoint1((ox + dx * 0, oy + dy * y, oz + dz * z))
            self.cursor_x.SetPoint2((ox + dx * nx, oy + dy * y, oz + dz * z))
            self.cursor_y.SetPoint1((ox + dx * x, oy + dy * 0, oz + dz * z))
            self.cursor_y.SetPoint2((ox + dx * x, oy + dy * ny, oz + dz * z))

    def change_axis(self, axis):
        """
        Change the axis perpendicular to the image plane

        Args:
            axis (int) :   x:0 , y:1, z:2
        """
        self.axis = axis
        actors_spacing1 = [0, 0, 0]
        actors_spacing2 = [0, 0, 0]
        actors_spacing1[axis] = -1 * self.delta
        actors_spacing2[axis] = 1 * self.delta
        self.actor_x1.SetPosition(actors_spacing1)
        self.actor_y1.SetPosition(actors_spacing1)
        self.actor_x2.SetPosition(actors_spacing2)
        self.actor_y2.SetPosition(actors_spacing2)

    def set_delta(self, delta):
        """
        Sets separation between front and back cursors.

        Args:
            delta (float) :  Separation
        """
        self.delta = delta


def build_grid(orig_img, img_slice, sampling_rate=5):
    """Creates an homogenous grid, useful for showing the effects of transformations

    The grid dimensions are based on the orig_img, img_slice is used to position the grid along the x axis,
    For the moment only grids perpendicular to the x axis are available

    Args:
        orig_img (vtkImageData) : Image to base grid on
        img_slice (int) : Slice of the image where the grid will be located (along the x asis)
        sampling_rate (int) : Density of the grid, there will be a line each *sampling_rate* voxels
    """
    dimensions = orig_img.GetDimensions()
    spacing = orig_img.GetSpacing()
    origin = orig_img.GetOrigin()
    n_points = int(dimensions[1] * dimensions[2])

    def img2world(i, j, k):
        return np.array((i, j, k)) * spacing + origin

    def flat_index(j, k):
        return j * dimensions[2] + k

    points = vtk.vtkPoints()
    points.SetNumberOfPoints(n_points)
    for j in xrange(dimensions[1]):
        for k in xrange(dimensions[2]):
            idx = flat_index(j, k)
            coords = img2world(img_slice, j, k)
            points.SetPoint(idx, coords)
    grid = vtk.vtkPolyData()
    grid.SetPoints(points)
    lines = vtk.vtkCellArray()
    # vertical:
    for j in xrange(dimensions[1]):
        if j % sampling_rate == 0:
            lines.InsertNextCell(dimensions[2])
            for k in xrange(dimensions[2]):
                lines.InsertCellPoint(flat_index(j, k))
    # horizontal
    for k in xrange(dimensions[2]):
        if k % sampling_rate == 0:
            lines.InsertNextCell(dimensions[1])
            for j in xrange(dimensions[1]):
                lines.InsertCellPoint(flat_index(j, k))

    grid.SetLines(lines)
    cleaner = vtk.vtkCleanPolyData()
    cleaner.SetInputData(grid)
    cleaner.Update()
    clean_grid = cleaner.GetOutput()
    return clean_grid


def add_solid_balloon(balloon_widget, solid_actor, name=None, my_volume=None):
    """Adds a standard balloon for models

    This standard balloon will contain the solid name(if given), its volume and its surface area
    my_volume can be specified to replace the auto calculated volume
    """
    mapper = solid_actor.GetMapper()
    poly_data = mapper.GetInput()
    (volume, area) = compute_volume_and_area(poly_data)
    #message = "Volume = %.2f mm3 \nSurface Area = %.2f mm2 " % (volume, area)
    if my_volume is not None:
        volume = my_volume
    message = "Volume* = %.2f mm3 \nSurface Area = %.2f mm2 " % (volume, area)

    if name is not None:
        message = "%s \n%s" % (name, message)
    balloon_widget.AddBalloon(solid_actor, message)
    return


def add_simple_solid_balloon(balloon_widget, solid_actor, message):
    """YOYIS Adds a standard balloon with a custom message"""
    balloon_widget.AddBalloon(solid_actor, message)
    return


def add_fibers_balloon(balloon_widget, fib_actor, name=None):
    """Adds a standard balloon for fiber bundles, the message contains the name, the number of fibers
    and descriptors about the length of the fibers (see fibers_balloon_message)"""
    message = fibers_balloon_message(fib_actor, name)
    balloon_widget.AddBalloon(fib_actor, message)


def get_window_level(img):
    """
    Automatically gets appropriate window and level values for displaying an image

    Args:
        img (vtkImageData) : Image

    Returns
        (window,level), proposed values
    """
    stats = vtk.vtkImageHistogramStatistics()
    stats.SetInputData(img)
    stats.Update()
    _, w = stats.GetAutoRange()
    return w, w / 2
