__author__ = 'diego'

import ConfigParser
from itertools import izip

known_nodes_kmc40 = {  #
                 # Name          :  ( data root                   , cache size in MB)
                 'gambita.uniandes.edu.co': ('/media/DATAPART5/KAB-db', 4000),
                 'Unidelosandes': ('K:\\JohanaForero\\KAB-db', 1200),
                 'dieg8': (r'C:\Users\Diego\Documents\kmc40-db\KAB-db', 4000),
                 'TiberioHernande': (r'E:\KAB-db', 1100),
                 'localhost.localdomain': ('/home/diego/braviz/subjects', 1000),
                 'ISIS-EML725001': (r'C:\KAB-db', 8000),
                 'archi5': (r"/mnt/win/Users/Diego/Documents/kmc40-db/KAB-db", 4000),
                 'dellingr.vrac.iastate.edu': (r"/Volumes/diegoa/KAB-db", 14000),
                 'MacAirCyril-S.local': ("/Users/CS/Desktop/diego_data", 7000),
                 'ATHPC1304': (r"F:\ProyectoCanguro\KAB-db", 14000),
                 'IIND-EML754066': (r"C:\Users\da.angulo39\Documents\KAB-db", 2000),
                 'da-angulo': (r"D:\KAB-db", 4000),
                 'Echer': ('H:/KAB-db',8000),
                 'imagine-PC' : ("E:\\KAB-db",50000)
}

keys_kmc40=("Data Root","Memory (MB)")

known_nodes_kmc400 = {  #
    # Name          :  ( static data root, dyn data root , cache size in MB)
    'gambita.uniandes.edu.co': ('/media/DATAPART5/kmc400','/media/DATAPART5/kmc400_braviz', 4000),
    #'dieg8': (r'E:\kmc400',"E:/kmc400_braviz", 4000),
    'dieg8': (r'C:\Users\Diego\Documents\kmc400',r"C:\Users\Diego\Documents/kmc400_braviz", 4000),
    'archi5': ('/mnt/win/Users/Diego/Documents/kmc400',"/mnt/win/Users/Diego/Documents/kmc400_braviz", 4000),
    'ATHPC1304' : (r"Z:",r"F:\ProyectoCanguro\kmc400_braviz",14000),
    'IIND-EML754066' : (r"Z:",r"C:\Users\da.angulo39\Documents\kmc400_braviz",2000),
    #'da-angulo': ("Z:\\","D:\\kmc400-braviz" ,4000),
    'da-angulo': ("X:\\","D:\\kmc400-braviz" ,4000),
    #'da-angulo': ("F:\\kmc400","F:\kmc400_braviz" ,4000), # from external drive
    #'da-angulo': ("F:\\kmc400","D:\\kmc400-braviz" ,4000), # from external drive
    #'da-angulo': (r"N:\run\media\imagine\backups\kmc400","D:\\kmc400-braviz" ,4000), # from external drive
    'ISIS-EML725001': ('G:/kmc400', 'G:/kmc400-braviz',8000),
    'Echer': ('H:/kmc400', 'H:/kmc400-braviz',8000),
    'colivri1-homeip-net' : ('/home/canguro/kmc400-braviz','/media/external2/canguro_win/kmc_400_braviz',50000),
    'imagine-PC' : ("Z:\\","E:\\kmc_400_braviz",50000)
}

keys_kmc400=("Data Root","Dynamic Data Root","Memory (mb)")

def write_nodes_to_config_file(data_dict,keys,output):
    config = ConfigParser.RawConfigParser()
    nodes = sorted(data_dict.items(),key=lambda x:x[0].lower())
    for node,values in nodes:
        config.add_section(node)
        for k,v in izip(keys,values):
            config.set(node,k,v)
    with open(output,"w") as f:
        config.write(f)

write_nodes_to_config_file(known_nodes_kmc40,keys_kmc40,"/home/diego/kmc40_hosts.cfg")
write_nodes_to_config_file(known_nodes_kmc400,keys_kmc400,"/home/diego/kmc400_hosts.cfg")