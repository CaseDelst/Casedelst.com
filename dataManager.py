import pandas as pd
from datetime import datetime
import time
import simplekml
import geojson
import geopy.distance
import lxml.etree
import lxml.builder

#Store the CSV Data from the POST submit
def storeCSV(locations):

    #Initialize values for stationary averaging
    timeAverage = 0
    latAverageSum = 0
    longAverageSum = 0
    averageCounter = 0
    stationaryBool = False

    #Loop through values of array inside locations (dictionaries)
    for entry in locations:

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
        #print(timeVal)
        dt = datetime.strptime(timeVal[:-1], "%Y-%m-%dT%H:%M:%S")
        timezone = timeVal[-1:]
        
        #Gets the timestamp and timezone from method
        timeVal, timezone = convertTimestamps(timeVal, 'ISO8601')
        
        #Sets property
        wifi = entry['properties'].get('wifi')
        if wifi is None: wifi = ''
        
        #Creates an array of all the important values in the correct order
        temp = [timeVal, coordinates, altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone]   #Placeholders for heartrate, steps, calories
        
        #Loads current csv into file
        file = pd.read_csv('.\data\history.csv')

        #Counts rows
        rowCount = file.shape[0]

        if file.shape[0] >= 2:
            
            firstRow = file.loc[rowCount - 2]
            secondRow = file.loc[rowCount - 1]

            #Gets the val in the accuracy column, splits the horiz and vert accuracy, selects the first, and casts it as int
            accuracyList = firstRow['accuracy'].split(',')
            oldAccuracy = int(accuracyList[0])

            
            
            #Makes list and casts it to float
            firstRowCoor = firstRow['coordinates'].split(',')
            firstRowCoor = [float(i) for i in firstRowCoor]

            #Makes list and casts it to float
            currentRowCoor = temp[1].split(',')
            currentRowCoor = [float(i) for i in currentRowCoor]
            currentAccuracy = int(temp[-3].split(',')[0])
            currentMotion = entry['properties'].get('motion')
            
            #If the motion typoe is stationary or [] set the bool to True
            stationaryBool = False
            if not currentMotion or currentMotion[0] == 'stationary':
                stationaryBool = True

            #Get coordinates from previous lists Formatted in Lat,Long
            coords0 = (firstRowCoor[0], firstRowCoor[1])
            coords1 = (currentRowCoor[0], currentRowCoor[1])

            #Calculate lists from created lists
            totalDistance = geopy.distance.distance(coords0, coords1).meters

            #If the accuracy is too bad -> next point 
            if currentAccuracy >= 11 or (temp[-2] and stationaryBool):
                continue

            #If the motion is [] or stationary sum
            if stationaryBool:
                timeAverage += temp[0]
                latAverageSum += coords1[0]
                longAverageSum += coords1[1]
                averageCounter += 1
                continue
            
            #If the motion is anything other than stationary or empty
            if not stationaryBool and averageCounter != 0:
                timeResult = timeAverage / averageCounter
                latResult = latAverageSum / averageCounter
                longResult = longAverageSum / averageCounter
                
                averageCounter = 0
                timeAverage = 0
                latAverageSum = 0
                longAverageSum = 0

                file.loc[rowCount] = [timeResult, str(latResult) + ',' + str(longResult), altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone]
                rowCount += 1

            
            # if motion type is nan or stationary
            # sum, increment counter
            # as soon as it's not, divide sum by counter and add point reset counter and sum
            # when incrementing, continue after increment

            #If the distance between point 1 and 3 is less than the accuracy, replace the middle point with the new point
            if totalDistance <= oldAccuracy or currentAccuracy >= 30:
                #print("replacing val with distance of: " + str(totalDistance) + '\nAccuracy of: ' + str(accuracy) + '\n')
                file.loc[rowCount - 1] = temp
            
            #Else add the new val to the end of the table
            else:
                #print("Adding to end: " + str(totalDistance) + '\nAccuracy of: ' + str(accuracy) + '\n')
                file.loc[rowCount] = temp
        
        #If the size is less than 2
        else:
            
            #If there is wifi, and I am stationary, throw away the point
            if temp[-2] and stationaryBool:
                continue
            currentAccuracy = int(temp[-3].split(',')[0])
            if currentAccuracy <= 11: file.loc[rowCount] = temp
        
        #X = Longtitude, Y = Latitude
        file.to_csv('.\data\history.csv', index=False)

#Make the KML Files based on the most recent data recieved <=-=>
def createKMLFiles():

    #Define a new KML creator, and summary array
    dayKML = simplekml.Kml()
    dayFol = dayKML.newfolder(name='Data Points')
    dayKML.document.name = "Day Summary"
    dayCoorArr = []
    
    #Define a new KML creator, and summary array
    weekKML = simplekml.Kml()
    weekFol = weekKML.newfolder(name='Data Points')
    weekKML.document.name = "Week Summary"
    weekCoorArr = []
    
    #Define a new KML creator, and summary array
    monthKML = simplekml.Kml()
    monthFol = monthKML.newfolder(name='Data Points')
    monthKML.document.name = "Month Summary"
    monthCoorArr = []
    
    #Define a new KML creator, and summary array
    yearKML = simplekml.Kml()
    yearFol = yearKML.newfolder(name='Data Points')
    yearKML.document.name = "Year Summary"
    yearCoorArr = []

    #Define a new KML creator, and summary array
    allKML = simplekml.Kml()
    allFol = allKML.newfolder(name='Data Points')
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
    for index, row in file.iterrows():
        print(index)
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
                                    th('Coordinates:'),
                                    th(str(row['coordinates'])),
                                ),
                                tr(
                                    th('Altitude:'),
                                    th(str(row['altitude']))
                                ),
                                tr(
                                    th('Speed:'),
                                    th(str(row['speed']))
                                ), 
                                tr(
                                    th('Motion Type:'),
                                    th(str(row['motion']))
                                ), 
                                tr(
                                    th('GPS Accuracy:'),
                                    th(str(row['accuracy']))
                                ),
                                tr(
                                    th('Phone Battery:'),
                                    th(str(row['battery_level']))
                                )
                            )

        pointDescription = lxml.etree.tostring(pointDescription, pretty_print=True, encoding='unicode', method='html')

        #Add all points that fit into each category into the respective summary KML file
        if time.time() - timeVal <= day:
            dayCoorArr.append((long, lat, int(row['altitude'])))
            dayFol.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativeToGround")

        if time.time() - timeVal <= week:
            weekCoorArr.append((long, lat, int(row['altitude'])))
            weekFol.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativeToGround")

        if time.time() - timeVal <= month:
            monthCoorArr.append((long, lat, int(row['altitude'])))
            monthFol.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativeToGround")

        if time.time() - timeVal <= year:
            yearCoorArr.append((long, lat, int(row['altitude'])))
            yearFol.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativeToGround")
        
        allCoorArr.append((long, lat, int(row['altitude'])))
        allFol.newpoint(name=timeString, description=pointDescription, coords=[(long, lat, int(row['altitude']))], altitudemode="relativeToGround")
        #end row looping
    
    dayLine = dayKML.newlinestring(name="Day Path", 
                         description="My travels of the current day", 
                         coords=dayCoorArr, 
                         altitudemode="relativeToGround",
                         extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    
    weekLine = weekKML.newlinestring(name="Week Path", 
                          description="My travels of the current week", 
                          coords=weekCoorArr, 
                          altitudemode="relativeToGround",
                         extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    monthLine = monthKML.newlinestring(name="Month Path", 
                           description="My travels of the current month", 
                           coords=monthCoorArr, 
                           altitudemode="relativeToGround",
                         extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    yearLine = yearKML.newlinestring(name="Year Path", 
                          description="My travels of the current year", 
                          coords=yearCoorArr, 
                          altitudemode="relativeToGround",
                         extrude="1")
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
        dt = datetime.strptime(time[:-1], "%Y-%m-%dT%H:%M:%S")
        dt = dt.timestamp()

        timezone = time[-1:]
        return dt, timezone

    else:
        return 'Time Zone Currently Not Supported by dataManager.py:convertTimestamps():59'

#Calculate Local Time

