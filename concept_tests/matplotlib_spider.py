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
headers=headers[4:N]
fig = plt.figure(figsize=(9, 9))

data=[random.randint(40,50) for i in range(N)]
data=[0.4, 0.01, 0.08, 0.00, 0.00, 0.04, 0.00, 0.00, 0.01]
colors=['r']
ax=fig.add_subplot(111,projection='radar')
plt.rgrids([0.2, 0.4, 0.6, 0.8])
ax.set_title('Radar', weight='bold', size='medium', position=(0.5, 1.1),
             horizontalalignment='center', verticalalignment='center')
ax.plot(theta,data,color='r')
ax.fill(theta, data, facecolor='r', alpha=0.25)
#ax.set_varlabels(headers)

plt.show()