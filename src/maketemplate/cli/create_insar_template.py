#!/usr/bin/env python3
import os
import re
import sys
import math
import argparse
import datetime
from datetime import datetime as dt
from datetime import timedelta as td
import src.maketemplate.asf_extractor as asf_extractor


EXAMPLE = f"""
DEFAULT FULLPATH FOR xlsfile IS ${os.getenv('SCRATCHDIR')}

create_insar_template.py --xlsfile Central_America.xlsx --save
create_insar_template.py --subswath '1 2' --url https://search.asf.alaska.edu/#/?zoom=9.065&center=130.657,31.033&polygon=POLYGON((130.5892%2031.2764,131.0501%2031.2764,131.0501%2031.5882,130.5892%2031.5882,130.5892%2031.2764))&productTypes=SLC&flightDirs=Ascending&resultsLoaded=true&granule=S1B_IW_SLC__1SDV_20190627T092113_20190627T092140_016880_01FC2F_0C69-SLC
create_insar_template.py  --polygon 'POLYGON((130.5892 31.2764,131.0501 31.2764,131.0501 31.5882,130.5892 31.5882,130.5892 31.2764))' --relativeOrbit 54 --subswath '1 2' --satellite 'Sen' --start-date '20160601' --end-date '20230926'
"""
SCRATCHDIR = os.getenv('SCRATCHDIR')


def create_parser():
    synopsis = 'Create Template for insar processing'
    epilog = EXAMPLE
    parser = argparse.ArgumentParser(description=synopsis, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--xlsfile', type=str, help="Path to the xlsfile file with volcano data.")
    parser.add_argument('--url', type=str, help="URL to the ASF data.")
    parser.add_argument('--polygon', type=str, help="Polygon coordinates in WKT format.")
    parser.add_argument('--relativeOrbit', dest='relative_orbit', type=int, help="relative orbit number.")
    parser.add_argument('--direction', type=str, choices=['A', 'D'], default='A', help="Flight direction (default: %(default)s).")
    parser.add_argument('--subswath', type=str, default='1 2 3', help="subswath numbers as a string (default: %(default)s).")
    parser.add_argument('--troposphericDelay-method',dest='tropospheric_delay_method', type=str, default='auto', help="Tropospheric correction mode.")
    parser.add_argument('--minTempCoh', dest='min_temp_coh', type=float, default=0.7, help="Threshold value for temporal coherence.")
    parser.add_argument('--lat-step', type=float, default=0.0002, help="Latitude step size (default: %(default)s).")
    parser.add_argument('--satellite', type=str, choices=['Sen'], default='Sen', help="Specify satellite (default: %(default)s).")
    parser.add_argument('--filename', dest='file_name', type=str, default=None, help=f"Name of template file (Default: Unknown).")
    parser.add_argument('--save', action="store_true")
    parser.add_argument('--start-date', nargs='*', metavar='YYYYMMDD', type=str, help='Start date of the search')
    parser.add_argument('--end-date', nargs='*', metavar='YYYYMMDD', type=str, help='End date of the search')
    parser.add_argument('--period', nargs='*', metavar='YYYYMMDD:YYYYMMDD, YYYYMMDD,YYYYMMDD', type=str, help='Period of the search')

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


def miaplpy_check_longitude(lon1, lon2):
    """
    Adjusts longitude values based on the Miaplpy criteria.
    """
    if abs(lon1 - lon2) > 0.2:
        val = (abs(lon1 - lon2) - 0.2) / 2
        miaLon1 = round(lon1 - val, 2) if lon1 > 0 else round(lon1 + val, 2)
        miaLon2 = round(lon2 + val, 2) if lon2 > 0 else round(lon2 - val, 2)
    else:
        miaLon1 = lon1
        miaLon2 = lon2
    return miaLon1, miaLon2


def topstack_check_longitude(lon1, lon2):
    """
    Adjusts longitude values based on the TopStack criteria.
    """
    if abs(lon1 - lon2) < 5:
        val = (5 - abs(lon1 - lon2)) / 2
        topLon1 = round(lon1 + val, 2) if lon1 > 0 else round(lon1 - val, 2)
        topLon2 = round(lon2 - val, 2) if lon2 > 0 else round(lon2 + val, 2)
    else:
        topLon1 = min(lon1, lon2)
        topLon2 = max(lon1, lon2)
    return topLon1, topLon2


def create_insar_template(inps, relative_orbit, subswath, tropospheric_delay_method, lat_step, start_date, end_date, satellite, lat1, lat2, lon1, lon2, miaLon1, miaLon2, topLon1, topLon2):
    """
    Creates an InSAR template configuration.

    Args:
        inps: Input parameters object containing various attributes.
        satellite: Satellite name or identifier.
        lat1, lat2: Latitude range.
        lon1, lon2: Longitude range.
        miaLon1, miaLon2: Miaplpy longitude range.
        topLon1, topLon2: Topstack longitude range.

    Returns:
        The generated template configuration.
    """
    lon_step = round(lat_step / math.cos(math.radians(float(lat1))), 5)

    print(f"Latitude range: {lat1}, {lat2}\n")
    print(f"Longitude range: {lon1}, {lon2}\n")
    print(f"Miaplpy longitude range: {miaLon1}, {miaLon2}\n")
    print(f"Topstack longitude range: {topLon1}, {topLon2}\n")

    template = generate_config(
        relative_orbit=relative_orbit,
        satellite=satellite,
        lat1=lat1,
        lat2=lat2,
        lon1=lon1,
        lon2=lon2,
        topLon1=topLon1,
        topLon2=topLon2,
        subswath=subswath,
        tropo=tropospheric_delay_method,
        miaLon1=miaLon1,
        miaLon2=miaLon2,
        lat_step=lat_step,
        lon_step=lon_step,
        start_date=inps.start_date[0],
        end_date= inps.end_date[0],
        min_temp_coh=inps.min_temp_coh
    )

    return template


def parse_polygon(polygon):
        polygon = polygon.replace("POLYGON((", "").replace("))", "")

        latitude = []
        longitude = []

        for word in polygon.split(','):
            if (float(word.split(' ')[1])) not in latitude:
                latitude.append(float(word.split(' ')[1]))
            if (float(word.split(' ')[0])) not in longitude:
                longitude.append(float(word.split(' ')[0]))

        lon1, lon2 = round(min(longitude),2), round(max(longitude),2)
        lat1, lat2 = round(min(latitude),2), round(max(latitude),2)

        return lat1, lat2, lon1, lon2


def get_satellite_name(satellite):
    if satellite == 'Sen':
        return 'SENTINEL-1A,SENTINEL-1B'
    elif satellite == 'Radarsat':
        return 'RADARSAT2'
    elif satellite == 'TerraSAR':
        return 'TerraSAR-X'
    else:
        raise ValueError("Invalid satellite name. Choose from ['Sen', 'Radarsat', 'TerraSAR']")


def generate_config(relative_orbit, satellite, lat1, lat2, lon1, lon2, topLon1, topLon2, subswath, tropo, miaLon1, miaLon2, lat_step, lon_step, start_date, end_date, min_temp_coh):
    config = f"""\
######################################################
ssaraopt.platform                  = {satellite}  # [Sentinel-1 / ALOS2 / RADARSAT2 / TerraSAR-X / COSMO-Skymed]
ssaraopt.relativeOrbit             = {relative_orbit}
ssaraopt.startDate                 = {start_date}  # YYYYMMDD
ssaraopt.endDate                   = {end_date}    # YYYYMMDD
######################################################
topsStack.subswath                 = {subswath} # '1 2'
topsStack.numConnections           = 3    # comment
topsStack.azimuthLooks             = 5    # comment
topsStack.rangeLooks               = 20   # comment
topsStack.filtStrength             = 0.2  # comment
topsStack.unwMethod                = snaphu  # comment
topsStack.coregistration           = auto  # [NESD geometry], auto for NESD
#topsStack.excludeDates            =  20240926
######################################################
mintpy.load.autoPath               = yes
mintpy.compute.cluster             = local #[local / slurm / pbs / lsf / none], auto for none, cluster type
mintpy.compute.numWorker           = 40 #[int > 1 / all], auto for 4 (local) or 40 (non-local), num of workers
mintpy.plot.maxMemory              = 180  #[float], auto for 4, max memory used by one call of view.py for plotting.
mintpy.networkInversion.parallel   = yes  #[yes / no], auto for no, parallel processing using dask
mintpy.save.hdfEos5                = yes   #[yes / update / no], auto for no, save timeseries to UNAVCO InSAR Archive format
mintpy.save.hdfEos5.update         = yes   #[yes / no], auto for no, put XXXXXXXX as endDate in output filename
mintpy.save.hdfEos5.subset         = yes   #[yes / no], auto for no, put subset range info in output filename
mintpy.save.kmz                    = yes   #[yes / no], auto for yes, save geocoded velocity to Google Earth KMZ file
mintpy.reference.minCoherence      = auto      #[0.0-1.0], auto for 0.85, minimum coherence for auto method
mintpy.troposphericDelay.method    = {tropo}   # pyaps  #[pyaps / height_correlation / base_trop_cor / no], auto for pyaps
mintpy.networkInversion.minTempCoh = 0.6 #[0.0-1.0], auto for 0.7, min temporal coherence for mask
######################################################
miaplpy.load.processor            = isce
miaplpy.multiprocessing.numProcessor= 40
miaplpy.inversion.rangeWindow     = 24   # range window size for searching SHPs, auto for 15
miaplpy.inversion.azimuthWindow   = 7    # azimuth window size for searching SHPs, auto for 15
miaplpy.timeseries.tempCohType    = full     # [full, average], auto for full.
miaplpy.interferograms.networkType= delaunay # network
######################################################
minsar.miaplpyDir.addition         = date  #[name / lalo / no] auto for no (miaply_$name_startDate_endDate))
mintpy.subset.lalo                 = {lat1}:{lat2},{lon1}:{lon2}
miaplpy.subset.lalo                = {lat1}:{lat2},{miaLon1}:{miaLon2}  #[S:N,W:E / no], auto for no
miaplpy.load.startDate             = auto  # 20200101
miaplpy.load.endDate               = auto 
mintpy.geocode.laloStep            = {lat_step},{lon_step}
miaplpy.timeseries.minTempCoh      = {min_temp_coh}      # auto for 0.5
mintpy.networkInversion.minTempCoh = {min_temp_coh}
######################################################
minsar.insarmaps_flag              = True
minsar.upload_flag                 = True
minsar.insarmaps_dataset           = filt*DS
"""
    return config


def main(iargs=None):
    inps = create_parser() if not isinstance(iargs, argparse.Namespace) else iargs
    data_collection = []

    if inps.xlsfile:
        from src.maketemplate.read_excel import main
        df = main(inps.xlsfile)

        for index, row in df.iterrows():
            lat1, lat2, lon1, lon2 = parse_polygon(row.polygon)

            # Perform checks
            miaLon1, miaLon2 = miaplpy_check_longitude(lon1, lon2)
            topLon1, topLon2 = topstack_check_longitude(lon1, lon2)
            yesterday = dt.now() - td(days=1)

            satellite = get_satellite_name(row.get('satellite'))

            # Create processed values dictionary
            processed_values = {
                'latitude1': lat1,
                'latitude2': lat2,
                'longitude1': lon1,
                'longitude2': lon2,
                'miaplpy.longitude1': miaLon1,
                'miaplpy.longitude2': miaLon2,
                'topsStack.longitude1': topLon1,
                'topsStack.longitude2': topLon2,
                'relative_orbit': row.get('ssaraopt.relativeOrbit', ''),
                'start_date': row.get('ssaraopt.startDate', ''),
                'end_date': yesterday.strftime('%Y%m%d') if 'auto' in row.get('ssaraopt.endDate', '') else row.get('ssaraopt.endDate', ''),
                'tropospheric_delay_method': row.get('mintpy.troposphericDelay', 'auto'),
                'subswath': row.get('topsStack.subswath', ''),
                'satellite': satellite

            }

            # Update row dictionary and append to collection
            row_dict = row.to_dict()
            row_dict.update(processed_values)
            data_collection.append(row_dict)
    else:
        # Handle URL or polygon input
        if inps.url:
            relative_orbit, satellite, direction, lat1, lat2, lon1, lon2 = asf_extractor.main(inps.url)
        else:
            lat1, lat2, lon1, lon2 = parse_polygon(inps.polygon)
            satellite = get_satellite_name(inps.satellite)
            direction = inps.direction
            relative_orbit = inps.relative_orbit

        # Perform checks
        miaLon1, miaLon2 = miaplpy_check_longitude(lon1, lon2)
        topLon1, topLon2 = topstack_check_longitude(lon1, lon2)

        # Create processed values dictionary
        processed_values = {
            'name': inps.name if hasattr(inps, 'name') else 'Unknown',
            'direction': direction,
            'ssaraopt.startDate': inps.start_date if hasattr(inps, 'start_date') else 'auto',
            'ssaraopt.endDate': inps.end_date if hasattr(inps, 'end_date') else 'auto',
            'ssaraopt.relativeOrbit': inps.relative_orbit if hasattr(inps, 'relative_orbit') else None,
            'topsStack.subswath': inps.subswath if hasattr(inps, 'subswath') else None,
            'mintpy.troposphericDelay': inps.troposphericDelay if hasattr(inps, 'troposphericDelay') else 'auto',
            'polygon': inps.polygon if hasattr(inps, 'polygon') else None,
            'satellite': satellite,
            'latitude1': lat1,
            'latitude2': lat2,
            'longitude1': lon1,
            'longitude2': lon2,
            'miaplpy.longitude1': miaLon1,
            'miaplpy.longitude2': miaLon2,
            'topsStack.longitude1': topLon1,
            'topsStack.longitude2': topLon2,
            'relative_orbit': relative_orbit
        }

        # Append processed values to collection
        data_collection.append(processed_values)

    for data in data_collection:
        template = create_insar_template(
            inps=inps,
            relative_orbit = data.get('relative_orbit',''),
            subswath = data.get('topsStack.subswath', ''),
            tropospheric_delay_method = data.get('tropospheric_delay_method', 'auto'),
            lat_step = inps.lat_step,
            start_date = data.get('start_date', ''),
            end_date = data.get('end_date', ''),
            satellite=data.get('satellite'),
            lat1=data.get('latitude1'),
            lat2=data.get('latitude2'),
            lon1=data.get('longitude1'),
            lon2=data.get('longitude2'),
            miaLon1=data.get('miaplpy.longitude1'),
            miaLon2=data.get('miaplpy.longitude2'),
            topLon1=data.get('topsStack.longitude1'),
            topLon2=data.get('topsStack.longitude2')
        )

        if inps.file_name or inps.save:
            name = inps.file_name if inps.file_name else data.get('name', '')
            sat = "Sen" if "SEN" in data.get('satellite', '').upper()[:4] else ""
            template_name = os.path.join(
                os.getenv('TEMPLATES'),
                f"{name}{sat}{data.get('direction')}{data.get('relative_orbit')}.template"
            )
            with open(template_name, 'w') as f:
                f.write(template)
                print(f"Template saved in {template_name}")

if __name__ == '__main__':
    main(iargs=sys.argv)
