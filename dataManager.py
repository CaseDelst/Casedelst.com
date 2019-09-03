import pandas as pd
from datetime import datetime
def storeCSVLine(entry):

    #Loop through values of array inside locations (dictionaries)
    #Store all relevant pieces of information that I want
    data_type = entry['geometry'].get('type')
    coordinates = str(entry['geometry']['coordinates'][0]) + ',' + str(entry['geometry']['coordinates'][1])
    
    try: #Motion doesn't always have properties in it
        motion = ','.join(entry['properties'].get('motion'))
    except (IndexError, TypeError) as e: 
        motion = 'None' #if there are no properties, assign None
    
    speed = entry['properties'].get('speed')
    if speed is None: speed = -1
    
    battery_level = entry['properties'].get('battery_level')
    if battery_level is None: battery_level = -1
    
    altitude = entry['properties'].get('altitude')
    if altitude is None: altitude = -1000
    
    battery_state = entry['properties'].get('battery_state')
    if battery_state is None: battery_state = ''
    
    accuracy = str(entry['properties'].get('horizontal_accuracy')) + ',' + str(entry['properties'].get('vertical_accuracy'))
    if accuracy is None: accuracy = '0,0'
    
    timeVal = entry['properties'].get('timestamp')

    #Convert UTC time to timestamp
    dt = datetime.strptime(timeVal[:-5], "%Y-%m-%dT%H:%M:%S")
    timezone = timeVal[-4:]
    dt = convertTimestamps(timeVal, 'ISO8601')
    timeVal, timezone= dt.timestamp()
    
    wifi = entry['properties'].get('wifi')
    if wifi is None: wifi = ''
    
    #Creates an array of all the important values in the correct order
    temp = [timeVal, coordinates, altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone]
    
    print(temp)

    file = pd.read_csv('.\data\history.csv')

    file.loc[file.shape[0]] = temp

    file.to_csv('.\data\history.csv', index=False)




def createKMLFiles():L


#Converts the timestamp from whatever format into unix
#IN: Time, String of Format
#OUT: Unix Timestamp in UTC, timezone
def convertTimestamps(time, timeFormat):
    
    if timeFormat == 'ISO8601':
        dt = datetime.strptime(time[:-5], "%Y-%m-%dT%H:%M:%S")
        timezone = time[-4:]
        return dt, timezone

    else:
        return 'Time Zone Currently Not Supported by dataManager.py:convertTimestamps():59'