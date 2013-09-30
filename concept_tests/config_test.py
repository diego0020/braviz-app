import os
import ConfigParser

__author__ = 'Diego'

config_dir=os.path.dirname(os.path.realpath(__file__))
config_file_name='braviz.cfg'
full_config_name=os.path.join(config_dir,'..', 'applications',config_file_name)
print full_config_name

braviz_conf=ConfigParser.RawConfigParser()
braviz_conf.add_section('VTK')
braviz_conf.set('VTK','Background','0.1 0.1 0.2')
braviz_conf.set('VTK','Interaction_Style','TrackballCamera')

config_file=open(full_config_name,'w')
braviz_conf.write(config_file)
config_file.close()