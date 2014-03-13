from __future__ import division
__author__ = 'Diego'

import vtk
import braviz

class SubjectViewer:
    def __init__(self,render_window_interactor,reader):

        render_window_interactor.Initialize()
        render_window_interactor.Start()
        self.iren=render_window_interactor
        self.ren_win=render_window_interactor.GetRenderWindow()
        self.ren=vtk.vtkRenderer()
        #self.ren.SetBackground((0.75,0.75,0.75))
        self.ren.GradientBackgroundOn()
        self.ren.SetBackground2( (0.5, 0.5, 0.5))
        self.ren.SetBackground((0.2, 0.2, 0.2))
        self.ren.SetUseDepthPeeling(1)
        self.ren_win.SetMultiSamples(0)
        self.ren_win.AlphaBitPlanesOn()
        self.ren.SetOcclusionRatio(0.1)
        self.ren_win.AddRenderer(self.ren)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.axes=braviz.visualization.OrientationAxes()
        self.axes.initialize(self.iren)

        self.reader=reader

        #state
        self.__current_subject="093"
        self.__current_space="world"
        self.__current_image=None
        self.__current_image_orientation=0
        self.__curent_fmri_paradigm=None

        #internal data
        self.__image_plane_widget=None
        self.__mri_lut=None
        self.__fmri_blender=braviz.visualization.fMRI_blender()

        #reset camera and render
        self.reset_camera(0)
        self.ren.Render()

    def show_cone(self):
        """Useful for testing"""
        cone=vtk.vtkConeSource()
        cone.SetResolution(8)
        cone_mapper=vtk.vtkPolyDataMapper()
        cone_mapper.SetInputConnection(cone.GetOutputPort())
        cone_actor=vtk.vtkActor()
        cone_actor.SetMapper(cone_mapper)
        self.ren.AddActor(cone_actor)
        self.ren_win.Render()

    def hide_image(self):
        if self.__image_plane_widget is not None:
            self.__image_plane_widget.Off()
            #self.image_plane_widget.SetVisibility(0)

    def create_image_plane_widget(self):
        if self.__image_plane_widget is not None:
            #already created
            return
        self.__image_plane_widget=braviz.visualization.persistentImagePlane(self.__current_image_orientation)
        self.__image_plane_widget.SetInteractor(self.iren)
        self.__image_plane_widget.On()
        self.__mri_lut=vtk.vtkLookupTable()
        self.__mri_lut.DeepCopy(self.__image_plane_widget.GetLookupTable())

    def change_image_modality(self,modality,paradigm=None):
        """Changes the modality of the current image
        to hide the image call hide_image
        in the case of fMRI modality should be fMRI and paradigm the name of the paradigm"""

        modality=modality.upper()
        if (modality ==self.__current_image) and (paradigm==self.__curent_fmri_paradigm):
            #nothing to do
            return

        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
        self.__image_plane_widget.On()

        #update image labels:
        aparc_img=self.reader.get("APARC",self.__current_subject,format="VTK",space=self.__current_space)
        aparc_lut=self.reader.get("APARC",self.__current_subject,lut=True)
        self.__image_plane_widget.addLabels(aparc_img)
        self.__image_plane_widget.setLabelsLut(aparc_lut)

        if modality=="FMRI":
            mri_image=self.reader.get("MRI",self.__current_subject,format="VTK",space=self.__current_space)
            fmri_image=self.reader.get("fMRI",self.__current_subject,format="VTK",space=self.__current_space,
                                       name=paradigm)
            fmri_lut=self.reader.get("fMRI",self.__current_subject,lut=True)
            self.__fmri_blender.set_luts(self.__mri_lut,fmri_lut)
            new_image=self.__fmri_blender.set_images(mri_image,fmri_image)
            self.__image_plane_widget.SetInputData(new_image)
            self.__image_plane_widget.GetColorMap().SetLookupTable(None)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            self.ren_win.Render()
            self.__current_image=new_image
            self.__image_plane_widget.text1_value_from_img(fmri_image)
            return

        self.__image_plane_widget.text1_to_std()
        #Other images
        new_image=self.reader.get(modality,self.__current_subject,space=self.__current_space,format="VTK")

        self.__image_plane_widget.SetInputData(new_image)

        if modality=="MRI":
            lut=self.__mri_lut
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
        elif modality=="FA":
            lut=self.reader.get("FA",self.__current_subject,lut=True)
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
        elif modality=="APARC":
            lut=self.reader.get("APARC",self.__current_subject,lut=True)
            self.__image_plane_widget.SetLookupTable(lut)
            #Important:
            self.__image_plane_widget.SetResliceInterpolateToNearestNeighbour()
        self.__current_image=new_image
        self.ren_win.Render()

    def change_image_orientation(self,orientation):
        """Changes the orientation of the current image
        to hide the image call hide_image
        orientation is a number from 0, 1 or 2 """
        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
        self.__image_plane_widget.set_orientation(orientation)
        self.ren_win.Render()

    def change_current_space(self):
        pass

    def reset_camera(self,position):
        """resets the current camera to standard locations. Position may be:
        0: initial 3d view
        1: left
        2: right
        3: front
        4: back
        5: top
        6: bottom"""

        positions_dict={
            0 : ((-3.5, 0, 13),(157, 154, 130),(0,0,1)),
            2 : ((-3.5, 0, 10),(250, 0, 10),(0,0,1)),
            1 : ((-3.5, 0, 10),(-250, 0, 10),(0,0,1)),
            4 : ((-3.5, 0, 10),(-3.5, -200, 10),(0,0,1)),
            3 : ((-3.5, 0, 10),(-3.5, 200, 10),(0,0,1)),
            5 : ((-3, 0, 3),(-3, 0, 252),(0,1,0)),
            6 : ((-3, 0, 3),(-3, 0, -252),(0,1,0)),
        }

        focal,position,viewup=positions_dict[position]

        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal)
        cam1.SetPosition(position)
        cam1.SetViewUp(viewup)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()

    def print_camera(self):
        cam1 = self.ren.GetActiveCamera()
        print "Camera coordinates:"
        print "focal: ",
        print cam1.GetFocalPoint()
        print "position: ",
        print cam1.GetPosition()
        print "viewUp: ",
        print cam1.GetViewUp()







