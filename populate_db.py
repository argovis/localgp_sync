# usage: python populate_db.py <data_dir> <collection_name> <matlab_varname> <varname> <units> <description>

import sys, glob, numpy, datetime, xarray, math
import scipy
from pymongo import MongoClient
from geopy import distance

def tidylon(longitude):
    # map longitude on [0,360] to [-180,180], required for mongo indexing
    if longitude <= 180:
        return longitude
    else:
        return longitude-360

def find_basin(basins, lon, lat):
    # for a given lon, lat,
    # identify the basin from the lookup table.
    # choose the nearest non-nan grid point.

    gridspacing = 0.5

    basin = basins['BASIN_TAG'].sel(LONGITUDE=lon, LATITUDE=lat, method="nearest").to_dict()['data']
    if math.isnan(basin):
        # nearest point was on land - find the nearest non nan instead.
        lonplus = math.ceil(lon / gridspacing)*gridspacing
        lonminus = math.floor(lon / gridspacing)*gridspacing
        latplus = math.ceil(lat / gridspacing)*gridspacing
        latminus = math.floor(lat / gridspacing)*gridspacing
        grids = [(basins['BASIN_TAG'].sel(LONGITUDE=lonminus, LATITUDE=latminus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latminus, lonminus)).miles),
                 (basins['BASIN_TAG'].sel(LONGITUDE=lonminus, LATITUDE=latplus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latplus, lonminus)).miles),
                 (basins['BASIN_TAG'].sel(LONGITUDE=lonplus, LATITUDE=latplus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latplus, lonplus)).miles),
                 (basins['BASIN_TAG'].sel(LONGITUDE=lonplus, LATITUDE=latminus, method="nearest").to_dict()['data'], distance.distance((lat, lon), (latminus, lonplus)).miles)]

        grids = [x for x in grids if not math.isnan(x[0])]
        if len(grids) == 0:
            # all points on land
            #print('warning: all surrounding basin grid points are NaN')
            basin = -1
        else:
            grids.sort(key=lambda tup: tup[1])
            basin = grids[0][0]
    return int(basin)

def insert_idx_integration_region(new_region, existing_regions):
    if new_region in existing_regions:
        return -1 # ie no insert needed
    for i, region in enumerate(existing_regions):
        if new_region[0] < region[0]:
            return i
        elif new_region[0] == region[0]:
            if new_region[1] < region[1]:
                return i
    return len(existing_regions)

# some globally useful facts
data_dir = sys.argv[1]
files = glob.glob(f"{data_dir}/*.mat")
collection = sys.argv[2]    # a collection should include variables that all have the same level spectrum
matlab_varname = sys.argv[3]
varname = sys.argv[4]
units = sys.argv[5]
description = sys.argv[6]
basins = xarray.open_dataset('parameters/basinmask_01.nc')
lon = numpy.arange(start=20.5, stop=380.5, step=1)
lat = numpy.arange(start=-89.5, stop=90.5, step=1)
integration_region = [int(files[0].split("/")[-1].split("_")[1]), int(files[0].split("/")[-1].split("_")[2])]
level_position = 0 # position in metadata_doc.levels corresponding to integration_region
variable_position = 0 # position in metadata_doc.data_info[0] corresponding to varname
expand_levels = True # false == overwrite level at level_position, true == insert new level
expand_variables = True # similar to levels
levels = []
variables = []

# db collection
client = MongoClient('mongodb://database/argo')
db = client.argo

# construct metadata doc
## planning one metadata doc per collection
metadata_collection = db['localGPMeta']
metaid = collection
## does this metadata doc already exist?
metadoc = metadata_collection.find_one({'_id': metaid})
if metadoc is None:
    levels = [integration_region]
    variables = [varname]
    level_position = 0
    variable_position = 0
    expand_levels = True
    expand_variables = True
    meta_doc = {
        '_id': metaid,
        'data_type': 'localGP_integral',
        'date_updated_argovis': datetime.datetime.now(),
        'source':[
            {
                'source': ['localGP'],
                'url': 'https://os.copernicus.org/articles/21/2463/2025/'
            }
        ],
        'levels': levels,
        'level_units': 'dbar integration ranges',
        'data_info': [
            variables,
            ['units', 'description'],
            [units, description]
        ],
        'lattice': {
            "center" : [
                0.5,
                0.5
            ],
            "spacing" : [
                1,
                1
            ],
            "minLat" : -89.5,       # to be double checked
            "minLon" : -179.5,
            "maxLat" : 89.5,
            "maxLon" : 179.5
        }
    }
    metadata_collection.insert_one(meta_doc)
else:
    ## append to existing doc
    ### integration region
    if integration_region in metadoc['levels']:
        level_position = metadoc['levels'].index(integration_region)
        expand_levels = False
    else:
        level_position = insert_idx_integration_region(integration_region, metadoc['levels'])
        expand_levels = True
    levels = metadoc['levels']
    ### variable
    if varname in metadoc['data_info'][0]:
        variable_position = metadoc['data_info'][0].index(varname)
        expand_variables = False
    else:
        variable_position = len(metadoc['data_info'][0])
        metadoc['data_info'][0].append(varname)
        metadoc['data_info'][2].append(units)
        metadoc['data_info'][2].append(description)
        expand_variables = True
    variables = metadoc['data_info'][0]
    metadata_collection.replace_one({'_id': metaid}, metadoc)

# construct data docs
for file in files:
    mat = scipy.io.loadmat(file)

    ## construct timestep
    f = file.split("/")[-1]
    month = int(f.split("_")[3])
    year = int(f.split("_")[4].split('.')[0])
    timestamp = datetime.datetime(year=year, month=month, day=15)

    for i in range(len(lat)):
        for j in range(len(lon)):
            _id = timestamp.strftime('%Y%m%d%H%M%S') + '_' + str(tidylon(lon[j])) + '_' + str(lat[i])
            geolocation = {
                'type': 'Point',
                'coordinates': [tidylon(lon[j]), lat[i]]
            }
            datavector = mat[matlab_varname][j,i].flatten().tolist()
            
            ## does this document already exist?
            existing_doc = db[collection].find_one({'_id': _id})
            if existing_doc is None:
                if numpy.isnan(datavector[0]):
                    continue # don't make a new doc until there's something to actually put in it
                data = [[None]*(len(levels))]*len(variables) # just in case this data doc didn't get written at all for the previous levels due to all NaNs
                data[variable_position][level_position] = datavector[0]
                data_doc = {
                    '_id': _id,
                    'metadata': [metaid],
                    'geolocation': geolocation,
                    'basin': find_basin(basins, tidylon(lon[j]), lat[i]),
                    'timestamp': timestamp,
                    'data': data,
                }
                db[collection].insert_one(data_doc)
            else:
                ## mutate data object to correct shape for new data
                if expand_levels:
                    ### need to insert new level at level_position
                    for v in range(len(existing_doc['data'])):
                        existing_doc['data'][v].insert(level_position, None)
                if expand_variables:
                    ### need to append new variable at variable_position
                    existing_doc['data'].insert(variable_position, [None]*len(levels))

                ## insert data and update document
                existing_doc['data'][variable_position][level_position] = datavector[0]
                db[collection].replace_one({'_id': _id}, existing_doc)
    

    
