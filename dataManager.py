import pandas as pd
import csv
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

VERBOSE = True

#Store the CSV Data from the POST submit
#IN: JSON formatted location data
#OUT: NO RETURN, updated location history file
def storeCSV(locations):

    bucket_name = 'flaskbucketcd'

    #https://stackoverflow.com/questions/30818341/how-to-read-a-csv-file-from-an-s3-bucket-using-pandas-in-python

    #Mount s3fs for AWS
    fs = s3fs.S3FileSystem(anon=False) # accessing all buckets you have access to with your credentials

    
    file = [[]]
    archiveFile = [[]]

    #Grab the files from aws
    with fs.open('s3://flaskbucketcd/data/history.csv', 'r') as history:
        file = list(csv.reader(history))

    raw_history = fs.open('s3://flaskbucketcd/data/raw_history.csv', 'a', newline='')
    writer = csv.writer(raw_history)

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

    archiveTimeVal = -1
    archiveLatitude = -1
    archiveLongtitude = -1
    archiveLocation = 'None'
    archiveWeather = 'None'
    archiveTemperature = -1
    archiveBatteryPercentage = -1
    archiveChargingStatus = 'False'
    archiveAltitude = -1
    archiveActivity = 'None'
    archiveSpeed = -1

    with fs.open('s3://flaskbucketcd/data/archiveCurrentVals.txt', 'r') as archiveVals:
        archiveTimeVal = int(float(archiveVals.readline()))
        archiveLatitude = archiveVals.readline().strip('\n')
        archiveLongtitude = archiveVals.readline().strip('\n')
        archiveLocation = archiveVals.readline().strip('\n')
        archiveTemperature = archiveVals.readline().strip('\n')
        archiveWeather = archiveVals.readline().strip('\n')
        archiveWeatherTime = int(archiveVals.readline().strip('\n'))
        archiveWeatherCode = archiveVals.readline().strip('\n')
        archiveBatteryPercentage = float(archiveVals.readline().strip('\n'))
        archiveChargingStatus = archiveVals.readline().strip('\n')
        archiveAltitude = archiveVals.readline().strip('\n')
        archiveActivity = archiveVals.readline().strip('\n')
        archiveSpeed = archiveVals.readline().strip('\n')
        archiveWeatherAPIkey = archiveVals.readline().strip('\n')

    #if archiveFile.shape[0] >= 1: 
    if len(file) >= 2:

        #latestTime = int(file['timestamp'].iloc[file.shape[0] - 1]
        latestTime = int(float(file[len(file) - 1][0]))

    #Counter to make sure it doesn't average all the way through without adding at least one of the vals that was averaged
    i = 0

    #Loop through values of array inside locations (dictionaries)
    for entry in tqdm.tqdm(locations):
        i+=1

        timeDate = entry['properties'].get('timestamp')

        #Convert UTC time to timestamp
        dt = datetime.strptime(timeDate[:-1], "%Y-%m-%dT%H:%M:%S")
        timezone = timeDate[-1:]
        
        #Gets the timestamp and timezone from method
        timeVal, timezone = convertTimestamps(timeDate, 'ISO8601')
        
        #If it is a duplicate point in filtered history file, skip it
        if archiveTimeVal >= timeVal:
            if VERBOSE: print('1: old data, continuing')
            continue

        #Set the new latest time to the newly entered time
        latestTime = timeVal

        #Store all relevant pieces of information that I want
        try: 
            data_type = entry['geometry'].get('type')
        
        #If it doesn't have a point tag, skip the point
        except (KeyError) as e: 
            if VERBOSE: print("2: Key Error, continuing")
            continue

        coordinates = str(entry['geometry']['coordinates'][0]) + ',' + str(entry['geometry']['coordinates'][1])
        
        try: #Motion doesn't always have properties in it
            motion = ','.join(entry['properties'].get('motion'))
            
            if motion is None:
                motion = 'None'
        
        except (IndexError, TypeError) as e: 
            motion = 'None' #if there are no properties, assign None
        
        archiveActivity = motion

        try: 
            speed = int(entry['properties'].get('speed'))
        except: 
            speed = -1

        archiveSpeed = speed
        
        battery_level = entry['properties'].get('battery_level')
        
        if battery_level is None or battery_level == 'None': 
            battery_level = -1
        else:
            battery_level = str(round(float(battery_level), 2))
        
        archiveBatteryPercentage = battery_level

        altitude = entry['properties'].get('altitude')
        
        if altitude is None or altitude == 'None': 
            altitude = -1000
        
        #Archive altitude is in feet
        archiveAltitude = round(altitude * 3.28084, 2)

        battery_state = entry['properties'].get('battery_state')
        
        if battery_state is None or battery_state == 'None': 
            battery_state = ''
        
        archiveChargingStatus = battery_state

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
    
        #Only store the data if it is the first val, or if the timestamp is chronologically after the previous
        if (len(archiveFile) == 1 or 
            int(archiveTimeVal) < int(timeVal)):
            
            writer.writerow(tempArchive)
            archiveTimeVal = int(timeVal)
        
        #if file.shape[0] >= 2:
        if len(file) >= 3:
            
            #Gets previous 2 rows of history file for calculations
            firstRow = file[len(file) - 2]
            secondRow = file[len(file) - 1]

            #Gets the val in the accuracy column, splits the horiz and vert accuracy, selects the first, and casts it as int
            accuracyList = firstRow[8].split(',')
            try: oldAccuracy = int(accuracyList[0])
            except: oldAccuracy = -1

            #Makes list and casts it to float
            firstRowCoor = firstRow[1].split(',')
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

            archiveLatitude = currentRowCoor[0]
            archiveLongtitude = currentRowCoor[1]

            #Calculate lists from created lists
            totalDistance = geopy.distance.distance((coords0[1],coords0[0]), (coords1[1],coords1[0])).meters

            #If the accuracy is too bad -> next point 
            if (currentAccuracy >= 11 or 
               (temp[-2] and stationaryBool)):

                if VERBOSE: print('3: accuracy too bad, or we have wifi and were stationary, continuing')
                continue

            #AVERAGING
            #If the motion is [] or stationary sum, or I am connected to a wifi that is not 'xfinitywifi'
            if (((stationaryBool or                             #We're stationary
               (wifi and wifi != 'xfinitywifi')) and            #We have a current wifi value
               (i != len(locations) - 1)) and                   #We aren't at the last element of our list
               averageCounter > 50):                            #Our counter is below min average count

                timeAverage += temp[0]
                latAverageSum += coords1[0]
                longAverageSum += coords1[1]
                averageCounter += 1
                if VERBOSE: print('4: averaged')
                continue
            
            #If the motion is anything other than stationary or empty, OR if there's already been 50 averaged values
            if (not stationaryBool or (not wifi or wifi == 'xfinitywifi')) or averageCounter != 0:
                
                #Gets average time, lat, and long over previous n points that were stationary
                timeResult = round(float(timeAverage / averageCounter), 1)
                latResult = latAverageSum / averageCounter
                longResult = longAverageSum / averageCounter
                
                if VERBOSE: print('5: averaged val added, counter =' + str(averageCounter))

                #Resets all averaging counters
                averageCounter = 0
                timeAverage = 0
                latAverageSum = 0
                longAverageSum = 0

                #Makes a new row for all the previous averaged values
                file.append([timeResult, str(latResult) + ',' + str(longResult), altitude, data_type, speed, motion, battery_level, battery_state, accuracy, wifi, timezone])
            
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

            #If I am biking, artificially emulate slightly worse accuracy to limit high point density
            if walkingBool:
                oldAccuracy += 30

            #If the distance between point 1 and 3 is less than the accuracy, replace the middle point with the new point
            if (totalDistance <= oldAccuracy or 
               currentAccuracy >= 30):

                #This replaces the last line in the file, aka the "middle" point of our 2nd to last, this one, and new line 
                if VERBOSE: print("6: replacing val because of insufficient distance")
                file[len(file) - 1] = temp
            
            #Else add the new val to the end of the table
            else:
                if VERBOSE: print("7: appending val")
                file.append(temp)
                
        
        #If the size is less than 2, so we can't do 3 point analysis
        else:
            
            #If there is wifi, and I am stationary, throw away the point
            if wifi and stationaryBool:
                if VERBOSE: print("8: else statement: wifi and stationary")
                continue

            #Get accuracy
            currentAccuracy = int(temp[-3].split(',')[0])
            
            #If my accuracy is lower than 11 (Most of them are 10-5), add the point to the table
            if currentAccuracy <= 11: 
                if VERBOSE: print("9: else statement: appending")
                file.append(temp)
        
    #Close large annex file that we've been writing to
    raw_history.close()

    #Writes all of filtered history to new file in bucket
    with fs.open(f"flaskbucketcd/data/history.csv",'w', newline='') as f:
        csvWriter = csv.writer(f,delimiter=',')
        csvWriter.writerows(file)

    #Write the last used time value to the file for the next use
    with fs.open(f"flaskbucketcd/data/archiveCurrentVals.txt",'w') as f:
        f.write(str(archiveTimeVal) + '\n')
        f.write(str(archiveLatitude) + '\n')
        f.write(str(archiveLongtitude) + '\n')
        f.write(str(archiveLocation) + '\n')
        f.write(str(archiveTemperature) + '\n')
        f.write(str(archiveWeather) + '\n')
        f.write(str(archiveWeatherTime) + '\n')
        f.write(str(archiveWeatherCode) + '\n')
        f.write(str(archiveBatteryPercentage) + '\n')
        f.write(str(archiveChargingStatus) + '\n')
        f.write(str(archiveAltitude) + '\n')
        f.write(str(archiveActivity) + '\n')
        f.write(str(archiveSpeed) + '\n')
        f.write(str(archiveWeatherAPIkey) + '\n')

#Make the KML Files based on the most recent data recieved
def createKMLFiles():

    #NOTE:
    #   Google maps inner-path color: 669df6 (REMEMBER TO ACCOUNT FOR KML COLOR SCHEME)
    #   Google maps outer-path color: 206cd5




    #Mount Filesystem
    fs = s3fs.S3FileSystem(anon=False)

    tf = TimezoneFinder()

    #Define styles to be used
    unknownStyle = simplekml.Style()
    unknownStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/question_mark.png'

    carStyle = simplekml.Style()
    carStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/car_map.svg'

    currentStyle = simplekml.Style()
    currentStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/current_location_map.png'

    bicycleStyle = simplekml.Style()
    bicycleStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/bicycle_map.png'

    originStyle = simplekml.Style()
    originStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/origin_map.png'

    planeStyle = simplekml.Style()
    planeStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/plane_map.png'

    runStyle = simplekml.Style()
    runStyle.iconstyle.icon.href = 'https://img.icons8.com/ios-filled/200/000000/running.png'

    stationaryStyle = simplekml.Style()
    stationaryStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/stationary.png'

    trainStyle = simplekml.Style()
    trainStyle.iconstyle.icon.href = 'http://casedelst.com/serve/activity/train_map.png'

    walkStyle = simplekml.Style()
    walkStyle.iconstyle.icon.href = 'https://img.icons8.com/ios-filled/100/000000/walking.png'

    activityDict = {'origin': originStyle,
                    'stationary': stationaryStyle,
                    'walking': walkStyle,
                    'running': runStyle,
                    'cycling': bicycleStyle,
                    'driving': carStyle,
                    'current': currentStyle,
                    'None': unknownStyle}

    #Define a new KML creator, and summary array
    dayKML = simplekml.Kml()
    dayDoc = dayKML.newdocument(name='Day Summary')
    dayCoorArr = []
    
    #Define a new KML creator, and summary array
    weekKML = simplekml.Kml()
    weekDoc = weekKML.newdocument(name='Week Summary')
    weekCoorArr = []
    
    #Define a new KML creator, and summary array
    monthKML = simplekml.Kml()
    monthDoc = monthKML.newdocument(name='Month Summary')
    monthCoorArr = []
    
    #Define a new KML creator, and summary array
    yearKML = simplekml.Kml()
    yearDoc = yearKML.newdocument(name='Year Summary')
    yearCoorArr = []

    #Define a new KML creator, and summary array
    allKML = simplekml.Kml()
    allDoc = allKML.newdocument(name='All Summary')
    allCoorArr = []

    #Number of seconds in each respective field
    year = 31104000
    month = 2592000
    week = 604800
    day = 86400

    #Read the csv
    
    #AWS
    #Grab the files from aws
    #file = pd.read_csv('s3://flaskbucketcd/data/history.csv')
    file = [[]]

    #Grab the files from aws
    with fs.open('s3://flaskbucketcd/data/history.csv', 'r') as history:
        file = list(csv.reader(history))

    #Line String takes an array of tuples: [(lat, long), (lat, long)]
    print('Entering KML File Loop')

    pastActivity = 'None'

    for i, row in tqdm.tqdm(enumerate(file)):

        if i == 0: 
            continue

        #print(index)
        timeVal = float(row[0])
        
        #This will either grab the first or only activty icon
        activity = str(row[5].split(',')[0])
        if activity in  {None, ''}: activity = 'None'
        
        #Hopefully this should eliminate all the None values of unsure activity
        if activity != 'None': #Resets the past activity if there is a valid current
            pastActivity = activity
        else: #Else grab the old one and use that
            activity = pastActivity

        if i == 1: #If we're at our first, substitute activity with origin marker
            activity = 'origin'
        elif i == (len(file) - 1): #If we're at our last, sub with current
            activity = 'current'

        long = str(round(float(row[1].split(',')[0]), 7))
        lat = str(round(float(row[1].split(',')[1]), 7))
        
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
        """  
        pointDescription = table(
                                tr(
                                    th('Altitude:'),
                                    th(str(row[2]))
                                ),
                                tr(
                                    th('Speed:'),
                                    th(str(row[4]))
                                ), 
                                tr(
                                    th('Motion Type:'),
                                    th(activity)
                                ),
                                tr(
                                    th('Phone Battery:'),
                                    th(str(round(float(row[6]), 2)))
                                )
                            )
        #pointDescription = table()
        pointDescription = lxml.etree.tostring(pointDescription, pretty_print=True, encoding='unicode', method='html')
        """
        pointDescription = ' '

        #Add all points that fit into each category into the respective summary KML file
        if time.time() - timeVal <= day:
            dayCoorArr.append((long, lat, int(row[2])))
            pnt = dayDoc.newpoint(name=timeString, 
                            description=pointDescription, 
                            coords=[(long, lat, int(row[2]))])
            pnt.style = activityDict[activity]
            
        if time.time() - timeVal <= week:
            weekCoorArr.append((long, lat, int(row[2])))
            pnt = weekDoc.newpoint(name=timeString, 
                             description=pointDescription, 
                             coords=[(long, lat, int(row[2]))])
            pnt.style = activityDict[activity]

        if time.time() - timeVal <= month:
            monthCoorArr.append((long, lat, int(row[2])))
            pnt = monthDoc.newpoint(name=timeString, 
                              description=pointDescription, 
                              coords=[(long, lat, int(row[2]))])
            pnt.style = activityDict[activity]

        if time.time() - timeVal <= year and i % 8 == 0:
            yearCoorArr.append((long, lat, int(row[2])))
            pnt = yearDoc.newpoint(name=timeString, 
                             description=pointDescription, 
                             coords=[(long, lat, int(row[2]))])
            pnt.style = activityDict[activity]
        
        if i % 10 == 0:
            allCoorArr.append((long, lat, int(row[2])))
            pnt = allDoc.newpoint(name=timeString, 
                            description=pointDescription, 
                            coords=[(long, lat, int(row[2]))])
            pnt.style = activityDict[activity]

    #----------------------------------------------------------------------------------

    dayLine = dayKML.newlinestring(name="Day Path", 
                                   description="My travels of the current day", 
                                   coords=dayCoorArr,
                                   extrude="1")
    
    weekLine = weekKML.newlinestring(name="Week Path", 
                                     description="My travels of the current week", 
                                     coords=weekCoorArr,
                                     extrude="1")
    
    monthLine = monthKML.newlinestring(name="Month Path", 
                                       description="My travels of the current month", 
                                       coords=monthCoorArr,
                                       extrude="1")
    
    yearLine = yearKML.newlinestring(name="Year Path", 
                                     description="My travels of the current year", 
                                     coords=yearCoorArr,
                                     extrude="1")
    
    allLine = allKML.newlinestring(name="All Time Path", 
                                   description="My travels since I've been tracking them", 
                                   coords=allCoorArr,
                                   extrude="1")

    with fs.open(f"flaskbucketcd/data/day.kml",'w') as f:
        f.write(dayKML.kml())

    with fs.open(f"flaskbucketcd/data/week.kml",'w') as f:
        f.write(weekKML.kml())

    with fs.open(f"flaskbucketcd/data/month.kml",'w') as f:
        f.write(monthKML.kml())

    with fs.open(f"flaskbucketcd/data/year.kml",'w') as f:
        f.write(yearKML.kml())

    with fs.open(f"flaskbucketcd/data/all.kml",'w') as f:
        f.write(allKML.kml())


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
        return 'Time Zone Currently Not Supported by dataManager.py:convertTimestamps()'

#TODO: see if I can make this useful
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