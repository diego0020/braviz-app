# -*- coding: utf-8 -*-
"""
Created on Mon Nov 11 14:00:04 2013

@author: Diego
"""
ax=plt.subplot(111,polar=True)
patches=[[ 1.57079633 , 0.76593829],
 [ 2.35619449 , 0.82202037],
 [ 3.14159265 , 0.95949363],
 [ 3.92699082 , 0.15392178],
 [ 4.71238898 , 0.44369595],
 [ 5.49778714 , 0.37636878],
 [ 6.28318531 , 0.48210942],
 [ 7.06858347 , 0.44050311],
 [ 1.57079633 , 0.76593829]]

def get_r_function(patches):
    def r_function(theta):
        #patches are uniformly spaced:
        #1 find to which patch the angle belongs
        theta_moved=(theta-np.pi/2)
        if theta_moved<0:
            theta_moved+=2*np.pi
        #print theta_moved
        index=int(theta_moved//(2*np.pi/(len(patches)-1)))
        #print "%f in [%f , %f) "%(theta,patches[index][0],patches[index+1][0])
        t1,r1=patches[index]
        t2,r2=patches[index+1]
        x1=r1*np.cos(t1)
        x2=r2*np.cos(t2)
        y1=r1*np.sin(t1)
        y2=r2*np.sin(t2)
        m=(y2-y1)/(x2-x1)
        q=y1-x1*m
        g=np.arctan(m)
        r3=(q/np.sqrt(1+m**2))/np.sin(theta-g)
        return np.abs(r3)
    return r_function
r_function=get_r_function(patches)

t5=np.linspace(0,2*pi,501)
r5=map(r_function,t5)
ax.set_rmax(1.0)
plot(t5,r5)
ax.set_rmax(1.0)
plt.show()

#profiling
#%%timeit 
#t=random.random()*np.pi*2
#r=r_function(t)
#
#10000 loops, best of 3: 29.3 us per loop

def get_r_function(patches):
    func_dir={}
    for i in range(len(patches)-1):
        def aux(theta):
            t1,r1=patches[i]
            t2,r2=patches[i+1]
            x1=r1*np.cos(t1)
            x2=r2*np.cos(t2)
            y1=r1*np.sin(t1)
            y2=r2*np.sin(t2)
            m=(y2-y1)/(x2-x1)
            q=y1-x1*m
            g=np.arctan(m)
            r3=(q/np.sqrt(1+m**2))/np.sin(theta-g)
            return np.abs(r3)
        func_dir[i]=aux
    def r_function(theta):
        #patches are uniformly spaced:
        #1 find to which patch the angle belongs
        theta_moved=(theta-np.pi/2)
        if theta_moved<0:
            theta_moved+=2*np.pi
        #print theta_moved
        index=int(theta_moved//(2*np.pi/(len(patches)-1)))
        #print "%f in [%f , %f) "%(theta,patches[index][0],patches[index+1][0])
        return func_dir[index](theta)
    return r_function
r_function=get_r_function(patches)

#%%timeit 
#t=random.random()*np.pi*2
#r=r_function(t)
#10000 loops, best of 3: 30.8 us per loop

def get_r_function(patches):
    def aux(theta,p1,p2):
        t1,r1=p1
        t2,r2=p2
        x1=r1*np.cos(t1)
        x2=r2*np.cos(t2)
        y1=r1*np.sin(t1)
        y2=r2*np.sin(t2)
        m=(y2-y1)/(x2-x1)
        q=y1-x1*m
        g=np.arctan(m)
        r3=(q/np.sqrt(1+m**2))/np.sin(theta-g)
        return np.abs(r3)
    def r_function(theta):
        #patches are uniformly spaced:
        #1 find to which patch the angle belongs
        theta_moved=(theta-np.pi/2)
        if theta_moved<0:
            theta_moved+=2*np.pi
        #print theta_moved
        index=int(theta_moved//(2*np.pi/(len(patches)-1)))
        #print "%f in [%f , %f) "%(theta,patches[index][0],patches[index+1][0])
        return aux(theta,patches[index],patches[index+1])
    return r_function
r_function=get_r_function(patches)