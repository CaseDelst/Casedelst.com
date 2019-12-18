import pandas as pd
from csv import writer
from io import StringIO
from datetime import datetime
from timezonefinderL import TimezoneFinder
import pytz
import time
import simplekml
import geojson
import geopy.distance
import lxml.etree
import lxml.builder
import tqdm
import boto3
import s3fs
import os


#Store the CSV Data from the POST submit
def storeCSV(locations):

    bucket_name = 'flaskbucketcd'

    #https://stackoverflow.com/questions/30818341/how-to-read-a-csv-file-from-an-s3-bucket-using-pandas-in-python

    #Mount s3fs for AWS
    fs = s3fs.S3FileSystem(anon=False) # accessing all buckets you have access to with your credentials

    #Grab the files from aws
    file = pd.read_csv('s3://flaskbucketcd/data/history.csv')
    archiveFile = pd.read_csv('s3://flaskbucketcd/data/mass_storage.csv')

    #Initialize values for stationary averaging
    timeAverage = 0
    latAverageSum = 0
    longAverageSum = 0
    averageCounter = 0
    
    stationaryBool = False
    drivingBool = False
    bikingBool = False
    walkingBool = False

    latestTime = 0

    #LOCAL
    #Loads current csv into file
    #file = pd.read_csv('./static/data/history.csv')
    #archiveFile = pd.read_csv('./static/data/raw_history.csv')
    #archiveFile = pd.read_csv('./static/data/mass_storage.csv')
    
    if file.shape[0] >= 1: 
       
        latestTime = int(file['timestamp'].iloc[file.shape[0] - 1])

    #Loop through values of array inside locations (dictionaries)
    print('Entering New Data Loop')
    
    for entry in tqdm.tqdm(locations):

        timeDate = entry['properties'].get('timestamp')

        #Convert UTC time to timestamp
        #print(timeVal)
        dt = datetime.strptime(timeDate[:-1], "%Y-%m-%dT%H:%M:%S")
        timezone = timeDate[-1:]
        
        #Gets the timestamp and timezone from method
        timeVal, timezone = convertTimestamps(timeDate, 'ISO8601')
        
        #If it is a duplicate point in filtered history file, skip it
        if latestTime >= timeVal:
            continue

        #Set the new latest time to the newly entered time
        latestTime = timeVal

        #Store all relevant pieces of information that I want
        try: 
            data_type = entry['geometry'].get('type')
        
        #If it doesn't have a point tag, skip the point
        except (KeyError) as e: 
            continue

        coordinates = str(entry['geometry']['coordinates'][0]) + ',' + str(entry['geometry']['coordinates'][1])
        
        try: #Motion doesn't always have properties in it
            motion = ','.join(entry['properties'].get('motion'))
            
            if motion is None:
                motion = 'None'
        
        except (IndexError, TypeError) as e: 
            motion = 'None' #if there are no properties, assign None
        
        try: 
            speed = int(entry['properties'].get('speed'))
        except: 
            speed = -1
        
        battery_level = entry['properties'].get('battery_level')
        
        if battery_level is None or battery_level == 'None': 
            battery_level = -1
        
        altitude = entry['properties'].get('altitude')
        
        if altitude is None or altitude == 'None': 
            altitude = -1000
        
        battery_state = entry['properties'].get('battery_state')
        
        if battery_state is None or battery_state == 'None': 
            battery_state = ''
        
        accuracy = str(entry['properties'].get('horizontal_accuracy')) + ',' + str(entry['properties'].get('vertical_accuracy'))
        
        if accuracy is None or accuracy == 'None': 
            accuracy = '0,0'
        
        timeDate = entry['properties'].get('timestamp')

        #Sets property
        wifi = entry['properties'].get('wifi')
        if wifi is None: wifi = ''
        
        #Creates an array of all the important values in the correct order
        temp = [timeVal, coordinates, altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone]   #Placeholders for heartrate, steps, calories
        
        #Set up the archival version of the array for raw_history
        tempArchive = [timeDate, coordinates, altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi]
        
        #Counts rows
        rowCount = file.shape[0]
        archRowCount = archiveFile.shape[0]

        #Sets up archiving based on previous and current timestamp
        archiveTimeDate = archiveFile['timestamp'].iloc[-1]
        dt = datetime.strptime(archiveTimeDate[:-1], "%Y-%m-%dT%H:%M:%S")
        archiveTimeVal, timezone = convertTimestamps(archiveTimeDate, 'ISO8601')

        #Only store the data if it is the first val, or if the timestamp is chronologically after the previous
        if archiveFile.shape[0] == 0 or int(archiveTimeVal) < int(timeVal):
            archiveFile.loc[archRowCount] = tempArchive
        
        if file.shape[0] >= 2:
            
            #Gets previous 2 rows of history file for calculations
            firstRow = file.loc[rowCount - 2]
            secondRow = file.loc[rowCount - 1]

            #Gets the val in the accuracy column, splits the horiz and vert accuracy, selects the first, and casts it as int
            accuracyList = firstRow['accuracy'].split(',')
            try: oldAccuracy = int(accuracyList[0])
            except: oldAccuracy = -1

            #Makes list and casts it to float
            firstRowCoor = firstRow['coordinates'].split(',')
            firstRowCoor = [float(i) for i in firstRowCoor]

            #Makes list and casts it to float
            currentRowCoor = temp[1].split(',')
            currentRowCoor = [float(i) for i in currentRowCoor]
            try: currentAccuracy = int(temp[-3].split(',')[0])
            except: currentAccuracy = -1
            currentMotion = str(entry['properties'].get('motion'))
            
            #If the motion type is stationary or [] (Empty array, so False) set the bool to True
            stationaryBool = False
            if not currentMotion or currentMotion[0] == 'stationary':
                stationaryBool = True

            drivingBool = False
            if 'driving' in currentMotion:
                drivingBool = True

            bikingBool = False
            if 'cycling' in currentMotion:
                bikingBool = True

            walkingBool = False
            if 'walking' in currentMotion:
                walkingBool = True
            
            #Get coordinates from previous lists Formatted in Lat,Long
            coords0 = (firstRowCoor[0], firstRowCoor[1])
            coords1 = (currentRowCoor[0], currentRowCoor[1])

            #Calculate lists from created lists
            totalDistance = geopy.distance.distance((coords0[1],coords0[0]), (coords1[1],coords1[0])).meters

            #If the accuracy is too bad -> next point 
            if currentAccuracy >= 11 or (temp[-2] and stationaryBool):
                continue

            #AVERAGING
            #If the motion is [] or stationary sum, or I am connected to a wifi that is not 'xfinitywifi'
            if stationaryBool or (wifi and wifi != 'xfinitywifi'):
                timeAverage += temp[0]
                latAverageSum += coords1[0]
                longAverageSum += coords1[1]
                averageCounter += 1
                continue
            
            #If the motion is anything other than stationary or empty
            if (not stationaryBool or (not wifi or wifi == 'xfinitywifi')) and averageCounter != 0:
                
                #Gets average time, lat, and long over previous n points that were stationary
                timeResult = timeAverage / averageCounter
                latResult = latAverageSum / averageCounter
                longResult = longAverageSum / averageCounter
                
                #Resets all averaging counters
                averageCounter = 0
                print('averaged ', averageCounter, ' values')
                timeAverage = 0
                latAverageSum = 0
                longAverageSum = 0

                #Makes a new row for all the previous averaged values
                file.loc[rowCount] = [timeResult, str(latResult) + ',' + str(longResult), altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone]
                
                #Moves row counter up one to follow ending line
                rowCount += 1
            
            #If I am driving, artificially emulate poor accuracy to limit point overlap 
            if drivingBool:

                #If there is a valid speed value, apply a range to get better driving data
                if speed != -1: 
                    speedRange = 90 - 0
                    accRange = 750 - 100

                    #NewValue = (((OldValue - OldMin) * NewRange) / OldRange) + NewMin
                    accOffset = (((speed - 0) * accRange) / speedRange) + 100
                    oldAccuracy += accOffset
            
                else:
                    
                    #Default car accuracy, 500m
                    oldAccuracy += 500

            #If I am biking, artificially emulate poor accuracy to limit high point density
            if bikingBool:
                oldAccuracy += 200

            #Only add values every n meters when walking
            if walkingBool:
                oldAccuracy += 30

            #If the distance between point 1 and 3 is less than the accuracy, replace the middle point with the new point
            if totalDistance <= oldAccuracy or currentAccuracy >= 30:
                file.loc[rowCount - 1] = temp
            
            #Else add the new val to the end of the table
            else:
                file.loc[rowCount] = temp
        
        #If the size is less than 2, so we can't do 3 point analysis
        else:
            
            #If there is wifi, and I am stationary, throw away the point
            if wifi and stationaryBool:
                continue

            #Get accuracy
            currentAccuracy = int(temp[-3].split(',')[0])
            
            #If my accuracy is lower than 11 (Most of them are 10-5), add the point to the table
            if currentAccuracy <= 11: file.loc[rowCount] = temp
        
    #Write to file after all done

    with fs.open(f"flaskbucketcd/data/history.csv",'w') as f:
        file.to_csv(f)
    
    #file.to_csv('s3://data/history.csv', index=False)
    
    with fs.open(f"flaskbucketcd/data/mass_storage.csv",'w') as f:
        archiveFile.to_csv(f)

#Make the KML Files based on the most recent data recieved <=-=>
def createKMLFiles():

    #Mount Filesystem
    fs = s3fs.S3FileSystem(anon=False)

    tf = TimezoneFinder()

    #Define styles to be used
    style2 = simplekml.Style() #creates shared style for all points
    style2.labelstyle.color = simplekml.Color.grey
    style2.labelstyle.scale = .75  # Text half as big


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
    
    #AWS
    #Grab the files from aws
    file = pd.read_csv('s3://flaskbucketcd/data/history.csv')

    #LOCAL
    file = pd.read_csv('./static/data/history.csv')
    
    #Line String takes an array of tuples: [(lat, long), (lat, long)]
    print('Entering KML File Loop')
    for index, row in tqdm.tqdm(file.iterrows()):

        #print(index)
        timeVal = float(row['timestamp'])

        #TEMPORARY, this only takes into account the last month of data
        if time.time() - timeVal > month:
            continue
        
        #Get the longtitude and latitude from csv row
        long = str(round(float(row['coordinates'].split(',')[0]), 7))
        lat = str(round(float(row['coordinates'].split(',')[1]), 7))
        
        #Get timezone name
        timezoneName = tf.timezone_at(lng=float(long), lat=float(lat))
    
        #Make a naive timezone object from timestamp
        utcmoment_naive = datetime.fromtimestamp(timeVal)
        
        #Make an aware timezone object
        utcmoment = utcmoment_naive.replace(tzinfo=pytz.utc)
        localFormat = "%Y-%m-%d %H:%M:%S"
        
        #Creates a local string based on variable timezone
        localDateTime = utcmoment.astimezone(pytz.timezone(timezoneName))
        timeString = localDateTime.strftime(localFormat)
        
        localTimeVal = datetime.now(pytz.timezone(timezoneName))
        timeVal = timeVal + localTimeVal.utcoffset().total_seconds()
        
        #Makes the XML Table
        E = lxml.builder.ElementMaker()
        table = E.table
        tr = E.tr
        th = E.th
        td = E.td
         
        """ tr(
                                    th('Coordinates:'),
                                    th(str(row['coordinates'])),
                                ), """
        pointDescription = table(
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
                                    th(str(round(float(row['battery_level']), 2)))
                                )
                            )
        #pointDescription = table()
        pointDescription = lxml.etree.tostring(pointDescription, pretty_print=True, encoding='unicode', method='html')

        #Add all points that fit into each category into the respective summary KML file
        if time.time() - timeVal <= day:
            dayCoorArr.append((long, lat, int(row['altitude'])))
            pnt = dayFol.newpoint(name=timeString, 
                            description=pointDescription, 
                            coords=[(long, lat, int(row['altitude']))])
            pnt.style = style2

        if time.time() - timeVal <= week:
            weekCoorArr.append((long, lat, int(row['altitude'])))
            pnt = weekFol.newpoint(name=timeString, 
                             description=pointDescription, 
                             coords=[(long, lat, int(row['altitude']))])

        if time.time() - timeVal <= month:
            monthCoorArr.append((long, lat, int(row['altitude'])))
            pnt = monthFol.newpoint(name=timeString, 
                              description=pointDescription, 
                              coords=[(long, lat, int(row['altitude']))])
            
            pnt.style = style2

        """
        if time.time() - timeVal <= year:
            yearCoorArr.append((long, lat, int(row['altitude'])))
            pnt = yearFol.newpoint(name=timeString, 
                             description=pointDescription, 
                             coords=[(long, lat, int(row['altitude']))])
            
            pnt.style = style2
        
        allCoorArr.append((long, lat, int(row['altitude'])))
        pnt = allFol.newpoint(name=timeString, 
                        description=pointDescription, 
                        coords=[(long, lat, int(row['altitude']))])

        print('4: ' + str(time.time()))

        pnt.style = style2
        """
        #end row looping
    
    dayLine = dayKML.newlinestring(name="Day Path", 
                                   description="My travels of the current day", 
                                   coords=dayCoorArr,
                                   extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    
    weekLine = weekKML.newlinestring(name="Week Path", 
                                     description="My travels of the current week", 
                                     coords=weekCoorArr,
                                     extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    monthLine = monthKML.newlinestring(name="Month Path", 
                                       description="My travels of the current month", 
                                       coords=monthCoorArr,
                                       extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5

    """
    yearLine = yearKML.newlinestring(name="Year Path", 
                                     description="My travels of the current year", 
                                     coords=yearCoorArr,
                                     extrude="1")
    dayLine.style.linestyle.color = 'ff0000ff'
    dayLine.style.linestyle.width = 5
    
    allLine = allKML.newlinestring(name="All Time Path", 
                                   description="My travels since I've been tracking them", 
                                   coords=allCoorArr,
                                   extrude="1")
    allLine.style.linestyle.color = 'ff0000ff'
    allLine.style.linestyle.width = 5
    """

    with fs.open(f"flaskbucketcd/data/day.kml",'w') as f:
        f.write(dayKML.kml())

    with fs.open(f"flaskbucketcd/data/week.kml",'w') as f:
        f.write(weekKML.kml())

    with fs.open(f"flaskbucketcd/data/month.kml",'w') as f:
        f.write(monthKML.kml())

    #dayKML.save('./static/data/day.kml')
    #weekKML.save('./static/data/week.kml')
    #monthKML.save('./static/data/month.kml')
    
    """
    #For Local Saving
    yearKML.save('./static/data/year.kml')
    allKML.save('./static/data/all.kml')
    """

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

def massStoreCSV(locations):
    #Instantiates a pandas dataframe
        
        frame = []
        file = pd.read_csv('.\static\\data\\mass_storage.csv')
        print(file)
        #Row counter
        i = 0
        
        #Loop through values of array inside locations (dictionaries)
        for entry in tqdm.tqdm(locations):

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
            
            timestamp = entry['properties'].get('timestamp')
            
            wifi = entry['properties'].get('wifi')
            if wifi is None: wifi = ''
            
            #Creates an array of all the important values in the correct order
            temp = [timestamp, coordinates, altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi]
            
            #Sets the row of the dataframe to the values in temp, correctly ordered
            file.loc[file.shape[0]] = temp
            
            #Increment row counter
            i += 1
        
        #Returns the complete dataframe, fixes all nans
        
        print(file)
        file.to_csv('static\\data\\mass_storage.csv', index=False)