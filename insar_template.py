import os
import sys
import math
import argparse
import pyperclip


EXAMPLE = """

"""
SCRATCHDIR = os.getenv('SCRATCHDIR')


def create_parser():
    synopsis = 'Create Template for insar processing'
    epilog = EXAMPLE
    parser = argparse.ArgumentParser(description=synopsis, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--polygon', type=str, required=True, help="Polygon coordinates in WKT format.")
    parser.add_argument('--path', type=int, required=True, help="Path number.")
    parser.add_argument('--swath', type=str, required=True, help="Swath numbers as a string.")
    parser.add_argument('--troposphere', type=str, action="staore_true", help="Tropospheric correction mode.")
    parser.add_argument('--thresh', type=float, default=0.7, help="Threshold value for temporal coherence.")
    parser.add_argument('--lat-step', type=float, required=True, help="Latitude step size.")

    inps = parser.parse_args()

    return inps


def generate_config(path, lat1, lat2, lon1, lon2, topLon1, topLon2, swath, tropo, miaLon1, miaLon2, lat_step, lon_step, thresh):
    config = f"""\
######################################################
cleanopt                          = 0   # [ 0 / 1 / 2 / 3 / 4]   0,1: none 2: keep merged,geom_master,SLC 3: keep MINTPY 4: everything
processor                         = isce
ssaraopt.platform                 = SENTINEL-1A,SENTINEL-1B
ssaraopt.relativeOrbit            = {path}
ssaraopt.startDate                = 20160601
#ssaraopt.endDate                  = 20211130
hazard_products_flag              = False
#insarmaps_flag                     = True
######################################################
#topsStack.boundingBox             = {lat1} {lat2} {topLon1} {topLon2}    # -1 0.15 -91.6 -90.9
#topsStack.excludeDates            =  20240926
topsStack.subswath                = {swath} # '1 2'
topsStack.numConnections          = 4    # comment
topsStack.azimuthLooks            = 3    # comment
topsStack.rangeLooks              = 15   # comment
topsStack.filtStrength            = 0.2  # comment
topsStack.unwMethod               = snaphu  # comment
topsStack.coregistration          = auto  # [NESD geometry], auto for NESD
#topsStack.referenceDate           = 20151220

######################################################
mintpy.load.autoPath              = yes
mintpy.subset.lalo                = {lat1}:{lat2},{lon1}:{lon2}
mintpy.compute.cluster            = local #[local / slurm / pbs / lsf / none], auto for none, cluster type
mintpy.compute.numWorker          = 30 #[int > 1 / all], auto for 4 (local) or 40 (non-local), num of workers
#mintpy.reference.lalo             = {lat1},{lon1}     # S of SN

mintpy.networkInversion.parallel  = yes  #[yes / no], auto for no, parallel processing using dask
mintpy.network.tempBaseMax        = auto  #[1-inf, no], auto for no, max temporal baseline in days
mintpy.network.perpBaseMax        = auto  #[1-inf, no], auto for no, max perpendicular spatial baseline in meter
mintpy.network.connNumMax         = auto  #[1-inf, no], auto for no, max number of neighbors for each acquisition
mintpy.network.coherenceBased     = auto  #[yes / no], auto for no, exclude interferograms with coherence < minCoherence
mintpy.network.aoiLALO            = auto  #[S:N,W:E / no], auto for no - use the whole area
mintpy.networkInversion.minTempCoh  = 0.6 #[0.0-1.0], auto for 0.7, min temporal coherence for mask

mintpy.troposphericDelay.method   = {tropo}   # pyaps  #[pyaps / height_correlation / base_trop_cor / no], auto for pyaps
mintpy.save.hdfEos5               = yes   #[yes / update / no], auto for no, save timeseries to UNAVCO InSAR Archive format
mintpy.save.hdfEos5.update        = yes   #[yes / no], auto for no, put XXXXXXXX as endDate in output filename
mintpy.save.hdfEos5.subset        = yes   #[yes / no], auto for no, put subset range info in output filename
mintpy.save.kmz                   = yes   #[yes / no], auto for yes, save geocoded velocity to Google Earth KMZ file
####################
minsar.miaplpyDir.addition         = date  #[name / lalo / no] auto for no (miaply_$name_startDate_endDate))
miaplpy.subset.lalo                = {lat1}:{lat2},{miaLon1}:{miaLon2}  #[S:N,W:E / no], auto for no
miaplpy.load.startDate             = auto # 20200101
miaplpy.load.endDate               = auto
mintpy.geocode.laloStep            = {lat_step},{lon_step}
mintpy.reference.minCoherence      = 0.5      #[0.0-1.0], auto for 0.85, minimum coherence for auto method
miaplpy.interferograms.delaunayBaselineRatio = 4
miaplpy.interferograms.delaunayTempThresh    = 120     # [days] temporal threshold for delaunay triangles, auto for 120
miaplpy.interferograms.delaunayPerpThresh    = 200     # [meters] Perp baseline threshold for delaunay triangles, auto for 200
miaplpy.interferograms.networkType           = single_reference # network
miaplpy.interferograms.networkType           = delaunay # network
#############################################
miaplpy.load.processor            = isce
miaplpy.multiprocessing.numProcessor = 40
miaplpy.inversion.rangeWindow     = 24   # range window size for searching SHPs, auto for 15
miaplpy.inversion.azimuthWindow   = 7    # azimuth window size for searching SHPs, auto for 15
miaplpy.timeseries.tempCohType    = full     # [full, average], auto for full.
miaplpy.timeseries.minTempCoh     = 0.50     # auto for 0.5
mintpy.networkInversion.minTempCoh = {thresh}
#############################################
minsar.upload_flag                = False    # [True / False ], upload to jetstream (Default: False)
minsar.insarmaps_flag             = False
minsar.insarmaps_dataset          = filt*DS
#############################################
"""
    return config


def main(iargs=None):
    inps = create_parser() if not isinstance(iargs, argparse.Namespace) else iargs

    inps.polygon = inps.polygon.replace("POLYGON((", "").replace("))", "")

    latitude = []
    longitude = []

    for word in inps.polygon.split(','):
        if (float(word.split(' ')[1])) not in latitude:
            latitude.append(float(word.split(' ')[1]))
        if (float(word.split(' ')[0])) not in longitude:
            longitude.append(float(word.split(' ')[0]))

    lon1, lon2 = round(min(longitude),2), round(max(longitude),2)
    lat1, lat2 = round(min(latitude),2), round(max(latitude),2)

##### MIAplpy check for longitude #####
    if abs(lon1 - lon2) > 0.2:
        val = (abs(lon1 - lon2) - 0.2)/2
        if lon1 > 0:
            miaLon1 = round(lon1 - val, 2)
        else:
            miaLon1 = round(lon1 + val, 2)
        if lon2 > 0:
            miaLon2 = round(lon2 + val, 2)
        else:
            miaLon2 = round(lon2 - val, 2)
    else:
        miaLon1 = lon1
        miaLon2 = lon2
########################################

##### TopStack check for longitude #####
    if abs(lon1 - lon2) < 5:
        val = (5 - abs(lon1 - lon2))/2
        if lon1 > 0:
            topLon1 = round(lon1 + val, 2)
        else:
            topLon1 = round(lon1 - val, 2)
        if lon2 > 0:
            topLon2 = round(lon2 - val, 2)
        else:
            topLon2 = round(lon2 + val, 2)
    else:
        topLon1 = min(lon1, lon2)
        topLon2 = max(lon1, lon2)
########################################

    lon_step = round(inps.lat_step / math.cos(math.radians(int(lat1))), 5)

    print(f"Latitude range: lat1 = {lat1}, lat2 = {lat2}")
    print(f"Longitude range: lon1 = {lon1}, lon2 = {lon2}")
    print(f"Miaplpy longitude range: miaLon1 = {miaLon1}, miaLon2 = {miaLon2}")
    print(f"Topstack longitude range: topLon1 = {topLon1}, topLon2 = {topLon2}")

    template = generate_config(
    path=inps.path,
    lat1=lat1,
    lat2=lat2,
    lon1=lon1,
    lon2=lon2,
    topLon1=topLon1,
    topLon2=topLon2,
    swath=inps.swath,
    tropo=inps.tropo,
    miaLon1=miaLon1,
    miaLon2=miaLon2,
    lat_step=inps.lat_step,
    lon_step=lon_step,
    thresh=inps.thresh
)

    pyperclip.copy(template)
    print(template)
    print('-'*100)

if __name__ == '__main__':
    main(iargs=sys.argv)