import os
import vtk
from ConfigParser import RawConfigParser
__author__ = 'Diego'

class braviz_config(RawConfigParser):
    def get_background(self):
        back_string=self.get('VTK','background')
        back_list=back_string.split(' ')
        back_nums=map(float,back_list)
        return tuple(back_nums)
    def get_interaction_style(self):
        vtk_attrs=dir(vtk)
        upper_vtk_attrs=map(lambda x:x.upper(),vtk_attrs)
        custom_interactor_style=self.get('VTK','interaction_style')
        interaction_style='vtkInteractorStyle%s'%custom_interactor_style
        try:
            idx=upper_vtk_attrs.index(interaction_style.upper())
        except ValueError:
            print 'Erroneous interactor_style value %s'%custom_interactor_style
            raise Exception('Erroneous interactor_style value %s'%custom_interactor_style)
        style=vtk_attrs[idx]
        return style

def get_config():
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    default_config_name=os.path.join(config_dir,config_file_name)
    full_config_name=os.path.join(config_dir,'..', '..','applications',config_file_name)
    braviz_conf=braviz_config()
    braviz_conf.read([default_config_name,full_config_name])
    return braviz_conf

