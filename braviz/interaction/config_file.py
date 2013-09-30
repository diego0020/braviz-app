import os
from ConfigParser import RawConfigParser
__author__ = 'Diego'

class braviz_config(RawConfigParser):
    def get_background(self):
        back_string=self.get('VTK','background')
        back_list=back_string.split(' ')
        back_nums=map(float,back_list)
        return tuple(back_nums)


def get_config():
    config_dir=os.path.dirname(os.path.realpath(__file__))
    config_file_name='braviz.cfg'
    full_config_name=os.path.join(config_dir,'..', '..','applications',config_file_name)
    braviz_conf=braviz_config()
    braviz_conf.read(full_config_name)
    return braviz_conf

