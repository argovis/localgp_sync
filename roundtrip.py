import glob, scipy, requests, time, numpy

files = glob.glob(f"data/integrals/potential_temperature/15_50/*.mat")

for file in files:
    mat = scipy.io.loadmat(file)

    month = int(file.split('/')[-1].split("_")[3])
    year = int(file.split('/')[-1].split("_")[4].split('.')[0])
    startDate = f"{year}-{month:02d}-01T00:00:00Z"
    endDate = f"{year}-{month:02d}-01T00:00:01Z"
    print('checking timestamp', startDate)

    longitude = 20.5
    latitude = -89.5
    data = mat['fullFieldGrid']

    av = requests.get(
                "https://argovis-apix-atoc-argovis-dev.apps.containers02.colorado.edu/grids/localGPintegral", 
                {
                    'startDate': startDate,
                    'endDate': endDate,
                    'data': 'all'
                }
            )
    av = av.json()
    print('grid points found:', len(av))

    for doc in av:
        longitude = doc['geolocation']['coordinates'][0]
        latitude = doc['geolocation']['coordinates'][1]

        longitude_idx = int((longitude - 20.5)%360)
        latitude_idx = int(latitude + 89.5)

        flag = True
        if data[longitude_idx][latitude_idx] == doc['data'][0][0]:
            flag = False
        if flag:
            print(f"Mismatch at lon {longitude}, lat {latitude}, timestamp {startDate}")
            print(data[longitude_idx][latitude_idx], av)        


    # for i in range(0,len(data)):
    #     print('checking longitude', longitude)
    #     for j in range(len(data[0])):
    #         flag = True
    #         if numpy.isnan(data[i][j]) and len(av.json())==0:
    #             flag = False
    #         elif data[i][j] == av.json()[0]['data'][0][0]:
    #             flag = False
    #         if flag:
    #             print(f"Mismatch at lon {longitude}, lat {latitude}, timestamp {startDate}: {data[i][j]}")
    #             print(data[i][j], av.json())
            
    #         time.sleep(1)
    #         latitude += 1
    #     longitude += 1
    #     latitude = -89.5
