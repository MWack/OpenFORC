__author__ = 'wack'

# Simple FORC plotter
# written by Michael Wack 2014
# patched for Python 3.9 in 2022
# under development

import sys
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import griddata


def fitPolySurface(x, y, z):
    v = np.array([np.ones(len(x)), x, y, x ** 2, y ** 2, x * y])

    # workaround for numpy nan bug
    idx = ~np.isnan(z)

    if ~np.any(idx):
        # print("all nan, not fitting")
        return [0, 0, 0, 0, 0, 0], 0, 0, 0
    else:
        # print(np.squeeze(v[:,idx].T, axis=1))
        # print(idx)
        # print(v[:,idx].shape)
        return np.linalg.lstsq(v[:, idx].T, z[idx], rcond=None)

    # numpy bug for nan values
    # return np.linalg.lstsq(v.T, z)


def importFORCdata(filename, reflect=True, skipchunks=0):
    # file format
    # long header
    # comma separated values: applied field, magnetic moment, (temperature)
    # alternating data chunks of drift field and FORC curves

    def readMicroMagHeader(lines):
        sectionstart = False
        sectiontitle = None
        sectioncount = 0
        header = {}
        # section header: CAPITALS, no spaces
        lc = 0
        for l in lines:
            lc += 1
            sl = l.strip()  # take away any leading and trailing whitespaces
            if lc == 1 and not sl.startswith("MicroMag 2900/3900 Data File"):  # check first line
                print("No valid MicroMag file. Header not found in first line.")
                return None

            if len(sl) == 0:  # empty line
                if sectionstart:  # this is already the second empty line, something is wrong
                    print('reading header finished at line %d' % (lc - 1))
                    break  # end of header
                sectionstart = True
                continue  # go to next line
            if sectionstart:  # previous line was empty
                sectionstart = False
                if sl.isupper():  # we have a capitalized section header
                    print('reading header section %s' % sl)
                    sectiontitle = sl
                    header[sectiontitle] = {}  # make new dictionary to gather data fields
                    sectioncount += 1
                    continue  # go to next line
                else:  # no captitalized section header after empty line -> we are probably at the end of the header
                    print('reading header finished at line %d' % lc - 1)
                    break  # end of header
            if sectiontitle is not None:  # we are within a section
                # split key value at fixed character position
                key = sl[:31].strip()
                value = sl[31:].strip(' "')
                if len(key) != 0:
                    header[sectiontitle][key] = value
        header['meta'] = {}
        header['meta']['numberoflines'] = lc - 1  # store header length
        header['meta']['numberofsections'] = sectioncount
        return header

    datachunktype = 'drift'  # defines actual chunk type 'drift' / 'forc'

    driftdata = None
    forcdata = None

    f = open(filename)
    # find start of data

    hl = -1  # line number of data header
    chunkline = 0  # line number within current data chunk
    chunkcount = 0  # count number of chunks in file
    Halen = 0  # Ha dimension of data
    Hblen = 0  # Hb dimension of data

    lines = f.readlines()

    f.close()

    header = readMicroMagHeader(lines)

    if header is None:  # no valid data file
        return None

    print(header)

    cl = header['meta']['numberoflines']  # current line number

    for line in lines[cl:]:
        cl += 1  # increase current line number count
        if "".join(line.split()).startswith('FieldMoment'):
            hl = cl  # set header line number to current line number
            print('data header detected in line %d' % hl)

        if cl > hl + 1 and hl != -1:  # now we are in the data part

            if line.strip() == '':  # empty line toggles between drift and forc data chunk
                chunkcount += 1
                if not chunkcount < skipchunks:
                    if datachunktype == 'drift':
                        datachunktype = 'forc'
                    elif datachunktype == 'forc':
                        datachunktype = 'drift'
                chunkline = 0

                continue  # go on to next line

            # go to next line in file if we have to skip this chunk
            if chunkcount < skipchunks:
                continue

            # here we know that we have to expect a valid data line of datachunktype
            chunkline += 1
            lstrs = line.strip().split(',')  # split comma seperated values
            if len(lstrs) < 2:
                print('ERROR: line %d does not contain comma seperated values. Skipping rest of file.' % cl)
                break
            # dl = np.array( map( float, lstrs))
            dl = np.array(lstrs, dtype=float)
            print(dl)
            if len(dl) == 2:  # we only got two elements, i.e. no temperature
                dl = np.append(dl, 0)  # lets append a zero for now

            if datachunktype == 'drift':
                print("reading drift chunk from line %d" % cl)
                if chunkline > 1:
                    print(
                        'ERROR: more than one dataset found in drift data chunk (line %d). Skipping rest of file.' % cl)
                    break
                # add dataset to driftdata
                if driftdata is None:
                    driftdata = np.reshape(dl, (1, len(dl)))  # reshape needed to form 2D array
                else:
                    driftdata = np.vstack((driftdata, dl))  # append line to array

            elif datachunktype == 'forc':
                # add dataset to forcdata
                if chunkline == 1:  # start of forc chunk --> first value is Ha
                    print("reading forc chunk from line %d" % cl)
                    Ha = dl[0]
                    MHa = dl[1]  # magnetic moment at Ha, needed to reflect data
                    Halen += 1  # count number of Ha steps
                Hb, M, T = dl
                fl = np.array((Ha, Hb, M, T))
                if forcdata is None:
                    forcdata = np.reshape(fl, (1, len(fl)))  # reshape needed to form 2D array
                else:
                    print('adding forc point line %d' % cl)
                    forcdata = np.vstack((forcdata, fl))  # append line to array
                    if reflect:  # extend forc space to Hb < Ha by point reflection for each branch
                        flr = np.array((fl[0], 2 * fl[0] - fl[1], 2 * MHa - M, T))  # create reflected point
                        forcdata = np.vstack((forcdata, flr))
                        chunkline += 1
                    print('done adding forc point line %d' % cl)
                if chunkline > Hblen:
                    Hblen = chunkline  # make Hblen size of largest FORC chunk

            else:
                print('bad datachunktype: ' + str(datachunktype))

    return driftdata, forcdata, Halen, Hblen


def TranslateHaHbHcHu(HaHbdata):
    ''' translate from Ha,Hb coordinates into common Hu,Hc coordinates'''
    # Hu = (Ha+Hb) / 2
    # Hc = (Hb-Ha) / 2
    HcHudata = None
    for fl in HaHbdata:
        Hu = (fl[0] + fl[1]) / 2
        Hc = (fl[1] - fl[0]) / 2

        newfl = (Hc, Hu, fl[2])

        if HcHudata is None:
            HcHudata = np.reshape(newfl, (1, len(newfl)))  # reshape needed to form 2D array
        else:
            HcHudata = np.vstack((HcHudata, newfl))  # append line to array

    return HcHudata


if __name__ == '__main__':  # test routine

    #forcdata = importFORCdata('../data/140401-Gd2O3_2.forc')
    forcdata = importFORCdata('../data/FeNi100-A-a-24-M001_005.forc', reflect=True)
    #forcdata = importFORCdata('../data/FeNi0_heated.forc', reflect=True, skipchunks=4)


    if forcdata is None:
        print('no forc data. exiting.')
        sys.exit(0)

    dd, fd, Halen, Hblen = forcdata

    # print forcdata

    # print Halen, Hblen
    # plot drift data
    # line, = plt.plot( dd[:,1])
    # plt.show()

    # plot raw forc data M( Ha, Hb)
    x = fd[:, 1]  # Hb
    y = fd[:, 0]  # Ha
    z = fd[:, 2]
    # define grid

    minHa, maxHa = min(y), max(y)
    minHb, maxHb = min(x), max(x)

    print(maxHa)
    # evenly spaced grid
    xi = np.linspace(minHb, maxHb, Hblen)
    yi = np.linspace(minHa, maxHa, Halen)
    grid = np.meshgrid(xi, yi)
    # grid the data
    points = np.column_stack((x,y))
    zi = griddata(points, z, tuple(grid), method='cubic', fill_value=np.nan)

    # contour the gridded data
    plt.contourf(xi, yi, zi, 50, cmap=plt.cm.get_cmap("jet"))

    # plt.imshow( zi, origin='lower', extent=(minHb, maxHb, minHa, maxHa), cmap='jet')
    plt.colorbar()  # draw colorbar
    plt.xlabel('Hb')
    plt.ylabel('Ha')
    plt.title('FORC raw data (magnetic moments)')
    plt.axis('equal')
    # plt.show()

    # calculate FORC diagram by fitting polygon surfaces to subareas of the gridded data
    SF = 2  # smoothing factor (use subarea of (2*SF+1)^2 for fitting)

    fittedFORCdata = None

    for Hbc in range(SF, Hblen - SF):  # walk through Ha and Hb space
        for Hac in range(SF, Halen - SF):
            # get sub area of gridded data
            fitdata = zi[Hac - SF:Hac + SF + 1, Hbc - SF:Hbc + SF + 1]

            if fitdata.shape == (2 * SF + 1, 2 * SF + 1):  # check if data is available for all points of subarea
                Hafd, Hbfd, Mfd = [], [], []
                for Hbfc in range(fitdata.shape[0]):
                    for Hafc in range(fitdata.shape[1]):
                        Hafd.append(Hafc)
                        Hbfd.append(Hbfc)
                        Mfd.append(fitdata[Hbfc, Hafc])

                # fit polynomial surface to sub area  f = c0 + c1 x + c2 y + c3 x**2 + c4 y**2 + c5 x*y
                coefficients, residues, rank, singval = fitPolySurface(np.array(Hbfd), np.array(Hafd), np.array(Mfd))

                # fitted data -> one point in FORC diagram
                fdata = np.array((minHa + (maxHa - minHa) / Halen * Hac, minHb + (maxHb - minHb) / Hblen * Hbc,
                                  -0.5 * coefficients[5]))

                if fittedFORCdata is None:
                    fittedFORCdata = np.reshape(fdata, (1, len(fdata)))  # reshape needed to form 2D array
                else:
                    fittedFORCdata = np.vstack((fittedFORCdata, fdata))  # append line to array

    # plot FORC diagram in Ha, Hb
    x, y, z = fittedFORCdata[:, 1], fittedFORCdata[:, 0], fittedFORCdata[:, 2]
    # define grid

    # xi = np.linspace(min(x),max(x), Hblen)
    # yi = np.linspace(min(y),max(y), Halen)

    # grid the data
    points = np.column_stack((x, y))
    zi = griddata(points, z, tuple(grid), method='cubic', fill_value=np.nan)
    # print zi
    plt.figure(2)
    # contour the gridded data
    plt.contourf(xi, yi, zi, 50, cmap=plt.cm.get_cmap("jet"))
    # print(zi)
    # plt.imshow( zi, origin='lower', extent=(minHb, maxHb, minHa, maxHa), cmap='RdBu')
    plt.colorbar()  # draw colorbar
    plt.xlabel('Hb')
    plt.ylabel('Ha')
    plt.title('FORC processed (SF=%d)' % SF)
    plt.axis('equal')

    print(fittedFORCdata.shape)
    fittedFORCdata = TranslateHaHbHcHu(fittedFORCdata)

    x, y, z = fittedFORCdata[:, 0], fittedFORCdata[:, 1], fittedFORCdata[:, 2]
    # define grid

    xi = np.linspace(0, max(x), Halen * 2)  # Hc space
    yi = np.linspace(min(y), max(y), Hblen * 2)  # Hu space
    grid = np.meshgrid(xi, yi)

    # grid the data
    points = np.column_stack((x, y))
    zi = griddata(points, z, tuple(grid), method='cubic', fill_value=np.nan)
    plt.figure(3)
    # contour the gridded data
    plt.contourf(xi, yi, zi, 50, cmap=plt.cm.get_cmap("jet"))
    plt.axhline(0, color='black')
    # plt.imshow( zi, origin='lower', extent=(minHb, maxHb, minHa, maxHa), cmap='RdBu')
    plt.colorbar()  # draw colorbar
    # plot data points.
    plt.xlabel('Hc')
    plt.ylabel('Hu')
    # show data points
    # plt.scatter( x, y)
    plt.title('FORC processed (SF=%d)' % SF)
    # plt.axis('equal')

    # plt.xlim( [0, 0.1])
    # plt.ylim( [-0.1, 0.03])
    # plt.savefig( fname + '.png')

    plt.show()