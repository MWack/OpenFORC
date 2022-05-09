__author__ = 'wack'

# Simple FORC plotter, convolution based
# written by Michael Wack 2014-2017
# patched for Python 3.9 2022
# under development

import io
import timeit
import sys

# import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage, interpolate
from scipy.interpolate import griddata

# import scipy

'''
def fitPolySurface( x, y, z):
    v = np.array([np.ones(len(x)), x, y, x**2, y**2, x*y])


    # workaround for numpy nan bug
    idx = ~np.isnan(z)

    if ~np.any(idx):
        #print("all nan, not fitting")
        return [0, 0, 0, 0, 0, 0], 0, 0, 0
    else:
        #print(np.squeeze(v[:,idx].T, axis=1))
        #print(idx)
        #print(v[:,idx].shape)
        return np.linalg.lstsq(v[:,idx].T, z[idx])

    # numpy bug for nan values
    #return np.linalg.lstsq(v.T, z)
'''


def FastImportFORCData(filename, dialect='micromag'):
    f = open(filename)

    hys_df = None
    msi_df = None

    inc_hysloop = False
    inc_msi = False

    if dialect == 'micromag':
        # important to check if those are declared in the header
        # in this case those must be treated/removed before the forc data

        cl = 0  # current line number

        for line in f:
            cl += 1  # increase current line number count
            if "".join(line.split()).startswith('Includeshysteresisloop?Yes'):
                inc_hysloop = True
                print('hysteresis loop declared in header line {}'.format(cl))
            elif "".join(line.split()).startswith('IncludesMsi(H)?Yes'):
                inc_msi = True
                print('msi branch declared in header line {}'.format(cl))
            elif "".join(line.split()).startswith(
                    'FieldMoment'):  # this marks beginning of data for Munich files (new micromag format?)
                print('data header (new format) detected in line {}'.format(cl))
                break  # we are done with header lines
            elif "".join(line.split()).startswith(
                    'NData'):  # this is end of header resp. beginning of data for forcopedia fiels (old micromag format?)
                print('data header (old format) detected in line {}'.format(cl))
                break  # we are done with header lines

    # elif dialect=='vftb':
    #    # just skip 34 lines
    #    for i in range(34):
    #        f.readline()
    else:
        raise Exception("unknown dialect")

    # start reading data into pandas data frame
    # chunks of data separated by blank lines
    # skip 1st and last 2 lines from file
    fdf = pd.read_csv(io.StringIO("".join(f.readlines()[1:-2])), skip_blank_lines=False, header=None,
                      names=['Field', 'Moment'],
                      dtype=float, index_col=False)
    f.close()  # done with reading from file

    fdf["segment"] = fdf.isnull().all(axis=1).cumsum()  # label chunks separated by NAN = empty line
    fdf = fdf.dropna()  # remove empty lines

    if inc_hysloop:  # if hysteresis loop is included in data set
        # -> throw away first drift chunk (chunk_no == 0) and move the next two (chunk_no == 1 & 2) to hysteresis_df
        hys_df = fdf[fdf.segment.isin([1, 2])]  # copy upfield and downfield hysteresis segment to hys_df
        fdf = fdf[fdf.segment >= 3]  # drop first three segments (Ms & hysteresis up and downfield)

    if inc_msi:
        msi_df = fdf[fdf.segment == fdf.segment.min() + 1]  # copy msi segment to hys_df
        fdf = fdf[fdf.segment > fdf.segment.min() + 1]  # drop msi segment from forc data

    # forc data fdf consists of alternating single Ms (drift) values and forc curves as segments
    # print(fdf)

    # separate forc and Ms data
    drift_df = fdf[fdf.segment.isin(
        range(fdf.segment.min(), fdf.segment.max(), 2))].copy()  # get every second segment as drift data
    forc_df = fdf[fdf.segment.isin(
        range(fdf.segment.min() + 1, fdf.segment.max(), 2))].copy()  # get every other segment as forc curve

    forc_df.rename(columns={'Field': 'Hb'}, inplace=True)  # rename column "Field" to "Hb"

    # also return hysteresis and msi?
    return drift_df, forc_df


def DriftCorrection(forc_df, drift_df, polyorder=6):
    """ Do drift correction of forc data based on drift data """

    # add segment steps needed for drift correction
    forcs = forc_df.groupby('segment')

    def SegStep(group):
        group['segstep'] = np.linspace(group['segment'].iloc[0], group['segment'].iloc[0] + 2, num=len(group),
                                       endpoint=False)
        return group

    forc_df = forcs.apply(SegStep)  # add decimal segment steps for each point - needed for drift correction

    # lets look at the drift data
    y = drift_df['Moment']
    x = drift_df['segment']  # segment numbers
    driftpoly = np.poly1d(np.polyfit(x, y, polyorder))  # fit polynomial to the data

    plt.plot(x, y, 'r.')
    p = plt.plot(x, driftpoly(x), 'g-')

    # apply drift correction
    # (see Variforc, Egli 2013, eq 23)
    forc_df['Moment'] *= driftpoly(1) / driftpoly(forc_df['segstep'])

    # return plot
    return forc_df


def PrepareForcData(forc_df, mirror=True):
    # add column Ha (first Hb of each FORC)
    def Ha(group):
        group['Ha'] = group['Hb'].iloc[0]
        return group

    forcs = forc_df.groupby('segment')
    forc_df = forcs.apply(Ha)  # adding Ha slow!

    forcs = forc_df.groupby('segment')

    if mirror:  # mirror each FORC curve # mirroring slow
        def mirror_forc(group):
            mirrored_group = group.copy()  # do not mirror first point since identical
            mirrored_group['segment'] = -group['segment']
            mirrored_group['Hb'] = 2 * group['Ha'] - group['Hb']  # could be done on whole data frame -> faster?
            mirrored_group['Moment'] = 2 * group['Moment'].iloc[0] - group['Moment']
            return pd.concat([mirrored_group.iloc[:0:-1], group])

        forc_df = forcs.apply(mirror_forc)

    # Halen is number of groups
    Halen = len(forcs)
    # Hblen is maximum length of a group
    Hblen = forcs.size().max()

    forc_df.reset_index(drop=True, inplace=True)

    return forc_df, Halen, Hblen


def PlotForcCurves(forc_df):
    # plot for testing
    for key, grp in forc_df.groupby('segment'):
        plt.plot(grp['Hb'], grp['Moment'], label="FORC {}".format(key))
    plt.show()


def FastTranslateHaHbHcHu(HaHbdata):
    ''' translate from Ha,Hb coordinates into common Hu,Hc coordinates'''
    # Hu = (Ha+Hb) / 2
    # Hc = (Hb-Ha) / 2
    return np.array([(HaHbdata[:, 1] - HaHbdata[:, 0]) / 2, (HaHbdata[:, 0] + HaHbdata[:, 1]) / 2, HaHbdata[:, 2]]).T


if __name__ == '__main__':  # test routine
    np.set_printoptions(threshold=sys.maxsize)
    dialect = 'micromag'
    fname = '../data/FeNi100-A-a-24-M001_005.forc'
    # fname = '../data/FeNi0_heated.forc'  # big ~70k points
    # fname = '../data/140401-Gd2O3_2.forc'
    # fname = "../data/forcopedia/1256D-4R-2-062-25mg-250c.frc"
    # fname = "../data/forcopedia/1256D-49R-2-099b.frc"
    # fname = "../data/forcopedia/Bjurbole-L1i3-grad0.1.frc"
    # fname = "../data/forcopedia/Karoonda-10d.frc"
    # fname = '../data/vftb_forc.frc'#; dialect = 'vftb'  # first vftb forc
    # fname = '../data/vftb_full_forc.frc'

    initial_time = timeit.default_timer()

    start_time = timeit.default_timer()
    print("starting data import from {} at {}s".format(fname, start_time - initial_time))
    dd, fd = FastImportFORCData(fname, dialect=dialect)
    print("Seconds for importFORCdata: {}".format(timeit.default_timer() - start_time))
    print("Number of datapoints: {}".format(len(fd)))

    # fd = DriftCorrection(fd, dd) # do drift correction
    fd, Halen, Hblen = PrepareForcData(fd, mirror=True)  # add Ha column, pot. mirror data
    PlotForcCurves(fd)

    fd = np.array(fd[['Ha', 'Hb', 'Moment']])

    # print( fd)

    # plot raw forc data M( Ha, Hb)
    x = fd[:, 1]  # Hb
    y = fd[:, 0]  # Ha
    z = fd[:, 2]
    # define grid

    minHa, maxHa = min(y), max(y)
    minHb, maxHb = min(x), max(x)

    # print(x,y,z)
    print(minHa, maxHa)
    print(minHb, maxHb)

    xi = np.linspace(minHb, maxHb, Hblen)
    yi = np.linspace(minHa, maxHa, Halen)
    # grid the data
    # zi = griddata(x,y,z,xi,yi,interp='linear')  # linearly interpolate values to regular grid

    f = interpolate.LinearNDInterpolator(fd[:, [1, 0]], z, fill_value=np.nan)  # bilinear
    # f = interpolate.NearestNDInterpolator(fd[:, [1, 0]], z)  # nearest neighborhood
    # f = interpolate.SmoothBivariateSpline( x, y, z, s=1, kx=3, ky=3)

    # f2 = interpolate.interp2d( x, y, z, kind='linear', fill_value = np.nan)
    # zi = f2(xi, yi)

    mg_xn, mg_yn = np.meshgrid(xi, yi)
    zi = f(mg_xn, mg_yn)

    # print( 'finding bicubic spline representation...')
    # tck = interpolate.bisplrep(x, y, z, s=0, kx=3, ky=3)  # bicubic splines
    # print('interpolating spline to grid')
    # zi = interpolate.bisplev(mg_xn[:,0], mg_yn[0,:], tck)  # gives always zero!?

    # xi, yi, zi are regular gridded forc values

    # contour the gridded data
    start_time = timeit.default_timer()
    print("starting plotting figure 1 at {}s ....".format(start_time - initial_time))
    plt.contourf(xi, yi, zi, 50, cmap=plt.cm.get_cmap("jet"))

    # plt.imshow( zi, origin='lower', extent=(minHb, maxHb, minHa, maxHa), cmap='jet')
    plt.colorbar()  # draw colorbar
    plt.xlabel('Hb')
    plt.ylabel('Ha')
    plt.title('FORC raw data (magnetic moments)')
    plt.axis('equal')

    # now run convolution on regular gridded (interpolated) forc data
    # define a kernel for differentiation in xy
    # k = -np.array([[1, 0, -1],
    #              [0, 0, 0],
    #              [-1, 0, 1]])

    k = -np.array([[1, 2, 0, -2, -1],
                   [2, 4, 0, -4, -2],
                   [0, 0, 0, 0, 0],
                   [-2, -4, 0, 4, 2],
                   [-1, -2, 0, 2, 1]])

    k = k / np.absolute(k).sum()  # normalize k to get right scaling of output

    raw_forc = zi
    # print(raw_forc.shape)

    start_time = timeit.default_timer()
    print("starting data convolution at {}s ....".format(start_time - initial_time))
    conv_forc = ndimage.convolve(raw_forc, k, mode='reflect')
    print("Seconds for data convolution: {}".format(timeit.default_timer() - start_time))

    start_time = timeit.default_timer()
    print("starting plotting figure 2 at {}s ....".format(start_time - initial_time))
    plt.figure(2)
    # contour the gridded data
    plt.contourf(xi, yi, conv_forc, 50, cmap=plt.cm.get_cmap("jet"))
    # print(zi)
    # plt.imshow( zi, origin='lower', extent=(minHb, maxHb, minHa, maxHa), cmap='RdBu')
    plt.colorbar()  # draw colorbar
    plt.xlabel('Hb')
    plt.ylabel('Ha')
    plt.title('FORC processed')
    plt.axis('equal')

    xv, yv = np.meshgrid(xi, yi)

    print("starting TranslateHaHbHcHu....")
    start_time = timeit.default_timer()
    fittedFORCdata = FastTranslateHaHbHcHu(np.array([yv.flatten(), xv.flatten(), conv_forc.flatten()]).T)
    print("Seconds for TranslateHaHbHcHu: {}".format(timeit.default_timer() - start_time))
    #
    x, y, z = fittedFORCdata[:, 0], fittedFORCdata[:, 1], fittedFORCdata[:, 2]
    # # define grid
    #
    xi = np.linspace(0, max(x), Halen * 2)  # Hc space
    yi = np.linspace(min(y), max(y), Hblen * 2)  # Hu space

    # # grid the data
    start_time = timeit.default_timer()
    print("starting gridding data at {}s ....".format(start_time - initial_time))
    grid = np.meshgrid(xi, yi)
    # grid the data
    points = np.column_stack((x, y))
    zi = griddata(points, z, tuple(grid), method='linear', fill_value=np.nan)
    print(zi)
    print("done")

    start_time = timeit.default_timer()
    print("starting plotting figure 3 at {}s ....".format(start_time - initial_time))
    plt.figure(3)
    # # contour the gridded data
    cs = plt.contourf(xi, yi, zi, 50, cmap=plt.cm.get_cmap("jet"))
    plt.contour(cs, levels=cs.levels[::5], colors='black')  # add contour lines
    plt.axhline(0, color='black')
    # plt.imshow( zi, origin='lower', extent=(minHb, maxHb, minHa, maxHa), cmap='RdBu')
    plt.colorbar(cs)  # draw colorbar
    # # plot data points.
    plt.xlabel('Hc')
    plt.ylabel('Hu')
    # # show data points
    # #plt.scatter( x, y)
    plt.title('FORC processed (Hu,Hc)')
    plt.axis('equal')
    #
    # #plt.xlim( [0, 0.1])
    # #plt.ylim( [-0.1, 0.03])
    # #plt.savefig( fname + '.png')

    start_time = timeit.default_timer()
    print("finished after {}s total. showing plots.".format(start_time - initial_time))

    plt.show()
