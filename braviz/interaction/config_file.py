"""A class and methods for manipulating a configuration file"""

import os
from ConfigParser import RawConfigParser
import logging

import vtk


__author__ = 'Diego'

class braviz_config(RawConfigParser):
    """A configuration file parser with functions to get braviz specific parameters"""
    def get_background(self):
        """returns a floats list with the background color specified in the configuration file"""
        back_string=self.get('VTK','background')
        back_list=back_string.split(' ')
        back_nums=map(float,back_list)
        return tuple(back_nums)
    def get_interaction_style(self):
        """Checks if the intraction style is a valid vtk interaction style and returns vtk name"""
        vtk_attrs=dir(vtk)
        upper_vtk_attrs=map(lambda x:x.upper(),vtk_attrs)
        custom_interactor_style=self.get('VTK','interaction_style')
        interaction_style='vtkInteractorStyle%s'%custom_interactor_style
        try:
            idx=upper_vtk_attrs.index(interaction_style.upper())
        except ValueError:
            log = logging.getLogger(__name__)
            log.error('Erroneous interactor_style value %s'%custom_interactor_style)
            raise Exception('Erroneous interactor_style value %s'%custom_interactor_style)
        style=vtk_attrs[idx]
        return style

def get_config(custom_dir=None):
    """A default configuration file is read at the library directory. A secondary configuration file can be set in the custom directory.
    For convenience a file can alse be passed as custom_dir, and the directory containing it will be taken"""
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    default_config_name=os.path.join(config_dir,config_file_name)
    config_files=[default_config_name]
    if custom_dir is not None:
        if os.path.isfile(custom_dir):
            custom_dir = os.path.dirname(custom_dir)
        custom_dir=os.path.realpath(custom_dir)
        full_config_name=os.path.join(custom_dir,config_file_name)
        if not os.path.isfile(full_config_name):
            make_default_config(full_config_name)
        else:
            config_files.append(full_config_name)
        #print config_files
    braviz_conf=braviz_config()
    braviz_conf.read(config_files)
    return braviz_conf

def make_default_config(default_config_name=None):
    """Creates a configuration file with defailt parameters and stores it as 'braviz.cfg'"""
    if default_config_name is None:
        config_dir=os.path.dirname(os.path.realpath(__file__))
        config_file_name='braviz.cfg'
        default_config_name=os.path.join(config_dir,config_file_name)
    braviz_conf=braviz_config()

    braviz_conf.add_section('Braviz')
    braviz_conf.set('Braviz','project','kmc400')

    braviz_conf.add_section("Default_Variables")
    braviz_conf.set('Default_Variables','nominal1','ubicac')
    braviz_conf.set('Default_Variables','nominal2','sexo5')
    braviz_conf.set('Default_Variables','numeric1','FSIQ')
    braviz_conf.set('Default_Variables','numeric2','peso5')

    braviz_conf.add_section('VTK')
    braviz_conf.set('VTK','Background','0.1 0.1 0.2')
    braviz_conf.set('VTK','Interaction_Style','TrackballCamera')

    log = logging.getLogger(__name__)
    try:
        with open(default_config_name,'w') as config_file:
            braviz_conf.write(config_file)

        log.info("default configuration file created in %s"%default_config_name)
    except IOError:
        log.error("couldn't create default configuration file in %s"%default_config_name)

    return braviz_conf

if __name__ == "__main__":
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    default_config_name=os.path.join(config_dir,config_file_name)
    make_default_config(default_config_name)
    config_dir=os.path.join(config_dir,"..","applications")
    default_config_name=os.path.join(config_dir,config_file_name)
    make_default_config(default_config_name)