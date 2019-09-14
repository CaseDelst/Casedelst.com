import pandas as pd
import dataManager
import tqdm


""" df = pd.read_csv('./data/raw_history.csv')
totalList = []


for index, row in tqdm.tqdm(df.iterrows()):
    try: 
        horizAcc = row['accuracy'].split(',')[0]
        vertAcc = row['accuracy'].split(',')[1]
    except:
        horizAcc = ''
        vertAcc = ''
    
    tempList = {"type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [
          row['coordinates'].split(',')[0],
          row['coordinates'].split(',')[1]
        ]
      },
      "properties": {
        "timestamp": row['timestamp'],
        "altitude": row['altitude'],
        "speed": row['speed'],
        "horizontal_accuracy": horizAcc,
        "vertical_accuracy": vertAcc,
        "motion": [row['motion']],
        "pauses": False,
        "activity": "other_navigation",
        "desired_accuracy": 100,
        "deferred": 1000,
        "significant_change": "disabled",
        "locations_in_payload": 1,
        "battery_state": row['battery_state'],
        "battery_level": row['battery_level'],
        "device_id": "",
        "wifi": row['wifi']
      }
    }
    totalList.append(tempList)

dataManager.storeCSV(totalList) """
dataManager.createKMLFiles()
