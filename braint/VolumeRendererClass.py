'''
Created on 26/10/2013

@author: jc.forero47
'''
import braviz
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

class VolumeRendererClass:
    def __init__(self):
        self.reader = braviz.readAndFilter.kmc40AutoReader()
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.renderer.SetBackground(0.0, 0.0, 0.0)
        
        self.current_actors = list()
        
    def load_model(self, vtk_structure, patient_number, vol_name):
        model = self.reader.get(vtk_structure, patient_number, name = vol_name)
        model_mapper=vtk.vtkPolyDataMapper()
        model_mapper.SetInputData(model)
        model_actor=vtk.vtkActor()
        model_actor.SetMapper(model_mapper)
        self.renderer.AddActor(model_actor)
        self.current_actors.append(model_actor)
        
    def refresh(self):
        self.render_window.Render()

    def remove_current_actors(self):
        '''
        Removes all the current actors-volumes
        '''
        for actor in self.current_actors:
            self.renderer.RemoveActor(actor)
            del actor
        
    def load_image_plane(self, type_image, patient_name, image_format):
        image=self.reader.get(type_image,patient_name, format = image_format)
        self.image_plane=braviz.visualization.persistentImagePlane()
        self.image_plane.SetInputData(image)
        
    def update_image_plane(self, type_image, patient_name, image_format):
        image=self.reader.get(type_image,patient_name, format = image_format)
        self.image_plane.SetInputData(image)
        
        
    def load_fibers(self,patient_number, fiber_color, fiber_waypoint):
        fibers_l=self.reader.get('fibers',patient_number,color = fiber_color, waypoint = fiber_waypoint)
        fiber_mapper=vtk.vtkPolyDataMapper()
        fiber_mapper.SetInputData(fibers_l)
        fiber_actor=vtk.vtkActor()
        fiber_actor.SetMapper(fiber_mapper)
        self.renderer.AddActor(fiber_actor)

    def get_render_window(self):
        return self.render_window

    def render(self, render_widget):
        interactor = render_widget.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        
        self.image_plane.SetInteractor(interactor)
        self.image_plane.On()
        interactor.Initialize()
        interactor.Start()
        
    #===========================================================================
    # def show_transform_grid(self, event=None):
    #     self.image_plane.GetTexturePlaneProperty().SetOpacity(1.0)
    #     
    #     grid_mapper=vtk.vtkPolyDataMapper()
    #     grid_actor=vtk.vtkActor()
    #     grid_actor.SetMapper(grid_mapper)
    #     self.renderer.AddActor(grid_actor)
    #     grid_actor.SetVisibility(0)
    #     
    #     
    #     if not select_show_warp_grid_status.get():
    #         grid_actor.SetVisibility(0)
    #         
    #         renWin.Render()
    #         return
    #     subj = select_subj_frame.get()
    #     #get original slice index
    #     p1 = planeWidget.GetPoint1()
    #     p2 = planeWidget.GetPoint2()
    #     center=(np.array(p1)+np.array(p2))/2
    #     orig_images={
    #         'MRI':      {'space':'world'},
    #         'FA':       {'space':'world'},
    #         'APARC' :   {'space':'world'},
    #         'Precision':{'space':'func_Precision'} ,
    #         'Power' :   {'space':'func_Power'},
    #     }
    # 
    #     #get orig_img
    #     orig_img_desc=orig_images[image_var.get()]
    #     if image_var.get() in ('Precision','Power'):
    #         orig_img = reader.get('fmri', subj, format='vtk', name=image_var.get(), **orig_img_desc)
    #     else:
    #         orig_img=reader.get(image_var.get(),subj,format='vtk',**orig_img_desc )
    #     #target_space -> world
    #     orig_center = reader.transformPointsToSpace(center, space_var.get(), subj, True)
    #     #world-> orig_space
    #     orig_center=reader.transformPointsToSpace(orig_center, orig_img_desc['space'], subj, False)
    #     #to image coordinates
    #     orig_img_center=(np.array(orig_center)-orig_img.GetOrigin())/orig_img.GetSpacing()
    #     orig_slice=round(orig_img_center[0])
    #     print orig_slice
    #     #get grid
    #     grid=braviz.visualization.build_grid(orig_img,orig_slice,5)
    #     #transform to current space
    #     #orig_space -> world
    #     grid = self.reader.transformPointsToSpace(grid, orig_img_desc['space'], subj, True)
    #     #world -> current space
    #     grid = self.reader.transformPointsToSpace(grid, space_var.get(), subj, False)
    #     #paint grid
    #     grid_mapper.SetInputData(grid)
    #     grid_actor.SetVisibility(1)
    #     self.image_plane.GetTexturePlaneProperty().SetOpacity(0.8)
    #     self.render_window.Render()
    #===========================================================================
        
    def clean_exit(self):
         self.render_window.Finalize()
         del self.render_window