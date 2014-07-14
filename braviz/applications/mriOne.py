from __future__ import division
import Tkinter as tk
import ttk

import numpy as np
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor

import braviz
import braviz.utilities

if __name__ == "__main__":
    braviz.utilities.configure_console_logger("mriOne")


    reader = braviz.readAndFilter.BravizAutoReader()
    FUNCTIONAL_PARADIGMS=list(reader.get("fMRI",None,index=True))

    initial_subject = reader.get("ids")[0]

    img = reader.get('MRI', initial_subject, format='VTK')

    config = braviz.interaction.get_config(__file__)
    background = config.get_background()

    picker = vtk.vtkCellPicker()
    picker.SetTolerance(0.005)

    #Visualization
    ren = vtk.vtkRenderer()
    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(ren)
    ren.SetBackground(background)

    planeWidget = braviz.visualization.persistentImagePlane()
    planeWidget.SetInputData(img)

    planeWidget.SetPicker(picker)
    planeWidget.UpdatePlacement()
    renWin.SetSize(600, 600)


    # An outline is shown for context.
    outline = vtk.vtkOutlineFilter()
    outline.SetInputData(img)

    outlineMapper = vtk.vtkPolyDataMapper()
    outlineMapper.SetInputConnection(outline.GetOutputPort())

    outlineActor = vtk.vtkActor()
    outlineActor.SetMapper(outlineMapper)
    ren.AddActor(outlineActor)

    aparc_lut = reader.get('aparc', None, lut=1)
    previous_img = 'MRI'
    mri_window_level = [0, 0]
    mri_lut = vtk.vtkLookupTable()
    fa_lut = vtk.vtkLookupTable()
    fa_lut.SetRampToLinear()
    fa_lut.SetTableRange(0.0, 1.0)
    fa_lut.SetHueRange(0.0, 0.0)
    fa_lut.SetSaturationRange(1.0, 1.0)
    fa_lut.SetValueRange(0.0, 1.0)
    fa_lut.Build()

    fmri_color_int = vtk.vtkColorTransferFunction()
    fmri_color_int.ClampingOn()
    fmri_color_int.SetColorSpaceToRGB()
    fmri_color_int.SetRange(-7, 7)
    fmri_color_int.Build()
    #                           x   ,r   ,g   , b
    fmri_color_int.AddRGBPoint(-7.0, 0.0, 1.0, 1.0)
    fmri_color_int.AddRGBPoint(-3.0, 0.0, 0.0, 0.0)
    fmri_color_int.AddRGBPoint(0.0, 0.0, 0.0, 0.0)
    fmri_color_int.AddRGBPoint(3.0, 0.0, 0.0, 0.0)
    fmri_color_int.AddRGBPoint(7.0, 1.0, 0.27, 0.0)

    fmri_lut = vtk.vtkLookupTable()
    fmri_lut.SetTableRange(-7.0, 7.0)
    fmri_lut.SetNumberOfColors(101)
    fmri_lut.Build()
    for i in range(101):
        s = -7 + 14 * i / 100
        if False and (s < -3 or s > 3):
            color = list(fmri_color_int.GetColor(s)) + [0.0]
        else:
            color = list(fmri_color_int.GetColor(s)) + [1.0]
        fmri_lut.SetTableValue(i, color)


    def setSubj(event=None):
        global previous_img
        #print subj
        subj = select_subj_frame.get()
        if previous_img == 'MRI':
            planeWidget.GetWindowLevel(mri_window_level)
            mri_lut.DeepCopy(planeWidget.GetLookupTable())
        selected_img = image_var.get()
        img = None
        if selected_img in FUNCTIONAL_PARADIGMS:
            try:
                mri_img = reader.get('MRI', subj, format='VTK', space=space_var.get())
            except Exception:
                mri_img = None
                print "No mri img found"
            selected_pdgm = image_var.get()
            if selected_pdgm == 'Precision':
                fmri_name = 'Precision'
            elif selected_pdgm == 'Power':
                fmri_name = 'PowerGrip'
            else:
                fmri_name = selected_pdgm
            try:
                fa_img = reader.get('fMRI', subj, format='vtk', space=space_var.get(), name=fmri_name)
            except IOError:
                print "%s not available for subject %s" % (fmri_name, subj)
                fa_img = None

            if fa_img is not None and mri_img is not None:
                planeWidget.On()
                blend = vtk.vtkImageBlend()
                color_mapper2 = vtk.vtkImageMapToColors()
                color_mapper2.SetInputData(fa_img)
                color_mapper2.SetLookupTable(fmri_color_int)
                blend.AddInputConnection(color_mapper2.GetOutputPort())
                planeWidget.text1_value_from_img(fa_img)

                color_mapper1 = vtk.vtkImageMapToWindowLevelColors()
                color_mapper1.SetInputData(mri_img)
                color_mapper1.SetLookupTable(mri_lut)
                #color_mapper1.SetWindow(mri_window_level[1])
                #color_mapper1.SetLevel(mri_window_level[0])

                blend.AddInputConnection(color_mapper1.GetOutputPort())

                blend.SetOpacity(0, .5)
                blend.SetOpacity(1, .5)
                blend.Update()
                img = blend.GetOutput()
                planeWidget.SetInputData(img)
            else:
                planeWidget.Off()
                img = None


            #img=fa_img
            #print img
        else:
            try:
                img = reader.get(selected_img, subj, format='VTK', space=space_var.get())
                planeWidget.text1_to_std()
            except Exception:
                img = None
                planeWidget.Off()
            else:
                planeWidget.SetInputData(img)
                planeWidget.On()
        if selected_img == 'MRI':
            planeWidget.SetLookupTable(mri_lut)
            planeWidget.SetWindowLevel(*mri_window_level)
            planeWidget.SetResliceInterpolateToCubic()
        elif selected_img == 'APARC':
            planeWidget.SetLookupTable(aparc_lut)
            planeWidget.SetResliceInterpolateToNearestNeighbour()
        elif selected_img == 'FA':
            planeWidget.SetLookupTable(fa_lut)
            planeWidget.SetResliceInterpolateToCubic()
        elif selected_img in FUNCTIONAL_PARADIGMS:
            #planeWidget.SetLookupTable(mri_lut)
            planeWidget.GetColorMap().SetLookupTable(None)
            #planeWidget.UserControlledLookupTableOff()
            planeWidget.SetResliceInterpolateToCubic()
        try:
            aparc_img = reader.get('aparc', subj, format='VTK', space=space_var.get())
        except Exception:
            aparc_img = None
        planeWidget.addLabels(aparc_img)
        planeWidget.setLabelsLut(aparc_lut)

        if img is not None:
            outline.SetInputData(img)
        previous_img = selected_img
        paint_fibers()
        show_transform_grid()
        #renWin.Render() called by paint fibers


    #================================Fibers==============================
    fib_mapper = vtk.vtkPolyDataMapper()
    fib_actor = vtk.vtkActor()
    fib_actor.SetVisibility(0)
    fib_actor.SetMapper(fib_mapper)
    ren.AddActor(fib_actor)


    def paint_fibers(event=None):
        if active_fibers.get():
            subj = select_subj_frame.get()
            try:
                fibers = reader.get('fibers', subj, space=space_var.get(), color=tract_var.get())
            except Exception:
                fib_actor.SetVisibility(0)
            else:
                fib_mapper.SetInputData(fibers)
                fib_actor.SetVisibility(1)
        else:
            fib_actor.SetVisibility(0)
        renWin.Render()


    grid_mapper = vtk.vtkPolyDataMapper()
    grid_actor = vtk.vtkActor()
    grid_actor.SetMapper(grid_mapper)
    ren.AddActor(grid_actor)
    grid_actor.SetVisibility(0)


    def show_transform_grid(event=None):
        if not select_show_warp_grid_status.get():
            grid_actor.SetVisibility(0)
            planeWidget.GetTexturePlaneProperty().SetOpacity(1.0)
            renWin.Render()
            return
        subj = select_subj_frame.get()
        #get original slice index
        p1 = planeWidget.GetPoint1()
        p2 = planeWidget.GetPoint2()
        center = (np.array(p1) + np.array(p2)) / 2
        orig_images = {
            'MRI': {'space': 'world'},
            'FA': {'space': 'world'},
            'APARC': {'space': 'world'},
            'Precision': {'space': 'func_Precision'},
            'Power': {'space': 'func_Power'},
        }

        #get orig_img
        orig_img_desc = orig_images[image_var.get()]
        if image_var.get() in FUNCTIONAL_PARADIGMS:
            orig_img = reader.get('fmri', subj, format='vtk', name=image_var.get(), **orig_img_desc)
        else:
            orig_img = reader.get(image_var.get(), subj, format='vtk', **orig_img_desc)
        #target_space -> world
        orig_center = reader.transformPointsToSpace(center, space_var.get(), subj, True)
        #world-> orig_space
        orig_center = reader.transformPointsToSpace(orig_center, orig_img_desc['space'], subj, False)
        #to image coordinates
        orig_img_center = (np.array(orig_center) - orig_img.GetOrigin()) / orig_img.GetSpacing()
        orig_slice = round(orig_img_center[0])
        print orig_slice
        #get grid
        grid = braviz.visualization.build_grid(orig_img, orig_slice, 5)
        #transform to current space
        #orig_space -> world
        grid = reader.transformPointsToSpace(grid, orig_img_desc['space'], subj, True)
        #world -> current space
        grid = reader.transformPointsToSpace(grid, space_var.get(), subj, False)
        if space_var.get().lower() == 'dartel':
            grid = braviz.visualization.remove_nan_from_grid(grid)
        #paint grid
        grid_mapper.SetInputData(grid)
        grid_actor.SetVisibility(1)
        planeWidget.GetTexturePlaneProperty().SetOpacity(0.8)
        renWin.Render()


    #===============================================Inteface=================================

    root = tk.Tk()
    root.withdraw()
    top = tk.Toplevel(root)
    top.title('BraViz-Mri')

    control_frame = tk.Frame(top, width=100)

    select_subj_frame = braviz.interaction.subjects_list(reader, setSubj, control_frame, text='Subject', padx=10, pady=5,
                                                         height='100')
    select_subj_frame.pack(side='top')

    coordinates_label = tk.Label(control_frame, text='Coordinates:', pady=10)
    coordinates_label.pack(side='top')
    space_var = tk.StringVar()
    space_sel = ttk.Combobox(control_frame, textvariable=space_var)
    space_sel['values'] = ('World', 'Talairach', 'Dartel')
    space_sel['state'] = 'readonly'
    space_sel.set('World')
    space_sel.pack(side='top')
    space_sel.bind('<<ComboboxSelected>>', setSubj)

    select_show_warp_grid_status = tk.BooleanVar()
    select_show_warp_grid_status.set(False)
    select_show_warp_grid = tk.Checkbutton(control_frame, text="Show tranform grid", variable=select_show_warp_grid_status,
                                           command=show_transform_grid)
    select_show_warp_grid.pack(side='top')

    image_label = tk.Label(control_frame, text='Image:', pady=10)
    image_label.pack(side='top')
    image_var = tk.StringVar()
    image_sel = ttk.Combobox(control_frame, textvariable=image_var)
    image_sel['values'] = ('MRI', 'FA', 'APARC')+tuple(FUNCTIONAL_PARADIGMS)
    image_sel['state'] = 'readonly'
    image_sel.set('MRI')
    image_sel.pack(side='top')
    image_sel.bind('<<ComboboxSelected>>', setSubj)


    #---------------------------------------------------------
    separator = ttk.Separator(control_frame, orient='horizontal')
    separator.pack(side='top', fill='x', pady=20)

    active_fibers = tk.BooleanVar()
    add_fibers = tk.Checkbutton(control_frame, text='Show tractography', pady=10, variable=active_fibers,
                                command=paint_fibers)
    add_fibers.pack(side='top')

    tract_label = tk.Label(control_frame, text='Color:', pady=10)
    tract_label.pack(side='top')
    tract_var = tk.StringVar()
    tract_sel = ttk.Combobox(control_frame, textvariable=tract_var)
    tract_sel['values'] = ('Orient', 'FA', 'Curv', 'Rand', 'y')
    tract_sel['state'] = 'readonly'
    tract_sel.set('orient')
    tract_sel.pack(side='top')
    tract_sel.bind('<<ComboboxSelected>>', paint_fibers)


    #=====================================================================
    display_frame = tk.Frame(top)
    control_frame.pack(side="left", anchor="n", fill="y", expand="false")
    display_frame.pack(side="left", anchor="n", fill="both", expand="true")
    renderer_frame = tk.Frame(display_frame)
    renderer_frame.pack(padx=3, pady=3, side="left",
                        fill="both", expand="true")

    render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                                rw=renWin, width=600,
                                                height=600)


    def clean_exit():
        global renWin
        print "adios"
        renWin.Finalize()
        del renWin
        render_widget.destroy()
        root.quit()
        root.destroy()


    top.protocol("WM_DELETE_WINDOW", clean_exit)

    render_widget.pack(fill='both', expand='true')
    #display_frame.pack(side="top", anchor="n", fill="both", expand="true")
    iact = render_widget.GetRenderWindow().GetInteractor()
    custom_iact_style = config.get_interaction_style()
    iact_style = getattr(vtk, custom_iact_style)()
    iact.SetInteractorStyle(iact_style)
    planeWidget.SetInteractor(iact)
    planeWidget.On()

    cam1 = ren.GetActiveCamera()
    cam1.Elevation(80)
    cam1.SetViewUp(0, 0, 1)
    cam1.Azimuth(80)
    ren.ResetCameraClippingRange()
    render_widget.Render()

    iact.Initialize()
    renWin.Render()
    iact.Start()
    setSubj()
    # Start Tkinter event loop

    root.mainloop()