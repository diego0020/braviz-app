from __future__ import division
import braviz
import os
from braviz.readAndFilter.read_csv import get_column,get_headers

from braviz.visualization.radar_chart import radar_factory

import matplotlib.pyplot as plt
import random
reader = braviz.readAndFilter.kmc40AutoReader(max_cache=100)
csv_file = os.path.join(reader.getDataRoot(), 'baseFinal_TMS.csv')

N=9
theta = radar_factory(N, frame='polygon')
headers=get_headers(csv_file)
headers=headers[4:N+4]
fig = plt.figure(figsize=(9, 9))

#data=[random.random()*0.7 for i in range(N-1)]+[5.0]
#data=[random.random()*0.7 for i in range(N)]
data=[22	,10	,153	,114	,17	,12	,22	,28	,65	,56	,13.7	,13.7	,100	,100]
#data=[0.88, 0.01, 0.03, 0.03, 0.00, 0.06, 0.01, 0.00, 0.00]
data2=data[:N]
colors=['r']
ax=fig.add_subplot(111,projection='radar')
#plt.rgrids([0.2, 0.4, 0.6, 0.8])
plt.rgrids(range(20,120,20))
ax.set_title('Radar', weight='bold', size='medium', position=(0.5, 1.1),
             horizontalalignment='center', verticalalignment='center')
ax.plot(theta,data2,color='r')
ax.fill(theta, data2, facecolor='r', alpha=0.25)
ax.set_rmax(120.0)
ax.set_varlabels(headers)
ax.set_rmin(0.0)
plt.show()