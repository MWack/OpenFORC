import plotly.graph_objects as go
from js import document
import numpy as np
from numpy import sin, cos, pi
from scipy.spatial.transform import Rotation as R
import munmagtools.anisotropy.tensorfit as tf

print("tensor_plotly_ellipsoid.py started")

# global variables needed:
# * tensor: dict with tensor data
# * dirs: reference directions as D,I and corresponding measrurements
# * matrix_type: scalar or vectorial


phi = np.linspace(0, 2*pi, num=25)
theta = np.linspace(-pi/2, pi/2, num=25)
phi, theta = np.meshgrid(phi, theta)

# need to get eigenvalues and eigenvectors in their original order
s = tensor['s']
T = np.array([[s[0], s[3], s[5]], [s[3], s[1], s[4]], [s[5], s[4], s[2]]])
evals, evecs = np.linalg.eig(T)

# scale sphere with eigenvalues
x = cos(theta) * sin(phi) * evals[0]
y = cos(theta) * cos(phi) * evals[1]
z = sin(theta) * evals[2]

xyz = np.array([x.ravel(), y.ravel(), z.ravel()])

# rotate ellipsoid meshgrid according to eigenvectors
xyzrot = np.dot(evecs, xyz)

# return to original shape of meshgrid
xrot = xyzrot[0].reshape(x.shape)
yrot = xyzrot[1].reshape(y.shape)
zrot = xyzrot[2].reshape(z.shape)

fig = go.Figure(data=[go.Surface(x=xrot, y=yrot, z=zrot, surfacecolor=xrot**2 + yrot**2 + zrot**2, opacity=.5)])

# add some lines for reference
# eigenvectors
colors = ['red', 'green', 'blue']
for c in range(3):
    xx, yy, zz = tensor['eigvecs'][c] * tensor['eigvals'][c] * 1.15 # eigenvector scaled to stick out of the ellipsoid
    fig.add_scatter3d(x=[xx,-xx], y=[yy,-yy], z=[zz,-zz], mode='lines', line_width=6, line_color=colors[c], name=f"eigenvector {c+1}")
# reference directions
for refxyz in [tf.DIL2XYZ([e["D"],e["I"],1]) for e in dirs.to_py().values()]:
    xx, yy, zz = refxyz / np.linalg.norm(refxyz) * 1.15 # reference directions scaled to stick out of the ellipsoid
    fig.add_scatter3d(x=[xx,0], y=[yy,0], z=[zz,0], mode='lines', line_width=3, line_color="black", name="reference")
# measurements as points
if matrix_type=='v':
    # original measurements
	meas_xyz = np.array([[e["x"],e["y"],e["z"]] for e in dirs.to_py().values()])
else:
    # calculate projected points on reference directions
    meas_xyz = np.array([np.array(tf.DIL2XYZ([e["D"],e["I"],1])) * e["s"] for e in dirs.to_py().values()])
# plot measurement points
fig.add_scatter3d(x=meas_xyz[:, 0], y=meas_xyz[:, 1], z=meas_xyz[:, 2], mode='markers',
        marker=dict(size=3, color="black", opacity=0.8), name="measurements")


# get max and min ellipsoid values for scaling
erange = [np.amax( xyzrot), np.amin(  xyzrot)]
# get max and min measurement values for scaling
mrange = [np.amax( meas_xyz), np.amin(  meas_xyz)]

# get total range to comprise ellipsoid and measurements
drange = [max( [erange[0], mrange[0]]), min( [erange[1], mrange[1]])]


fig.update_layout(
    #coloraxis_colorbar=dict(orientation="h"), # doesn't work
    legend_orientation="h",
    scene = dict(
        xaxis = dict(range=drange,),
        yaxis = dict(range=drange,),
        zaxis = dict(range=drange,),),
        width=500,
        title='Anisotropy ellipsoid',
        margin=dict(r=20, l=10, b=10, t=10))
		
# fig.update_coloraxes(colorbar=dict(orientation="h")) # doesn't work

ps = f"var graphs = {fig.to_json()};\n" + "Plotly.plot('plot',graphs,{});\n"

print("tensor_plotly_ellipsoid.py finished")
