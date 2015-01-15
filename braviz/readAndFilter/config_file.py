
"""Contains a class for accessing Braviz configuration from configuration files and functions to access such files"""

import os
from ConfigParser import RawConfigParser
import logging

import vtk


__author__ = 'Diego'

class BravizConfig(RawConfigParser):
    """Holds Braviz configuration"""
    def get_background(self):
        """Background color from a configuration file

        .. deprecated:: 3.0b
           Use a gray or degraded gray background

        Returns:
            RGB value as a float tuple
        """
        back_string=self.get('VTK','background')
        back_list=back_string.split(' ')
        back_nums=map(float,back_list)
        return tuple(back_nums)
    def get_interaction_style(self):
        """Interaction style from a configuration file

        .. deprecated:: 3.0b
           Use TrackballCamera

        Checks if the intraction style is a valid vtk interaction style and returns vtk name

        Returns:
            vtkInteractorStyle class
        """
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
    def get_default_variables(self):
        """
        Default variables from configuration file

        Returns:
            A dictionary containing the default variables. The keys are
            ``{"nom1","nom2","ratio1","ratio2","lat"}``
        """
        nom1=self.get('Default_Variables','nominal1')
        nom2=self.get('Default_Variables','nominal2')
        ratio1=self.get('Default_Variables','numeric1')
        ratio2=self.get('Default_Variables','numeric2')
        lat=self.get('Default_Variables','laterality')

        return {"nom1":nom1,"nom2":nom2,"ratio1":ratio1,"ratio2":ratio2,"lat":lat}

    def get_laterality(self):
        """
        Laterality from configuration file

        Returns:
            A tuple ``(lat, left)`` where *lat* is the name of the nominal variable containing laterality information
             and *left* is the label (integer) this variable takes for left-handed subjects.

        """
        lat = self.get('Default_Variables','laterality')
        left = self.getint('Default_Variables','left_handed_label')
        return lat,left

    def get_default_subject(self):
        """
        Default subject from configuration file

        Returns:
            An integer containing the code for the chosen default subject
        """
        return self.getint('Defaults','default_subject')

    def get_reference_population(self):
        """
        Reference population from configuration file

        Returns:
            A tuple ``(var,label)`` where *var* is the name of the nominal variable that separates the reference population
            and *label* is the integer value this variable takes for the reference population
        """
        var = self.get('Default_Variables','reference_pop_var')
        label = self.getint('Default_Variables','reference_pop_label')
        return var,label

    def get_project_name(self):
        return self.get("Braviz","project")


def get_apps_config():
    """
    Reads configuration from the 'braviz.applications' directory

    Returns:
        An instance of :class:`BravizConfig`
    """
    apps_dir = os.path.join(os.path.dirname(__file__),"..","applications")
    return get_config(apps_dir)

def get_config(custom_dir=None):
    """
    Read Braviz configuration file

    A default configuration file is read at the library directory. A secondary configuration can also be read,
    and in this case its values will overwrite default ones.

    Args:
        custom_dir (str) : Location of a secondary configuration file.
            For convenience a file can also be passed and the directory containing it will be used

    Returns:
        An instance of :class:`BravizConfig`
    """
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
    braviz_conf=BravizConfig()
    braviz_conf.read(config_files)
    return braviz_conf

def make_default_config(default_config_name=None):
    """Creates a configuration file with default parameters and stores it

    Args:
        default_config_name (str) : Name used to store the default configuration,
            if ``None`` it stored as `braviz.cfg` in the directory containing this library
    """
    if default_config_name is None:
        config_dir=os.path.dirname(os.path.realpath(__file__))
        config_file_name='braviz.cfg'
        default_config_name=os.path.join(config_dir,config_file_name)
    braviz_conf=BravizConfig()

    braviz_conf.add_section('Braviz')
    braviz_conf.set('Braviz', 'project', 'kmc400')
    braviz_conf.set('Braviz', 'logger', 'console')

    braviz_conf.add_section("Default_Variables")
    braviz_conf.set('Default_Variables','nominal1','ubicac')
    braviz_conf.set('Default_Variables','nominal2','BIRTH_sexo5')
    braviz_conf.set('Default_Variables','numeric1','WASI_FSIQ_4')
    braviz_conf.set('Default_Variables','numeric2','BIRTH_peso5')
    braviz_conf.set('Default_Variables','laterality','LAT_EdinburgHandedness')
    braviz_conf.set('Default_Variables','left_handed_label',3)
    braviz_conf.set('Default_Variables','reference_pop_var','ubicac')
    braviz_conf.set('Default_Variables','reference_pop_label',3)

    braviz_conf.add_section("Defaults")
    braviz_conf.set('Defaults','default_subject',119)

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

def get_host_config(project,hostname=None):
    """
    Reads host configuration for a given project

    Args:
        project (str) : The name of the project. This function will look for a file called ``<project>_hosts.cfg``
            in the directory containing the module :mod:`braviz.applications`
        hostname (str) : Name of host to get configuration. If ``None`` the name of the current host,
            as returned by :func:`platform.node` will be used

    Returns:
        A dictionary containing the requested configuration parameters.
    """
    if hostname is None:
        import platform
        hostname = platform.node()
    config = RawConfigParser()
    file_name = os.path.join(os.path.dirname(__file__),"..","applications","%s_hosts.cfg"%project)
    config.read(file_name)
    if not config.has_section(hostname):
        apps_dir=os.path.normpath(os.path.dirname(file_name))
        raise KeyError("Unknown host %s\nPlease modify the %s_hosts.cfg file in %s" % (hostname,project,apps_dir ))
    items = dict(config.items(hostname))
    return items

if __name__ == "__main__":
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    default_config_name=os.path.join(config_dir,config_file_name)
    make_default_config(default_config_name)
    config_dir=os.path.join(config_dir,"..","applications")
    default_config_name=os.path.join(config_dir,config_file_name)
    make_default_config(default_config_name)