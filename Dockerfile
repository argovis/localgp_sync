FROM python:3.9

RUN apt-get update -y; apt-get install -y nano
RUN pip install scipy numpy pymongo xarray geopy requests

WORKDIR /app
COPY populate_db.py /app/populate_db.py
COPY parameters/basinmask_01.nc parameters/basinmask_01.nc 
RUN chown -R 1000660000 /app
