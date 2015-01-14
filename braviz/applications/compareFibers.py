##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

from __future__ import division
import Tkinter as tk
import tkFont
import ttk
import threading
import thread
from itertools import izip

import vtk
import numpy as np
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import braviz
from braviz.visualization.simple_vtk import persistentImagePlane, add_solid_balloon


scheduled_refresh = False
renWin,renWin2 = None,None
fibers_t = None
fibers2_t = None

class locked_IntVar(object):
    def __init__(self,x0):
        self.lock=threading.Lock()
        self.x=x0
    def set(self,v):
        self.lock.acquire()
        self.x=v
        self.lock.release()
    def get(self):
        self.lock.acquire()
        v=self.x
        self.lock.release()
        return v

class CompareFibers(object):
    def __init__(self):

        progress_internal=locked_IntVar(0)
        reader=braviz.readAndFilter.BravizAutoReader()
        initialized=False

        global renWin, renWin2, scheduled_refresh, fibers_t, fibers2_t
        ref_subj='144'
        curr_subj='093'
        curr_space='talairach'
        #Functionality
        dual_disp=True
        def changeReference(new_ref):
            #update GUI
            global ref_subj,img1
            ref_index=subjects.listVariable().index(ref_subj)
            subjects.itemconfigure(ref_index,background='')
            subjects.itemconfigure(ref_index,selectbackground='')
            ref_subj=new_ref
            ref_var.set(ref_subj)
            ref_index=subjects.listVariable().index(ref_subj)
            subjects.itemconfigure(ref_index,background='peach puff')
            subjects.itemconfigure(ref_index,selectbackground='firebrick1')
            select_model.changeSubj(ref_subj)
            #update display
            if active_planes.get():
                img1=reader.get('MRI',ref_subj,format='VTK',space=curr_space)
                planeWidget.SetInputData(img1)
            refresh_fibers()
            update_balloons()


        #Visualization
        img1=reader.get('MRI',ref_subj,format='VTK',space=curr_space)
        img2=reader.get('MRI',curr_subj,format='VTK',space=curr_space)

        picker = vtk.vtkCellPicker()
        picker.SetTolerance(0.005)

        ren1=vtk.vtkRenderer()
        ren2=vtk.vtkRenderer()
        #ren1.SetViewport(0,0.5,1,1)
        #ren2.SetViewport(0,0,1,0.5)
        renWin=vtk.vtkRenderWindow()
        renWin2=vtk.vtkRenderWindow()
        renWin.AddRenderer(ren1)
        renWin2.AddRenderer(ren2)
        ren1.SetBackground(0.1, 0.1, 0.1)

        #config=braviz.interaction.get_config(__file__)
        config=braviz.interaction.get_config()
        background= config.get_background()
        ren2.SetBackground(0.2,0.2,0.2)

        planeWidget= persistentImagePlane()
        planeWidget.SetInputData(img1)
        planeWidget.SetResliceInterpolateToNearestNeighbour() # Sin interpolar

        planeWidget.SetPicker(picker)
        renWin.SetSize(600, 300)
        renWin.SetSize(600, 300)

        planeWidget2= persistentImagePlane()
        planeWidget2.SetInputData(img2)
        planeWidget2.SetResliceInterpolateToNearestNeighbour() # Sin interpolar


        planeWidget2.SetResliceInterpolateToNearestNeighbour() # Sin interpolar

        planeWidget.SetPicker(picker)

        balloon=vtk.vtkBalloonWidget()
        balloon_repr=vtk.vtkBalloonRepresentation()
        balloon.SetRepresentation(balloon_repr)

        balloon2=vtk.vtkBalloonWidget()
        balloon2_repr=vtk.vtkBalloonRepresentation()
        balloon2.SetRepresentation(balloon2_repr)
        #planeWidget2.SetPicker(picker)



        ref_models={}
        other_models={}
        ref_actor2model={} #used for picking
        other_actor2model={}

        def addModel(model_name,addToRef=True):
            #if addToRef is True the model is added to the reference, otherwise to the other
            #if already exists make visible
            availableModels=reader.get('model',ref_subj,index='t') #always from reference
            if addToRef:
                models_dict=ref_models
                actor2model_dict=ref_actor2model
                ren=ren1
                subj=ref_subj
            else:
                models_dict=other_models
                actor2model_dict=other_actor2model
                if dual_disp:
                    ren=ren2
                else:
                    ren=ren1
                subj=curr_subj


            if models_dict.has_key(model_name):
                #update
                model,mapper,actor=models_dict[model_name]
                if model_name in availableModels:
                    model=reader.get('MODEL',subj,name=model_name,space=curr_space)
                    mapper.SetInputData(model)
                    if active_waypoints.get():
                        actor.SetVisibility(1)
                    models_dict[model_name]=(model,mapper,actor)
            else:
                #New model
                if model_name in availableModels:
                    model=reader.get('MODEL',subj,name=model_name,space=curr_space)
                    model_color=reader.get('MODEL',None,name=model_name,color='T')
                    if not addToRef and not dual_disp:
                        model_color=(0.1, 0.4, 0.2)
                    model_mapper=vtk.vtkPolyDataMapper()
                    model_actor=vtk.vtkActor()
                    model_properties=model_actor.GetProperty()
                    model_properties.SetColor(list(model_color[0:3]))
                    model_mapper.SetInputData(model)
                    model_actor.SetMapper(model_mapper)
                    ren.AddActor(model_actor)
                    models_dict[model_name]=(model,model_mapper,model_actor)
                    actor2model_dict[id(model_actor)]=model_name
                    if not active_waypoints.get():
                        model_actor.SetVisibility(0)
            if addToRef:
                model_volume=reader.get('model',ref_subj,name=model_name,volume='1')
                add_solid_balloon(balloon, models_dict[model_name][2], model_name,model_volume)
            else:
                #"show personalized message"
                volume_other=reader.get('model',curr_subj,name=model_name,volume='1')
                _,area_r=braviz.interaction.compute_volume_and_area(ref_models[model_name][0])
                _,area_o=braviz.interaction.compute_volume_and_area(other_models[model_name][0])
                vol_o=reader.get('model',curr_subj,name=model_name,volume='1')
                vol_r=reader.get('model',ref_subj,name=model_name,volume='1')
                vol_d=vol_o-vol_r
                area_d=area_o-area_r
                message="%s\nVolume* = %.2f mm3 ( %+.2f )\nSurface Area = %.2f mm2 ( %+.2f )"%(model_name,vol_o,vol_d,area_o,area_d)
                if dual_disp:
                    balloon2.AddBalloon(other_models[model_name][2], message)
                else:
                    balloon.AddBalloon(other_models[model_name][2], message)
            refresh_display()

        def removeModel(model_name,removeFromRef=True):
            #check that it actually exists
            if removeFromRef:
                models_dict=ref_models
                actor2model_dict=ref_actor2model
                ren=ren1
                ball=balloon
            else:
                models_dict=other_models
                actor2model_dict=other_actor2model
                if dual_disp:
                    ren=ren2
                    ball=balloon2
                else:
                    ren=ren1
                    ball=balloon
            if not models_dict.has_key(model_name):
                return
            model, mapper, actor=models_dict.pop(model_name)
            ren.RemoveActor(actor)
            ball.RemoveBalloon(actor)
            actor2model_dict.pop(id(actor))
            del actor
            del mapper
            del model
            refresh_display()

        def update_balloons():
            #to call when ref changes
            for model_name in other_models.iterkeys():
                vol_r,area_r=braviz.interaction.compute_volume_and_area(ref_models[model_name][0])
                vol_o,area_o=braviz.interaction.compute_volume_and_area(other_models[model_name][0])
                vol_d=vol_o-vol_r
                area_d=area_o-area_r
                message="%s\nVolume = %.2f mm3 ( %+.2f )\nSurface Area = %.2f mm2 ( %+.2f )"%(model_name,vol_o,vol_d,area_o,area_d)
                if dual_disp:
                    balloon2.AddBalloon(other_models[model_name][2], message)
                else:
                    balloon.AddBalloon(other_models[model_name][2], message)


        scheduled_refresh=False
        def refresh_display(*args):
            global scheduled_refresh
            if not scheduled_refresh:
                top.after_idle(do_refresh)
                scheduled_refresh=True

        def do_refresh():
            global scheduled_refresh
            ren1.ResetCameraClippingRange()
            ren2.ResetCameraClippingRange()
            renWin.Render()
            if dual_disp:
                renWin2.Render()
            scheduled_refresh=False


        #======fibers================

        waypoints=['Brain-Stem','ctx-lh-precentral']

        fibers_mapper=vtk.vtkPolyDataMapper()

        fibers_actor=vtk.vtkActor()
        fibers_actor.SetMapper(fibers_mapper)
        ren1.AddActor(fibers_actor)


        fibers_mapper2=vtk.vtkPolyDataMapper()

        fibers_actor2=vtk.vtkActor()
        fibers_actor2.SetMapper(fibers_mapper2)
        ren2.AddActor(fibers_actor2)

        processing_fibers=False
        processing_fibers_lock=threading.Lock()

        def async_read_fibers():
            global fibers_t,fibers2_t,processing_fibers
            progress_internal.set(10)
            fibers_t=reader.get('Fibers',ref_subj,waypoint=waypoints,space=curr_space,color=color_var.get())
            progress_internal.set(50)
            fibers2_t=reader.get('Fibers',curr_subj,waypoint=waypoints,space=curr_space,color=color_var.get())
            progress_internal.set(90)
            processing_fibers_lock.acquire()
            processing_fibers=False
            processing_fibers_lock.release()


        def end_refresh_fibers():
            processing_fibers_lock.acquire()
            if processing_fibers:
                top.after(10,end_refresh_fibers)
                progress.set(progress_internal.get())
            else:
                fibers_mapper.SetInputData(fibers_t)
                fibers_mapper2.SetInputData(fibers2_t)
                progress_internal.set(100)
                progress.set(progress_internal.get())
                fibers_balloons()
                for w in widgets:
                    w.config(state='normal')
                for w in combos:
                    w['state']='readonly'

                refresh_display()

            processing_fibers_lock.release()

        descriptors_cache={}
        def fibers_balloons():
            ref_key="ref %s %s"%(ref_subj,str(select_model.get()))
            #print ref_key
            if descriptors_cache.has_key(ref_key):
                d_r=descriptors_cache[ref_key]
            else:
                d_r=braviz.interaction.get_fiber_bundle_descriptors(fibers_t)
                descriptors_cache[ref_key]=d_r
            ref_message="""Reference bundle
        Number of fibers: %d
        Mean Length: %.2f
            Max: %.2f
            Min: %.2f
            Std: %.2f"""%d_r
            #TODO: Add a cache to avoid recalculating this
            other_key="other %s %s"%(curr_subj,str(select_model.get()))
            if descriptors_cache.has_key(other_key):
                d_o=descriptors_cache[other_key]
            else:
                d_o=braviz.interaction.get_fiber_bundle_descriptors(fibers2_t)
                descriptors_cache[other_key]=d_o

            deltas=np.subtract(d_o,d_r)
            combined_d=[]
            for o,d in izip(d_o,deltas):
                combined_d+=[o,d]
            custom_message="""Bundle
        Number of fibers: %d ( %+d )
        Mean Length (mm) : %.2f ( %+.2f )
            Max: %.2f ( %+.2f )
            Min: %.2f ( %+.2f )
            Std: %.2f ( %+.2f ) """%tuple(combined_d)


            balloon.AddBalloon(fibers_actor,ref_message)
            if dual_disp:
                balloon.RemoveBalloon(fibers_actor2)
                balloon2.AddBalloon(fibers_actor2,custom_message)
            else:
                balloon.RemoveBalloon(fibers_actor2)
                balloon.AddBalloon(fibers_actor2,custom_message) #To have it also in split view



        def refresh_fibers():
            global processing_fibers,waypoints
            waypoints=tuple(select_model.get())
            for w in widgets:
                w.config(state='disabled')
            for w in combos:
                w['state']='disabled'
            processing_fibers_lock.acquire()
            processing_fibers=True
            processing_fibers_lock.release()
            #async_read_fibers()
            thread.start_new_thread(async_read_fibers,tuple())
            top.after(10,end_refresh_fibers)



        #==========GUI========================
        root=tk.Tk()
        root.withdraw()
        top=tk.Toplevel()
        top.title('braviz-compareFibers')

        control_frame=tk.Frame(top,width=100)
        renderer_frame=tk.Frame(top)

        control_frame.grid(column=0,row=0,sticky='NS')
        renderer_frame.grid(column=1,row=0,sticky='SNEW')
        top.columnconfigure(1, weight=1)
        top.rowconfigure(0, weight=1)

        #===========Control====================
        def change_subj(event):
            global curr_subj
            curr_subj=subjects.get()
            if active_planes.get():
                if dual_disp:
                    img2=reader.get('MRI',curr_subj,format='vtk',space=curr_space)
                    planeWidget2.SetInputData(img2)
            wanted_models=select_model.get()
            #print wanted_models
            available2=reader.get('model',curr_subj,index='t')
            #print available2
            for m in wanted_models:
                if m in available2:
                    addModel(m, False)
                    #print 'adding %s'%m
                else:
                    removeModel(m, False)
            refresh_fibers()
            refresh_display()


        subjects=braviz.interaction.subjects_list(reader,change_subj,control_frame)
        subjects.grid(row=0)


        ref_index=subjects.listVariable().index(ref_subj)

        subjects.itemconfigure(ref_index,background='peach puff')
        subjects.itemconfigure(ref_index,selectbackground='firebrick1')

        def changeEntry(*args):
            entry_text=ref_var.get()
            if entry_text in subjects.listVariable():
                #valid subject
                changeReference(entry_text)
            else:
                ref_var.set(ref_subj)
            print "testing"

        ref_frame=tk.Frame(control_frame)
        ref_label=tk.Label(ref_frame,text=' Reference: ',justify='left',border=1)
        ref_label_font=tkFont.Font(font=ref_label['font'])
        ref_label_font['weight']='bold'
        ref_label.config(font=ref_label_font)

        ref_var=tk.StringVar()
        ref_var.set(ref_subj)
        ref_input=tk.Entry(ref_frame,width=10,textvariable=ref_var)
        ref_input.bind('<Return>', changeEntry)
        ref_label.grid(row=0,column=0,sticky='W',padx=1)
        ref_input.grid(row=0,column=1,sticky='E',columnspan=1,padx=1)
        ref_frame.columnconfigure(1, weight=1)
        ref_frame.grid(row=2,sticky='EW')

        def refButton(*args):
            changeReference(subjects.get())



        reference_button=tk.Button(control_frame,text='Set Reference',command=refButton)
        reference_button.grid(row=3,sticky='EW',pady=5)

        #=================================================================================

        interactive_plane_active=False
        ref_plane_Widget=vtk.vtkPlaneWidget()
        ref_plane_Widget2=vtk.vtkPlaneWidget()
        def activate_interactive_plane(event=None):
            global interactive_plane_active
            if interactive_plane_active:
                ref_plane_Widget.Off()
                ref_plane_Widget2.Off()
                interactive_plane_active=False
                plane_button.config(text='Activate interactive plane')
            else:
                ref_plane_Widget.On()
                ref_plane_Widget2.On()
                interactive_plane_active=True
                plane_button.config(text='Deactivate interactive plane')


        plane_button=tk.Button(control_frame,text='Activate interactive plane',command=activate_interactive_plane)
        plane_button.grid(sticky='we')


        #============================================================

        images_structs_frame=tk.Frame(control_frame)
        active_planes=tk.BooleanVar()
        active_planes.set(True)
        def imagePlanesStatus():
            #print "change in image planes, status=%s"%active_planes.get()
            if active_planes.get():
                planeWidget.On()
                planeWidget2.On()
            else:
                planeWidget.Off()
                planeWidget2.Off()
            refresh_display()

        active_waypoints=tk.BooleanVar()
        active_waypoints.set(True)
        def visibleStructsStatus():
            if active_waypoints.get():
                visibility=1
            else:
                visibility=0
            for k in ref_models.keys():
                actor=ref_models[k][2]
                actor.SetVisibility(visibility)
            for k in other_models.keys():
                actor=other_models[k][2]
                actor.SetVisibility(visibility)
            refresh_display()

        show_planes=tk.Checkbutton(images_structs_frame,text='Images',command=imagePlanesStatus,variable=active_planes,pady=10)
        show_planes.grid(row=0,column=0,sticky='ew')

        show_structs=tk.Checkbutton(images_structs_frame,text='Waypoints',command=visibleStructsStatus,variable=active_waypoints,pady=10)
        show_structs.grid(row=0,column=1,sticky='ew')

        images_structs_frame.columnconfigure(0, weight=1)
        images_structs_frame.columnconfigure(1, weight=1)


        images_structs_frame.grid(sticky='ew')



        def spaceChange(event=None):
            global curr_space
            curr_space=space_var.get()
            change_subj(None)
            changeReference(ref_subj)
            #print 'SpaceChange'
        space_frame=tk.Frame(control_frame)
        coordinates_label=tk.Label(space_frame,text='Coordinates:',pady=1)
        coordinates_label.grid(row=0,column=0,sticky='w')
        space_var=tk.StringVar()
        space_sel=ttk.Combobox(space_frame,textvariable=space_var,width=10)
        space_sel['values']=('World','Talairach','Dartel')
        space_sel['state']='readonly'
        space_sel.set('Talairach')
        space_sel.grid(row=0,column=1,sticky='e')
        space_sel.bind('<<ComboboxSelected>>',spaceChange)
        space_frame.columnconfigure(0, weight=1)
        space_frame.columnconfigure(1, weight=1)
        space_frame.grid(sticky='EW',pady=1)

        def change_split(event=None):
            global dual_disp,initial_sphere_pos
            #print "new split=%s"%split_var.get()
            if split_var.get()=='Together':
                print 'hola'
                render_widget.forget()
                render_widget2.grid_forget()

                render_widget.grid(row=0,column=0,sticky='SNEW')
                renderer_frame.columnconfigure(0, weight=1)
                renderer_frame.columnconfigure(1, weight=0)
                renderer_frame.rowconfigure(0, weight=1)
                renderer_frame.rowconfigure(1, weight=0)
                #remove objects from ren2 and add to ren1
                keys=tuple(other_models.keys())
                for k in keys:
                    removeModel(k, False)
                dual_disp=False
                for k in keys:
                    addModel(k, False)
                ren2.RemoveActor(fibers_actor2)
                ren1.AddActor(fibers_actor2)
                fibers_balloons()
                sphere_widget.On()
                if len(keys)>0:
                    xmax_s=[other_models[k][0].GetBounds()[1] for k in keys]
                    ymax_s=[other_models[k][0].GetBounds()[3] for k in keys]
                    zmax_s=[other_models[k][0].GetBounds()[5] for k in keys]

                    corner=[max(xmax_s),max(ymax_s),max(zmax_s)]
                else:
                    corner=(0,0,0)
                sphere_widget_repr.PlaceWidget(corner,corner)
                initial_sphere_pos=corner
                sphere_widget_repr.SetRadius(10)
                return

            if split_var.get()=='Vertical':
                render_widget.forget()
                render_widget2.forget()
                render_widget.grid(row=0,column=0,sticky='SNEW')
                render_widget2.grid(row=0,column=1,sticky='SNEW')
                renderer_frame.columnconfigure(0, weight=1)
                renderer_frame.columnconfigure(1, weight=1)
                renderer_frame.rowconfigure(0, weight=1)
                renderer_frame.rowconfigure(1, weight=0)

            if split_var.get()=='Horizontal':
                render_widget.forget()
                render_widget2.forget()
                render_widget.grid(row=0,column=0,sticky='SNEW')
                render_widget2.grid(row=1,column=0,sticky='SNEW')
                renderer_frame.columnconfigure(0, weight=1)
                renderer_frame.columnconfigure(1, weight=0)
                renderer_frame.rowconfigure(0, weight=1)
                renderer_frame.rowconfigure(1, weight=1)


            #remove objects from ren1 and add to ren2

            sphere_widget.Off()
            keys=tuple(other_models.keys())
            for k in keys:
                removeModel(k, False)
            dual_disp=True
            fibers_balloons()
            change_subj(None)
            ren1.RemoveActor(fibers_actor2)
            ren2.AddActor(fibers_actor2)
            fibers_actor2.SetPosition((0,0,0))
            follow_camera(ren1)
            copyPlane(ref_plane_Widget,None)
            refresh_display()
            return


        split_frame=tk.Frame(control_frame)
        split_label=tk.Label(split_frame,text='Split:',pady=1)
        split_label.grid(row=0,column=0,sticky='w')
        split_var=tk.StringVar()
        split_sel=ttk.Combobox(split_frame,textvariable=split_var,width=10)
        split_sel['values']=('Horizontal','Vertical','Together')
        split_sel['state']='readonly'
        split_sel.set('Horizontal')
        split_sel.grid(row=0,column=1,sticky='e')
        split_sel.bind('<<ComboboxSelected>>',change_split)
        split_frame.columnconfigure(0, weight=1)
        split_frame.columnconfigure(1, weight=1)
        split_frame.grid(sticky='EW',pady=1)
        #sep=ttk.Separator(control_frame,orient=tk.HORIZONTAL)
        #sep.grid(pady=10,padx=10,sticky='EW')

        def color_fibers(Event=None):
            refresh_fibers()
            refresh_display()

        color_frame=tk.Frame(control_frame)
        color_label=tk.Label(color_frame,text='Color:',pady=1)
        color_label.grid(row=0,column=0,sticky='w')
        color_var=tk.StringVar()
        color_sel=ttk.Combobox(color_frame,textvariable=color_var,width=10)
        color_sel['values']=('Orient','FA','Y','Rand','Curv')
        color_sel['state']='readonly'
        color_sel.set('Orient')
        color_sel.grid(row=0,column=1,sticky='e')
        color_sel.bind('<<ComboboxSelected>>',color_fibers)
        color_frame.columnconfigure(0, weight=1)
        color_frame.columnconfigure(1, weight=1)
        color_frame.grid(sticky='EW',pady=5)


        #==============================================

        def changeStruct(action,model):
            #print "struct change %s, %s"%(action,model)
            if action=='add':
                addModel(model, True)
                addModel(model, False)
            else:
                removeModel(model, True)
                removeModel(model, False)
            #if initialized:
            #    refresh_fibers()
            #refresh_display()
        def calculate_fibers(event=None):
            if initialized:
                refresh_fibers()
            refresh_display()

        select_model=braviz.interaction.structureList(reader,ref_subj,changeStruct , control_frame,waypoints,text='Waypoints',padx=10,pady=15)
        select_model.grid(row=20,sticky='WESN',pady=5)
        control_frame.rowconfigure(20, weight=1)

        calculate_but=tk.Button(control_frame,text="Calculate fibers",command=calculate_fibers)
        calculate_but.grid(row=21,sticky='ew')


        #=============================progress=======================



        progress=tk.IntVar()
        progress.set(progress_internal.get())

        fibers_progress_bar=ttk.Progressbar(control_frame,orient='horizontal',length='100',mode='determinate',variable=progress)
        fibers_progress_bar.grid(row=22,pady=10)

        #==================DISPLAY FRAME===========================================




        render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                                    rw=renWin,width=600,
                                                    height=300)
        render_widget2 = vtkTkRenderWindowInteractor(renderer_frame,
                                                    rw=renWin2,width=600,
                                                    height=300)
        render_widget.grid(row=0,sticky='WESN')
        render_widget2.grid(row=1,sticky='WESN')
        renderer_frame.rowconfigure(0, weight=1)
        renderer_frame.rowconfigure(1, weight=1)
        renderer_frame.columnconfigure(0, weight=1)

        def clean_exit():
            global renWin,renWin2
            print "adios"
            renWin.Finalize()
            renWin2.Finalize()
            del renWin
            del renWin2
            render_widget.destroy()
            render_widget2.destroy()
            root.quit()
            root.destroy()
        top.protocol("WM_DELETE_WINDOW", clean_exit)
        iact = render_widget.GetRenderWindow().GetInteractor()
        iact2 = render_widget2.GetRenderWindow().GetInteractor()
        planeWidget.SetDefaultRenderer(ren1)
        planeWidget.SetInteractor(iact)
        planeWidget.On()

        planeWidget2.SetDefaultRenderer(ren2)
        planeWidget2.SetInteractor(iact2)
        planeWidget2.On()

        balloon.SetInteractor(iact)
        balloon2.SetInteractor(iact2)

        balloon.On()
        balloon2.On()

        iact2.Initialize()
        #iact.AddObserver(vtk.vtkCommand.LeftButtonPressEvent,picking,10)

        custom_iact_style=config.get_interaction_style()
        iact_style=getattr(vtk,custom_iact_style)()
        iact.SetInteractorStyle(iact_style)

        iact2_style=getattr(vtk,custom_iact_style)()
        iact2.SetInteractorStyle(iact2_style)
        #===========Initial view==============

        cam1 = ren1.GetActiveCamera()
        cam1.SetPosition(-500,0,0)
        cam1.Elevation(0)
        cam1.SetViewUp(0, 0, 1)
        cam1.Azimuth(0)
        ren1.ResetCameraClippingRange()

        cam2 = ren2.GetActiveCamera()
        cam2.SetPosition(-500,0,0)
        cam2.Elevation(0)
        cam2.SetViewUp(0, 0, 1)
        cam2.Azimuth(0)
        ren2.ResetCameraClippingRange()

        planeWidget.SetSliceIndex(110)
        planeWidget2.SetSliceIndex(110)

        #======================VTK INTERACTION==============================

        #follow cameras
        def follow_camera(reference):
            if not dual_disp:
                return
            obj=reference
            if obj==ren1:
                follower=ren2
            else:
                follower=ren1
            cam1=obj.GetActiveCamera()
            position=cam1.GetPosition()
            focal_point=cam1.GetFocalPoint()
            viewup=cam1.GetViewUp()
            cam2=follower.GetActiveCamera()
            cam2.SetPosition(position)
            cam2.SetFocalPoint(focal_point)
            cam2.SetViewUp(viewup)
            follower.ResetCameraClippingRange()
            refresh_display()

        def iactEvent(obj,event):
            if not dual_disp:
                return
            pos = obj.GetEventPosition()
            ref=obj.FindPokedRenderer(*pos)
            follow_camera(ref)

        copying=False
        slicing=False
        def replicateCursor(obj=None,event=None):
            global copying,slicing
            if copying:
                return
            if not dual_disp:
                return
            copying=True
            #print event
            if obj==planeWidget:
                slave=iact2
                ref=iact
                plane2=planeWidget2
            else:
                slave=iact
                ref=iact2
                plane2=planeWidget

            x,y=list(ref.GetEventPosition())

            slave.SetEventInformation(x,y)
            if(event=='StartInteractionEvent'):
                if MiddleButton:
                    slave.InvokeEvent('MiddleButtonPressEvent')
                    slicing=True
                else:
                    slave.InvokeEvent('LeftButtonPressEvent')
            elif(event=='EndInteractionEvent'):
                if slicing:
                    slave.InvokeEvent('MiddleButtonReleaseEvent')
                    slicing=False
                else:
                    slave.InvokeEvent('LeftButtonReleaseEvent')
            elif(event=='InteractionEvent'):
                if slicing:
                    plane2.SetSliceIndex(obj.GetSliceIndex())
                    plane2.InvokeEvent('InteractionEvent')
                else:
                    slave.MouseMoveEvent()
            elif(event=='WindowLevelEvent'):
                wl=[0,0]
                obj.GetWindowLevel(wl)
                plane2.SetWindowLevel(*wl)
            copying=False



        MiddleButton=False
        def detectMiddleButton(obj,event):
            global MiddleButton
            if not dual_disp:
                return
            if event=='MiddleButtonPressEvent':
                MiddleButton=True
            else:
                MiddleButton=False


        iact.AddObserver(vtk.vtkCommand.RenderEvent ,iactEvent,0.0)
        iact2.AddObserver(vtk.vtkCommand.RenderEvent ,iactEvent,0.0)
        iact.AddObserver('MiddleButtonPressEvent',detectMiddleButton,5000)
        iact2.AddObserver('MiddleButtonPressEvent',detectMiddleButton,5000)
        iact.AddObserver('MiddleButtonReleaseEvent',detectMiddleButton,500)
        iact2.AddObserver('MiddleButtonReleaseEvent',detectMiddleButton,500)
        planeWidget.AddObserver(vtk.vtkCommand.AnyEvent,replicateCursor,1000)
        planeWidget2.AddObserver(vtk.vtkCommand.AnyEvent,replicateCursor,1000)


        #=============Sphere Widget===================

        sphere_widget=vtk.vtkSphereWidget2()
        sphere_widget_repr=vtk.vtkSphereRepresentation()
        sphere_widget.SetInteractor(iact)
        sphere_widget.SetRepresentation(sphere_widget_repr)
        sphere_widget.PickingManagedOn()

        sphere_widget.ScalingEnabledOff()
        sphere_widget_repr.HandleVisibilityOff()
        sphere_widget_repr.SetRepresentationToSurface()
        sphere_widget_repr.SetRadius(5)
        sphere_widget.SetPriority(8)
        sphere_widget.SetKeyPressActivation(0)

        prop=sphere_widget_repr.GetSphereProperty()
        prop.SetColor(0.1, 0.4, 0.2)
        prop=sphere_widget_repr.GetSelectedSphereProperty()
        prop.SetColor(0.9,0.1,0.1)
        sphere_widget_repr.PlaceWidget((0,0,0),(0,0,0))

        initial_sphere_pos=(0,0,0)
        def move_sphere(obj,event):
            new_pos=sphere_widget_repr.GetCenter()
            displacement=[x-y for x,y in izip(new_pos,initial_sphere_pos)]
            for triplet in other_models.values():
                actor=triplet[2]
                actor.SetPosition(displacement)
            fibers_actor2.SetPosition(displacement)
            refresh_display()

        sphere_widget.AddObserver(vtk.vtkCommand.InteractionEvent,move_sphere)

        #======================Plane Widget==================


        ref_plane_Widget.SetInteractor(iact)
        ref_plane_Widget2.SetInteractor(iact2)
        for plane in [ref_plane_Widget,ref_plane_Widget2]:
            plane.SetOrigin(-25, -25, 0)
            plane.SetPoint1(50,-25,0)
            plane.SetPoint2(-25,50,0)
            plane.PickingManagedOn()
            plane.SetRepresentationToSurface()
            prop=plane.GetPlaneProperty()
            prop.SetColor(0.5,0.5,0.5)
            plane.PlaceWidget()
            plane.SetKeyPressActivation(0)
            plane.SetPriority(5)
            plane.Off()


        def reset_planes():
            global ref_plane_Widget,ref_plane_Widget2,plane_reset_queued
            print 'resetting'
            keys=other_models.keys()
            for k in keys:
                removeModel(k, False)
            keys=ref_models.keys()
            for k in keys:
                removeModel(k, True)

            for plane in [ref_plane_Widget,ref_plane_Widget2]:
                plane.SetOrigin(-25, -25, 0)
                plane.SetPoint1(50,-25,0)
                plane.SetPoint2(-25,50,0)
                plane.UpdatePlacement()
                plane.On()

            plane_reset_queued=False
            spaceChange(None)

        plane_reset_queued=False
        def copyPlane(obj,event):
            global plane_reset_queued
            if not dual_disp:
                return
            if obj==ref_plane_Widget:
                ref=ref_plane_Widget
                slave=ref_plane_Widget2
            else:
                ref=ref_plane_Widget2
                slave=ref_plane_Widget
            try:
                slave.SetCenter(ref.GetCenter())
                slave.SetPoint1(ref.GetPoint1())
                slave.SetPoint2(ref.GetPoint2())
                slave.SetOrigin(ref.GetOrigin())
                #slave.SetNormal(ref.GetNormal())
                slave.UpdatePlacement()
            except TypeError:
                print "Fatal Error, don't move handlers out of render window please"
                if not plane_reset_queued:
                    top.after(1000, reset_planes)
                    plane_reset_queued=True
                #raise
            refresh_display()

        ref_plane_Widget.AddObserver(vtk.vtkCommand.InteractionEvent,copyPlane,10)
        ref_plane_Widget2.AddObserver(vtk.vtkCommand.InteractionEvent,copyPlane,10)

        widgets=[select_model,plane_button,show_planes,show_structs,reference_button,ref_input,subjects,calculate_but]
        combos=[split_sel,space_sel]

        #====================================

        refresh_fibers()
        initialized=True
        root.mainloop()

if __name__ == "__main__":
    CompareFibers()