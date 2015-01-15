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


"""This module contains complex -tk widgets and associated functions which can be used for building tk interfaces"""

import Tkinter as tk
from Tkinter import LabelFrame
import ast
import logging

from braviz.interaction.tk_tooltip import ToolTip


class subjects_list(LabelFrame):
    """A subjects list  tkMegaWidget. It gets the available subjects from a braviz reader and calls a function when changed
    The get method can be used to query the currently selected subject
    The listVariable method returns a tuple conaining the available items in the list"""
    def __init__(self,reader,function,master,**kw):
        """the reader should be a braviz reader which is used to populate the list of available subjects
        the function is called whenever the selection changes
        master is the parent tk_widget
        Additional keyword parameters are directly passed to the tk_widget frame constructor"""
        if not kw.has_key('text'):
            kw['text']='Subject'
        if not kw.has_key('padx'):
            kw['padx']=10
        if not kw.has_key('pady'):
            kw['pady']=5
        LabelFrame.__init__(self,master,**kw)
        list_and_bar=tk.Frame(self)
        list_and_bar.pack(side='top',fill='both',expand=1)
        scrollbar=tk.Scrollbar(list_and_bar,orient=tk.VERTICAL)
        self.tk_listvariable=tk_listvariable=tk.StringVar()
        subjects_list_box=tk.Listbox(list_and_bar,selectmode=tk.BROWSE,yscrollcommand=scrollbar.set,exportselection=0,listvariable=tk_listvariable)
        scrollbar.config(command=subjects_list_box.yview)
        scrollbar.pack(side=tk.RIGHT,fill=tk.Y)
        subjects_list_box.pack(side="left",fill='both',expand=1)
        subjects=reader.get('ids')
        self.list=subjects
        self.subjects_list=subjects_list_box
        tk_listvariable.set(tuple(subjects))
        subjects_list_box.select_set(0,0)
        subjects_list_box.bind('<<ListboxSelect>>',function)
        subjects_list_box.bind('<Double-Button-1>',function)
        master.bind('<Return>', function)
        subjects_list_box.bind('<Key>',function)
        self.itemconfigure=subjects_list_box.itemconfigure
    def get(self):
        """Gets the currently selected subject"""
        select_idx=self.subjects_list.curselection()
        #print select_idx
        subj=self.subjects_list.get(select_idx)
        return subj
    def config(self,**kw):
        """Intercepts state option and passes it to the listbox widget, other options are passed directly to the tkFrame"""
        if kw.has_key('state'):
            new_state=kw.pop('state')
            self.subjects_list.config(state=new_state)
        LabelFrame.config(self, **kw)
    def configure(self,**kw):
        """Alias to config"""
        self.config(**kw)
    def listVariable(self):
        """Returns a tuple containing the subjects in the list"""
        return ast.literal_eval(self.tk_listvariable.get())
    
    
    def setSelection(self, index):
        """YOYIS: Sets the current selection to the given index"""
        #print self.subjects_list.size()
        self.subjects_list.selection_clear(0, tk.END)
        self.subjects_list.selection_set(index, index)
        self.subjects_list.see(index)
    def getSelectionIndex(self, value):
        """YOYIS: Returns the index of the given value in the patients list"""
        return self.list.index(value)

class structureList(LabelFrame):
    """A tkMegaWidget for listing freesurfer segmentation models.
    By default the list allows multiple selections.
    It maintains an internal list of structures directly chosen by the user.
    When a change in the selection is made the command function is called, 
    with 'add' or 'remove' as the first argument, and the changed model name as the second argument
    The changeSubj method can be used to change the subject to which the list of structures match
    Not all subjects have the same structures, the list of directly chosen structures is not changed
    when the subject changes, but the command function is called in order to do the corresponding changes
    (See mriMultSlicer application for an example)
    The listVariable method returns a tuple with the models currently in the list
    The get method can be used to retrieve a list of currently selected models"""
    
    def __init__(self,reader,initial_subj,command,parent,initial_models=None,**kw):
        """the reader should be a braviz reader which is used to populate the list of available structures
        initial_subj is the subject initially used to populate the list
        command is called whenever the selection changes, with 'add' or 'remove' as first argument and the changed model name as second argument
        parent is the parent tk_widget
        Additional keyword parameters are directly passed to the tk_widget frame constructor"""
        if not kw.has_key('text'):
            kw['text']='Models'
        if not kw.has_key('padx'):
            kw['padx']=10
        if not kw.has_key('pady'):
            kw['pady']=5
        LabelFrame.__init__(self, parent, **kw)
        model_list_and_bar=tk.Frame(self)
        model_list_and_bar.pack(side='top',fill='both',expand=1)
        model_scrollbar=tk.Scrollbar(model_list_and_bar,orient=tk.VERTICAL)
        self.tk_listvariable=tk.StringVar()
        model_list=tk.Listbox(model_list_and_bar,selectmode=tk.MULTIPLE,yscrollcommand=model_scrollbar.set,exportselection=0,listvariable=self.tk_listvariable)
        model_scrollbar.config(command=model_list.yview)
        model_scrollbar.pack(side=tk.RIGHT,fill=tk.Y,expand=1)
        model_list.pack(side="left",fill='both',expand=1)
        model_list.bind('<<ListboxSelect>>',self.__update)
        
        availableModels=reader.get('model',initial_subj,index='t')
        self.tk_listvariable.set(tuple(sorted(availableModels)))
        
        if initial_models is not None:
            self.chosen_models=set(initial_models)
        else:
            self.chosen_models= {'CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior'}
        for m in self.chosen_models:
            try:
                index=self.listVariable().index(m)
            except ValueError:
                pass
            else:
                model_list.selection_set(index)
                if command is not None:
                    command('add',m)
        
        self.previous_selection=set(model_list.curselection())
        self.command=command
        self.model_list=model_list
        self.reader=reader
        self.model_list=model_list
        
        #Replicate list Interface
        self.see=model_list.see
        self.itemconfigure=model_list.itemconfigure
        self.itemconfig=model_list.itemconfig
        self.tool_tip=ToolTip(model_list,msgFunc=self.__get_tooltip,follow=1, delay=0.5)
        from braviz.readAndFilter.link_with_rdf import cached_get_free_surfer_dict
        self.cool_names=cached_get_free_surfer_dict(reader)
        parent.focus()
    def __update(self,*args):
        """Internally handles changes in subject selection and calls 'command' if necessary"""
        model_idx=set(self.model_list.curselection())
        chosen_models=self.chosen_models
        #find if a model was added
        new_set=model_idx-self.previous_selection
        if new_set:
            if len(new_set)>1:
                log = logging.getLogger(__name__)
                log.warning("WARNING: this shouldn't happen, model_idx changed by more than one")
            new_name=self.model_list.get(new_set.pop())
            chosen_models.add(new_name)
            if self.command is not None:
                self.command('add',new_name)
            #print "%s added"%(new_name)
        #find if a model was removed
        removed_set=self.previous_selection-model_idx
        if removed_set:
            if len(removed_set)>1:
                log.warning("WARNING: this shouldn't happen, model_idx changed by more than one")
            remove_name=self.model_list.get(removed_set.pop())
            chosen_models.remove(remove_name)
            if self.command is not None:
                self.command('remove',remove_name)
            #print "%s removed"%(remove_name)
        self.previous_selection=set(self.model_list.curselection())
    def changeSubj(self,newSubj):
        """Change the subject to which the structures list makes reference"""
        new_models=set(self.reader.get('model',newSubj,index='t'))
        unavailable_models=self.chosen_models-new_models
        available_models=self.chosen_models.intersection(new_models)
        if self.command is not None:
            for m in unavailable_models:
                self.command('remove',m)
            for m in available_models:
                self.command('add',m)
        self.model_list.select_clear(0,tk.END)
        self.tk_listvariable.set(tuple(sorted(new_models)))
        for m in available_models:
            index=self.listVariable().index(m)
            self.model_list.selection_set(index)
        self.previous_selection=set(self.model_list.curselection())
        
        
    def config(self,**kw):
        """Intercepts state kw and passes it to the listbox widget, other argument are passed directly to the tkFrame"""
        if kw.has_key('state'):
            new_state=kw.pop('state')
            self.model_list.config(state=new_state)
        LabelFrame.config(self, **kw)
    def configure(self,**kw):
        """Alias to config"""
        self.config(**kw)
    def listVariable(self):
        """Gets a tuple representation of the items in the list"""
        return ast.literal_eval(self.tk_listvariable.get())
    def get(self):
        """Get a list of currently selected items"""
        select_idx=self.model_list.curselection()
        return [self.model_list.get(i) for i in select_idx]
    def __get_tooltip(self,event=None):
        """returns a string containing the name under the event, and the cool name if available"""
        #print dir(event)
        y_coord=event.y
        index=self.model_list.nearest(y_coord)
        name=self.model_list.get(index)
        cool_name=self.cool_names.get(name,'')
        return "%s : %s " %(name,cool_name)

def hierarchy_dict_to_tree(tree_view,hierarchy_dict,root='',tags=tuple(),tooltip_dict=None,tooltip_source=None,default_message=''):
    """
    Reads from a hierarchy dictionary and adds the hierarchy to a tk tree view

    the id of the different nodes will contain the prefix root,
    a list of tags can also be added to the nodes
    if a tooltip_dict is provided, it will be used to associate tootips to the nodes looking in tooltip_source
    This is, the resulting message for the tooltip will be tooltip_source[tooltip_dict[key]] where key is the element in
    the hierarchy_dict. If tooltip_source does not contain dict, the default message will be used instead
    """

    for name,childs in sorted(hierarchy_dict.items(),key=lambda x:x[0]):
        tags2=tags[:]
        if len(childs)>0:
            tags2.append('parent')
        else:
            tags2.append('leaf')
        iid=':'.join((root,name))
        iid=iid.replace(' ','_')
        tree_view.insert(root, 'end', iid, text=name, tags=tags2)
        if tooltip_dict is not None:
            tooltip_dict[iid]=tooltip_source.get(name,default_message)
        if len(childs)>0:
            if tooltip_source is None:
                hierarchy_dict_to_tree(tree_view,childs,iid,tags,tooltip_dict,tooltip_source,'')
            else:
                hierarchy_dict_to_tree(tree_view,childs,iid,tags,tooltip_dict,tooltip_source,tooltip_source.get(name,''))

