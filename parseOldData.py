import pandas as pd
import dataManager
import s3fs
import boto3
import tqdm
import csv
import tqdm

fs = s3fs.S3FileSystem(anon=False)
totalList = []
file = [[]]

#Grab the files from aws
with fs.open('s3://flaskbucketcd/data/raw_history.csv', 'r') as history:
    file = list(csv.reader(history))

i = -1
for row in tqdm.tqdm(file):
    i+= 1

    if i == 0:
        continue
    
    try: 
        horizAcc = row[8].split(',')[0]
        vertAcc = row[8].split(',')[1]
    except:
        horizAcc = ''
        vertAcc = ''
    
    tempList = {"type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          row[1].split(',')[0],
          row[1].split(',')[1]
        ]
      },
      "properties": {
        "timestamp": row[0],
        "altitude": row[2],
        "speed": row[4],
        "horizontal_accuracy": horizAcc,
        "vertical_accuracy": vertAcc,
        "motion": [row[5]],
        "pauses": False,
        "activity": "other_navigation",
        "desired_accuracy": 100,
        "deferred": 1000,
        "significant_change": "disabled",
        "locations_in_payload": len(file) - 1,
        "battery_state": row[7],
        "battery_level": row[6],
        "device_id": "",
        "wifi": row[9]
      }
    }

    totalList.append(tempList)

#Once all data has been populated into a list, feed it into the filter to fill out the history fill
dataManager.storeCSV(totalList)
#dataManager.createKMLFiles()
