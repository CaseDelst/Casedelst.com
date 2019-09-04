import pandas as pd
from datetime import datetime
import time
import simplekml
from xml.sax.saxutils import unescape
import lxml.etree
import lxml.builder

#Store the CSV Data from the POST submit
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
    timezone = timeVal[-5:]
    
    #Gets the timestamp and timezone from method
    timeVal, timezone = convertTimestamps(timeVal, 'ISO8601')

    #Inserts a colon in between the hours and minutes
    timezone = timezone[0:3] + ':' +timezone[3:] 
    print('First timeval' + str(timeVal))
    
    wifi = entry['properties'].get('wifi')
    if wifi is None: wifi = ''
    
    #Creates an array of all the important values in the correct order
    temp = [timeVal, coordinates, altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone, '', '', '']   #Placeholders for heartrate, steps, calories
    
    print(temp)

    file = pd.read_csv('.\data\history.csv')

    file.loc[file.shape[0]] = temp

    file.to_csv('.\data\history.csv', index=False)

#Make the KML Files based on the most recent data recieved
def createKMLFiles():

    #Define a new KML creator, and summary array
    dayKML = simplekml.Kml()
    dayKML.document.name = "Day Summary"
    dayCoorArr = []
    
    #Define a new KML creator, and summary array
    weekKML = simplekml.Kml()
    weekKML.document.name = "Week Summary"
    weekCoorArr = []
    
    #Define a new KML creator, and summary array
    monthKML = simplekml.Kml()
    monthKML.document.name = "Month Summary"
    monthCoorArr = []
    
    #Define a new KML creator, and summary array
    yearKML = simplekml.Kml()
    yearKML.document.name = "Year Summary"
    yearCoorArr = []

    #Define a new KML creator, and summary array
    allKML = simplekml.Kml()
    allKML.document.name = "All Time Summary"
    allCoorArr = []

    #Number of seconds in each respective field
    year = 31104000
    month = 2592000
    week = 604800
    day = 86400

    #Read the csv
    file = pd.read_csv('.\data\history.csv')
    
    #Line String takes an array of tuples: [(lat, long), (lat, long)]
    for index, row in file.head().iterrows():

        #Get both the unix time and time string
        timeString = str(datetime.fromtimestamp(float(row['timestamp']))) 
        timeVal = float(row['timestamp'])

        #Get the longtitude and latitude from csv row
        long = row['coordinates'].split(',')[0]
        lat = row['coordinates'].split(',')[1]
       
        #Makes the XML Table
        E = lxml.builder.ElementMaker()
        table = E.table
        tr = E.tr
        th = E.th
        td = E.td

        pointDescription = table(
                                tr(
                                    th('Coordinates'),
                                    th('Altitude'),
                                    th('Speed'),
                                    th('Phone Battery'),
                                    th('Heartrate'),
                                    th('Steps'),
                                    th('Calories')
                                ),
                                tr(
                                    th(str(row['coordinates'])),
                                    th(str(row['altitude'])),
                                    th(str(row['speed'])),
                                    th(str(row['battery_level'])),
                                    th(str(row['heartrate'])),
                                    th(str(row['steps'])),
                                    th(str(row['calories']))
                                )
                            )

        pointDescription = lxml.etree.tostring(pointDescription, pretty_print=True, encoding='unicode', method='html')
        
        print(pointDescription)

        #Add all points that fit into each category into the respective summary KML file
        if time.time() - timeVal <= day:
            dayCoorArr.append((long, lat, int(row['altitude'])))
            dayKML.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativetoground")

        if time.time() - timeVal <= week:
            weekCoorArr.append((long, lat, int(row['altitude'])))
            weekKML.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativetoground")

        if time.time() - timeVal <= month:
            monthCoorArr.append((long, lat, int(row['altitude'])))
            monthKML.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativetoground")

        if time.time() - timeVal <= year:
            yearCoorArr.append((long, lat, int(row['altitude'])))
            yearKML.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativetoground")
        
        allCoorArr.append((long, lat, int(row['altitude'])))
        allKML.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativetoground")
        #end row looping
    
    dayLine = dayKML.newlinestring(name="Day Path", 
                         description="My travels of the current day", 
                         coords=dayCoorArr, 
                         altitudemode="relativeToGround")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    
    weekLine = weekKML.newlinestring(name="Week Path", 
                          description="My travels of the current week", 
                          coords=weekCoorArr, 
                          altitudemode="relativeToGround")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    monthLine = monthKML.newlinestring(name="Month Path", 
                           description="My travels of the current month", 
                           coords=monthCoorArr, 
                           altitudemode="relativeToGround")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    yearLine = yearKML.newlinestring(name="Year Path", 
                          description="My travels of the current year", 
                          coords=yearCoorArr, 
                          altitudemode="relativeToGround")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5
    
    allLine = allKML.newlinestring(name="All Time Path", 
                         description="My travels since I've been tracking them", 
                         coords=allCoorArr, 
                         altitudemode="relativeToGround",
                         extrude="1")
    allLine.style.linestyle.color = 'ff0000ff'
    allLine.style.linestyle.width = 5

    dayKML.save('./data/day.kml')
    weekKML.save('./data/week.kml')
    monthKML.save('./data/month.kml')
    yearKML.save('./data/year.kml')
    allKML.save('./data/all.kml')

#Converts the timestamp from whatever format into unix
#IN: Time, String of Format
#OUT: Unix Timestamp in UTC, timezone
def convertTimestamps(time, timeFormat):
    
    if timeFormat == 'ISO8601':
        dt = datetime.strptime(time[:-5], "%Y-%m-%dT%H:%M:%S")
        dt = dt.timestamp()

        timezone = time[-5:]
        return dt, timezone

    else:
        return 'Time Zone Currently Not Supported by dataManager.py:convertTimestamps():59'

#Calculate Local Time