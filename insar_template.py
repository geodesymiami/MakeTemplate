import os
import re
import sys
import math
import argparse
import datetime
import pyperclip
import asf_extractor


EXAMPLE = """
insar_template --swath '1 2' --url https://search.asf.alaska.edu/#/?zoom=9.065&center=130.657,31.033&polygon=POLYGON((130.5892%2031.2764,131.0501%2031.2764,131.0501%2031.5882,130.5892%2031.5882,130.5892%2031.2764))&productTypes=SLC&flightDirs=Ascending&resultsLoaded=true&granule=S1B_IW_SLC__1SDV_20190627T092113_20190627T092140_016880_01FC2F_0C69-SLC
insar_template --polygon 'POLYGON((130.5892 31.2764,131.0501 31.2764,131.0501 31.5882,130.5892 31.5882,130.5892 31.2764))' --path 54 --swath '1 2' --satellite 'Sen' --start-date '20160601' --end-date '20230926'
"""
SCRATCHDIR = os.getenv('SCRATCHDIR')


def create_parser():
    synopsis = 'Create Template for insar processing'
    epilog = EXAMPLE
    parser = argparse.ArgumentParser(description=synopsis, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--url', type=str, help="URL to the ASF data.")
    parser.add_argument('--polygon', type=str, help="Polygon coordinates in WKT format.")
    parser.add_argument('--path', type=int, help="Path number.")
    parser.add_argument('--swath', type=str, default='1 2 3', help="Swath numbers as a string (default: %(default)s).")
    parser.add_argument('--troposphere', action="store_true", help="Tropospheric correction mode.")
    parser.add_argument('--thresh', type=float, default=0.7, help="Threshold value for temporal coherence.")
    parser.add_argument('--lat-step', type=float, default=0.0002, help="Latitude step size (default: %(default)s).")
    parser.add_argument('--satellite', type=str, choices=['Sen'], default='Sen', help="Specify satellite (default: %(default)s).")
    parser.add_argument('--save-name', type=str, default=None, help=f"Save the template with specified Volcano name ({os.getenv('TEMPLATES')}/Volcano.template).")
    parser.add_argument('--start-date', nargs='*', metavar='YYYYMMDD', type=str, help='Start date of the search')
    parser.add_argument('--end-date', nargs='*', metavar='YYYYMMDD', type=str, help='End date of the search')
    parser.add_argument('--period', nargs='*', metavar='YYYYMMDD:YYYYMMDD, YYYYMMDD,YYYYMMDD', type=str, help='Period of the search')
    parser.add_argument("--jeststream", action="store_true", help="Upload on jetstream")
    parser.add_argument("--insarmaps", action="store_true", help="Upload on insarmaps")

    inps = parser.parse_args()

    if inps.period:
        for p in inps.period:
            delimiters = '[,:\-\s]'
            dates = re.split(delimiters, p)

            if len(dates[0]) and len(dates[1]) != 8:
                msg = 'Date format not valid, it must be in the format YYYYMMDD'
                raise ValueError(msg)

            inps.start_date.append(dates[0])
            inps.end_date.append(dates[1])
    else:
        if not inps.start_date:
            inps.start_date = "20160601"
        if not inps.end_date:
            inps.end_date = datetime.datetime.now().strftime("%Y%m%d")

    return inps


def get_satellite_name(satellite):
    if satellite == 'Sen':
        return 'SENTINEL-1A,SENTINEL-1B'
    elif satellite == 'Radarsat':
        return 'RADARSAT2'
    elif satellite == 'TerraSAR':
        return 'TerraSAR-X'
    else:
        raise ValueError("Invalid satellite name. Choose from ['Sen', 'Radarsat', 'TerraSAR']")


def generate_config(path, satellite, lat1, lat2, lon1, lon2, topLon1, topLon2, swath, tropo, miaLon1, miaLon2, lat_step, lon_step, start_date, end_date, thresh, jetstream, insarmaps):
    config = f"""\
######################################################
cleanopt                          = 0   # [ 0 / 1 / 2 / 3 / 4]   0,1: none 2: keep merged,geom_master,SLC 3: keep MINTPY 4: everything
processor                         = isce
ssaraopt.platform                 = {satellite}  # [Sentinel-1 / ALOS2 / RADARSAT2 / TerraSAR-X / COSMO-Skymed]
ssaraopt.relativeOrbit            = {path}
ssaraopt.startDate                = {start_date}  # YYYYMMDD
ssaraopt.endDate                  = {end_date}    # YYYYMMDD
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
minsar.upload_flag                = {jetstream}    # [True / False ], upload to jetstream (Default: False)
minsar.insarmaps_flag             = {insarmaps}
minsar.insarmaps_dataset          = filt*DS
#############################################
"""
    return config


def main(iargs=None):
    inps = create_parser() if not isinstance(iargs, argparse.Namespace) else iargs

    if inps.url:
        inps.path, satellite, node, lat1, lat2, lon1, lon2 = asf_extractor.main(inps.url)
    else:
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

        satellite = get_satellite_name(inps.satellite)

##### Miaplpy check for longitude #####
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
#######################################

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

    print(f"Latitude range: {lat1}, {lat2}")
    print(f"Longitude range: {lon1}, {lon2}")
    print(f"Miaplpy longitude range: {miaLon1}, {miaLon2}")
    print(f"Topstack longitude range: {topLon1}, {topLon2}")

    template = generate_config(
    path=inps.path,
    satellite=satellite,
    lat1=lat1,
    lat2=lat2,
    lon1=lon1,
    lon2=lon2,
    topLon1=topLon1,
    topLon2=topLon2,
    swath=inps.swath,
    tropo=inps.troposphere,
    miaLon1=miaLon1,
    miaLon2=miaLon2,
    lat_step=inps.lat_step,
    lon_step=lon_step,
    start_date=inps.start_date,
    end_date=inps.end_date,
    thresh=inps.thresh
)

    if inps.save_name:
        if "SEN" in satellite[:4].upper():
            sat = "Sen"

        template_name = os.path.join(os.getenv('TEMPLATES'), inps.save_name + sat + node + inps.path + '.template')
        with open(template_name, 'w') as f:
            f.write(template)
            print(f"Template saved in {template_name}")
    else:
        pyperclip.copy(template)
        print(template)
        print('-'*100)

if __name__ == '__main__':
    main(iargs=sys.argv)