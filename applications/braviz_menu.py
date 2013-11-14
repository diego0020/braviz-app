import Tkinter as tk
from Tkinter import Frame as tkFrame
from braviz.utilities import working_directory
import os.path as os_path
import subprocess
import sys
import tkFont
__author__ = 'Diego'

class MenuButton(tkFrame):
    def __init__(self,name,image,program,parent,**kw):
        tkFrame.__init__(self,parent,**kw)
        self.pack_propagate(0)
        with working_directory(os_path.dirname(__file__)):
            self.img=tk.PhotoImage(file=os_path.join("icons",image))
            def launch_program(event=None):
                subprocess.Popen((sys.executable,program))
        button=tk.Button(self,text=name,image=self.img,compound=tk.TOP,command=launch_program)
        button.pack(fill='both',expand=1)

applications_dict={
    "mult_var": ( "Multiple Variables", "multiple_variables.gif", "multiple_variables.py"),
    "comp_fib": (  "Compare Fibers","compare_fibers.gif","compareFibers.py"),
    "comp_str": ("Compare Structures"  ,"compare_structs.gif","compareStructs.py"),
    "fmri" : ("fMRI Explorer"     ,"explore_fmri.gif","explore_fmri.py"),
    "grid" : ("Grid Viewer"     ,"grid_view.gif","grid_view.py"),
    "mult" : ("Multiple Structures"     ,"mult_slicer.gif","mriMultSlicer.py"),
    "mri" : ("Images and tractography"      ,"mri1.gif","mriOne.py"),
    "ctxt" : ("Structures in context"     ,"mri1_context.gif","mriOneSlicer_context.py"),
    "surf" : ("Cortex Surfaces"     ,"surf.gif","mriOneSurf.py"),
    "tab" : ("Tabulas VS Structural"      ,"tab_vs_struct.gif","tab_vs_stcut.py"),
    "tms" : ("TMS View"      ,"tms.gif","tms_view2.py"),
    "braint" : ("Braint"      ,"braint.gif",os_path.join("..","braint","Braint_V_1_2.py")),
}


if __name__=="__main__":
    root=tk.Tk()
    root.title("Braviz-Menu")
    def create_and_grid(key, row, column):
        button1 = MenuButton(*applications_dict[key], parent=root, width=140, height=140)
        button1.grid(row=row, column=column, sticky='NSEW',padx=5,pady=5)

    font = tkFont.Font(size=12)
    single_label=tk.Label(root,text="Single Subject:",font=font,justify=tk.LEFT)
    single_label.grid(row=5,column=0,columnspan=1,sticky="WEN",pady=10)
    #single subject
    create_and_grid("mri", 10, 0)
    create_and_grid("fmri", 10, 1)
    create_and_grid("mult", 10, 2)
    create_and_grid("ctxt", 10, 3)
    create_and_grid("surf", 10, 4)
    mult_label = tk.Label(root, text="Multiple Subjects:",font=font,justify=tk.LEFT)
    mult_label.grid(row=15, column=0, columnspan=1, sticky="WEN",pady=10)
    #many subjects
    create_and_grid("tms", 20, 0)
    create_and_grid("mult_var",20,3)
    create_and_grid("grid", 20, 1)
    create_and_grid("tab", 20, 2)
    create_and_grid("braint", 20, 4)
    two_label = tk.Label(root, text="Two Subjects:",font=font,justify=tk.LEFT)
    two_label.grid(row=39, column=0, columnspan=1, sticky="WEN",pady=10)
    #two subjects
    create_and_grid("comp_fib", 40, 1)
    create_and_grid("comp_str", 40, 0)

    imagine_logo_path=os_path.join(os_path.dirname(__file__),"icons","imagine.gif")
    imagine_logo=tk.PhotoImage(file=imagine_logo_path)
    imagine_label=tk.Label(image=imagine_logo,width=140*3,justify=tk.RIGHT,anchor='se')
    imagine_label.grid(row=40,column=2,columnspan=3,rowspan=1,sticky='SE',padx=10)

    root.resizable(0, 0)
    root.mainloop()

