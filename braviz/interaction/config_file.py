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

def get_config(custom_dir=None):
    """A default configuration file is read at the library directory. A secondary configuration file can be set in the custom directory.
    For convenience a file can alse be passed as custom_dir, and the directory containing it will be taken"""
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    default_config_name=os.path.join(config_dir,config_file_name)
    config_files=[default_config_name]
    if custom_dir is not None:
        custom_dir=os.path.realpath(custom_dir)
        full_config_name=os.path.join(custom_dir,config_file_name)
        config_files.append(full_config_name)
        full_config_name=os.path.join(os.path.dirname(custom_dir),config_file_name)
        config_files.append(full_config_name)
        #print config_files
    braviz_conf=braviz_config()
    braviz_conf.read(config_files)
    return braviz_conf

def make_default_config():
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    default_config_name=os.path.join(config_dir,config_file_name)
    braviz_conf=braviz_config()
    braviz_conf.add_section('VTK')
    braviz_conf.set('VTK','Background','0.1 0.1 0.2')
    braviz_conf.set('VTK','Interaction_Style','TrackballCamera')
    try:
        config_file=open(default_config_name,'w')
        braviz_conf.write(config_file)
        config_file.close()
        print "default configuration file created in %s"%default_config_name
    except:
        print "couldn't create default configuration file in %s"%default_config_name


    return braviz_conf

