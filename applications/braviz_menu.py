import Tkinter as tk
from Tkinter import Frame as tkFrame
from braviz.utilities import working_directory
import os.path as os_path
__author__ = 'Diego'

class MenuButton(tkFrame):
    def __init__(self,parent,**kw):
        tkFrame.__init__(self,parent,**kw)
        self.pack_propagate(0)
        with working_directory(os_path.dirname(__file__)):
            self.img=tk.PhotoImage(file="test.gif")
        button=tk.Button(self,text="hola",image=self.img,compound=tk.TOP)
        button.pack(fill='both',expand=1)

if __name__=="__main__":
    root=tk.Tk()
    button1=MenuButton(root,width=120,height=140)
    button1.grid()
    root.mainloop()

