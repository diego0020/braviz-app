from __future__ import division
import os
from itertools import ifilter

import matplotlib.pyplot as plt
import numpy as np

import braviz
from braviz.readAndFilter.read_csv import get_tuples_dict
from braviz.visualization.radar_chart import radar_factory


reader = braviz.readAndFilter.kmc40AutoReader(max_cache=100)
csv_file = os.path.join(reader.getDataRoot(), 'baseFinal_TMS.csv')
pow_wanted_cols = ('ICId', 'ICInd', 'ICFd', 'ICFnd', 'RMTd', 'RMTnd')
time_wanted_cols = ('IHIlatd', 'IHIlatnd', 'IHIdurd', 'IHIdurnd', 'MEPlatd', 'MEPlatnd')

data_rows = {
    'Times': time_wanted_cols,
    'Signal': pow_wanted_cols,
}
max_values = {
    'Times': 50,
    'Signal': 300,
}
fig = plt.figure(figsize=(9, 9))

colors = ['#E41A1C', '#377EB8', '#4DAF4A']
col_names = ['Canguro', 'Control', 'Gorditos']

ubica_dict = get_tuples_dict(csv_file, 'CODE', 'UBICA', numeric=True)

for row, (row_name, wanted_cols) in enumerate(data_rows.iteritems()):
#headers=get_headers(csv_file)
#headers=headers[4:N+4]

    N = len(wanted_cols)

    data_dict=get_tuples_dict(csv_file,'CODE',wanted_cols,numeric=True)
    #remove nans
    data_dict=dict((k,v) for k,v in data_dict.iteritems() if np.all(np.isfinite(v)))
    theta = radar_factory(N, frame='polygon')
    max_radius=max_values[row_name]
    for col,color in enumerate(colors):
        ax=fig.add_subplot(2,3,row*3+col+1,projection='radar')
        #plt.rgrids([0.2, 0.4, 0.6, 0.8])
        plt.rgrids(np.linspace(0,max_radius,5)[1:])
        ax.set_title(col_names[col], weight='bold', size='medium', position=(0.5, 1.1),
                     horizontalalignment='center', verticalalignment='center')
        for code,data2 in ifilter(lambda (x,y): ubica_dict[x]==col+1,data_dict.iteritems()):
            ax.plot(theta,data2,color=color)
            ax.fill(theta, data2, alpha=0.15,color=color)
        ax.set_rmax(max_radius)
        ax.set_varlabels(wanted_cols)
        ax.set_rmin(0.0)
plt.show()