from pymongo import MongoClient

client = MongoClient('mongodb://database/argo')
db = client.argo

lattice = []
longitudes = [i + 0.5 for i in range(-180, 180)]
latitudes = [i + 0.5 for i in range(-90, 90)] # just filling out the whole grid for now, missing points will vary based on updates, don't really want to encode it here.
for lon in longitudes:
    for lat in latitudes:
        lattice.append([lon, lat])

localGPintegral = { "_id" : "localGPintegralsummary", "data" : [ "potential_temperature" ], "lattice" : lattice } 

try:
	db['summaries'].insert_one(localGPintegral)
except BaseException as err:
	print('error: db write failure')
	print(err)
