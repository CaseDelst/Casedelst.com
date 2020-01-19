# NOTE To push to heroku: "heroku login" then "git push heroku master"
# NOTE Before first run, you have to set AWS environment variables for id and key
# To set AWS Keys https://devcenter.heroku.com/articles/s3

from flask import Flask, render_template, url_for, jsonify, request, send_from_directory, redirect, session
import dataManager
import pandas as pd
import socket
import boto3
import time
import requests
import s3fs
import json
import string
import random
import os

DEV = False
DEBUG = False


app = Flask(__name__, static_url_path='')

# Setup a tool to let me see the local IP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))

# Prints the IP address I need to connect to
print(' * IP: ' + str(s.getsockname()[0]) + ':' + str(5000) + '')
s.close()


@app.route("/")
@app.route("/index")
@app.route("/home")
def index():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    instagram = url_for('static', filename='instagram.png')
    email = url_for('static', filename='email.png')
    linkedin = url_for('static', filename='linkedin.png')
    github = url_for('static', filename='github.png')

    return render_template('index.html', archive=archive, signature=signature, instagram=instagram, email=email, linkedin=linkedin, github=github)

# Serves files from my website
@app.route("/serve/<path:path>")
def serve_static(path):
    return send_from_directory('static', path)

# Serves files from my website
@app.route("/serve/data/<path:path>")
def serve_data(path):
    return send_from_directory('data', path)


@app.route("/about")
def about():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    image_file = url_for('static', filename='me_pic.png')
    return render_template('about.html', archive=archive, image_file=image_file, signature=signature)


@app.route("/projects")
def projects():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    website = url_for('static', filename='website.png')
    slugbus = url_for('static', filename='slugbus.png')
    fitbit_project = url_for('static', filename='fitbit_project.png')
    ping = url_for('static', filename='ping.png')

    return render_template('projects.html', archive=archive, title='Projects', ping=ping, fitbit_project=fitbit_project, slugbus=slugbus, website=website, signature=signature)


@app.route("/blog")
def blog():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    cruzhacks = url_for('static', filename='cruzhacks.png')
    FitByte = url_for('static', filename='fitbit.png')
    return render_template('blog.html', archive=archive, title='Blog', signature=signature, cruzhacks=cruzhacks, FitByte=FitByte)


@app.route("/blog/cruzhacks")
def cruzhacks():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    return render_template('cruzhacks.html', archive=archive, title='CruzHacks', signature=signature)


@app.route("/blog/fitbyte")
def fitbyte():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    return render_template('fitbyte.html', archive=archive, title='FitByte', signature=signature)


@app.route("/portfolio")
def portfolio():

    archive = create_archive_urls()

    signature = url_for('static', filename='signature.png')
    blue_ref = url_for('static', filename='blue_ref.png')
    purple_horizon = url_for('static', filename='purple_horizon.png')
    boss = url_for('static', filename='boss.png')
    dozer = url_for('static', filename='dozer.png')
    drop = url_for('static', filename='drop.png')
    ninten = url_for('static', filename='ninten.png')
    shades = url_for('static', filename='shades.png')
    trapcity = url_for('static', filename='trapcity.png')
    tumbleweed = url_for('static', filename='prom.png')
    prom = url_for('static', filename='tumbleweed.png')
    return render_template('portfolio.html', archive=archive, title='Portfolio', blue_ref=blue_ref, purple_horizon=purple_horizon, boss=boss, dozer=dozer, drop=drop, ninten=ninten, shades=shades, trapcity=trapcity, tumbleweed=tumbleweed, prom=prom, signature=signature)

# Main location webpage
@app.route("/location")
def location():

    fs = s3fs.S3FileSystem(anon=False)
    archiveTimeVal = 0

    with fs.open('s3://flaskbucketcd/data/archiveCurrentVals.txt', 'r') as archiveVals:
        archiveTimeVal = int(float(archiveVals.readline()))

    # Slider setup:
    timeValues = [1, 1, 1, 1]

    # Accounts for pst
    timeValues[0] = 1562970616000 - 28800000

    timeValues[1] = int(str(archiveTimeVal) + '000') - 28800000
    timeValues[2] = timeValues[0] + int((timeValues[1] - timeValues[0]) * (1/4))
    timeValues[3] = timeValues[0] + int((timeValues[1] - timeValues[0]) * (3/4))

    timeValues = json.dumps(timeValues)
    archive = create_archive_urls()
    signature = url_for('static', filename='signature.png')
    return render_template('location.html', timeValues=timeValues, archive=archive, title='Location', signature=signature)

# Reciever for Location Data
@app.route("/location/endpoint", methods=['POST'])
def locationendpoint():

    print('Retrieving Data From Phone\n\n')
    data = request.get_json()
    dataHeader = request.headers
    print(dataHeader)
    locations = data['locations']
    i = 0

    # Store every value sent by the endpoint to the main CSV file 'raw_history.csv', and makes a shortened history csv
    dataManager.storeCSV(locations)
    dataManager.createKMLFiles()
    print('Stored CSV Data')

    if DEV:
        return jsonify({"result": "Currently Testing"})
    else:
        return jsonify({"result": "ok"})

# Reciever for the range slider to make the file, it it hasn't already been made
@app.route("/location/range", methods=['POST'])
def locationRange():

    # 1 is to value
    # 2 is from value
    # Response from the slider on location.html
    response = request.get_json()

    # Converts from milliseconds to seconds
    fromValue = int(int(response['1']) / 1000)
    toValue = int(int(response['2']) / 1000)

    fileName = str(fromValue) + str(toValue) + '.kml'

    if not os.path.isfile(fileName):
        print('\n--', fileName, 'not found, creating new file--')
        dataManager.createKMLRange(fromValue, toValue, fileName)

    return (fileName, 200)

# Displayer of the file made in locationRange
@app.route("/location/range/display/<filename>")
def locationRangeDisplay(filename):
    return render_template('location_range.html', filename=filename)

# Displays the all kml file
@app.route("/location/all")
def locationAll():
    return render_template('location_all.html', title='All Time Location')

# Displays the year kml file
@app.route("/location/year")
def locationYear():
    return render_template('location_year.html', title='Year Location')

# Displays the month kml file
@app.route("/location/month")
def locationMonth():
    return render_template('location_month.html', title='Month Location')

# Displays the week kml file
@app.route("/location/week")
def locationWeek():
    return render_template('location_week.html', title='Week Location')

# Displays the day kml file
@app.route("/location/day")
def locationDay():
    return render_template('location_day.html', title='Day Location')

# Displays the all kml file
@app.route("/location/test")
def locationTest():
    return render_template('location_test.html', title='Test Location')

# Refreshes the KML file
@app.route("/location/refresh")
def kmlrefresh():

    dataManager.createKMLFiles()
    return redirect(url_for('location'))


# Helper function for the status bar in every page
# Creates all the resources for the live display
def create_archive_urls():

    # accessing all buckets you have access to with your credentials
    fs = s3fs.S3FileSystem(anon=False)

    degree_sign = u'\N{DEGREE SIGN}'
    charging_sign = u'🗲'

    archive = {'Location': '',
               'Temperature': '',
               'Weather': '',
               'WeatherDescription': '',
               'BatteryImage': None,
               'BatteryPercentage': 0,
               'Altitude': -1,
               'Activity': None,
               'ActivityDescription': '',
               'Speed': -1}

    archiveTimeVal = None
    archiveLatitude = None
    archiveLongtitude = None
    archiveLocation = None
    archiveTemperature = None
    archiveWeather = None
    archiveWeatherTime = None
    archiveBatteryPercentage = None
    archiveChargingStatus = None
    archiveAltitude = None
    archiveActivity = None
    archiveSpeed = None
    archiveWeatherAPIkey = None

    with fs.open('s3://flaskbucketcd/data/archiveCurrentVals.txt', 'r') as archiveVals:
        archiveTimeVal = int(float(archiveVals.readline()))
        archiveLongtitude = archiveVals.readline().strip('\n')
        archiveLatitude = archiveVals.readline().strip('\n')
        archiveLocation = archiveVals.readline().strip('\n')
        archiveTemperature = archiveVals.readline().strip('\n')
        archiveWeather = archiveVals.readline().strip('\n')
        archiveWeatherTime = int(float(archiveVals.readline().strip('\n')))
        archiveWeatherCode = archiveVals.readline().strip('\n')
        archiveBatteryPercentage = float(archiveVals.readline().strip('\n'))
        archiveChargingStatus = archiveVals.readline().strip('\n')
        archiveAltitude = archiveVals.readline().strip('\n')
        archiveActivity = archiveVals.readline().strip('\n')
        archiveSpeed = archiveVals.readline().strip('\n')

    # Location
    archive['Location'] = archiveLocation

    # Weather
    # If the last call to archive time is longer than 10 minutes ago, refresh it

    if time.time() - archiveWeatherTime > 600:
        print('Calling WeatherMap API')

        responseObj = requests.get('http://api.openweathermap.org/data/2.5/weather?lat=' + str(
            archiveLatitude) + '&lon=' + str(archiveLongtitude) + '&APPID=' + '1eff0fee19ecf6766369ff253358f72b')
        
        #print('http://api.openweathermap.org/data/2.5/weather?lat=' + str(archiveLatitude) + '&lon=' + str(archiveLongtitude) + '&APPID=' + str(archiveWeatherAPIkey))
        #print(responseObj)
        
        response = responseObj.json()

        # If response is not an error code, rely on new data
        if response['cod'] != 404 and response['cod'] != 401 and response['cod'] != 429 and response['cod'] != 400:

            weatherDict = response.get('weather', None)

            if weatherDict:
                archiveWeather = weatherDict[0]['main'] + ',' + \
                                 weatherDict[0]['description'] + ',' + \
                                 str(response['wind']['speed'])

            archiveTemperature = float(response['main']['temp'])

            archiveWeatherTime = int(time.time())

            archiveLocation = response['name']

            # Check for day/night, then add code correctly to match filenames
            weatherCode = response['weather'][0]['icon']

            if weatherCode[2] == 'n' and (weatherCode[:2] in {'01', '02', '10'}):
                archiveWeatherCode = weatherCode
            else:
                archiveWeatherCode = weatherCode[:2]

    archive['Location'] = archiveLocation
    archive['Temperature'] = str(round(((float(archiveTemperature) - 273.15) * 9/5) + 32, 1)) + 'F' + degree_sign
    archive['Weather'] = url_for('static', filename='weather/' + str(archiveWeatherCode) + '.png')

    weatherComponents = archiveWeather.split(',')
    archive['WeatherDescription'] = weatherComponents[0] + '\n' + weatherComponents[1] + '\nWind: ' + \
                                    str(round(float(weatherComponents[2]) * 2.23694, 1)) + 'mph'

    archive['BatteryPercentage'] = str(int(float(archiveBatteryPercentage) * 100)) + '%'

    # If charging, show the charging icon
    if archiveChargingStatus == 'charging':

        # Add a little charging symbol next to percentage
        archive['BatteryPercentage'] = charging_sign + \
            archive['BatteryPercentage']

        if archiveBatteryPercentage >= 1.0:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery_charging_100.png')

        elif archiveBatteryPercentage >= .8:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery_charging_80.png')

        elif archiveBatteryPercentage >= .6:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery_charging_60.png')

        elif archiveBatteryPercentage >= .4:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery_charging_40.png')

        elif archiveBatteryPercentage >= .2:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery_charging_20.png')

        else:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery_charging_0.png')

    # Else, determine the correct level of battery to show
    else:
        if archiveBatteryPercentage >= .8:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery5.png')

        elif archiveBatteryPercentage >= .6:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery4.png')

        elif archiveBatteryPercentage >= .4:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery3.png')

        elif archiveBatteryPercentage >= .2:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery2.png')

        else:
            archive['BatteryImage'] = url_for(
                'static', filename='battery/battery1.png')

    # Altitude, check to see if our value is -1000 m in ft
    if archiveAltitude != '-3280.84':
        archive['Altitude'] = str(archiveAltitude) + 'ft'
    else:
        archive['Altitude'] = 'UNAVBL'

    # Activity
    # Figure out what image to serve

    # If the motion type is known to us, assign a known image

    if archiveActivity == 'driving':
        archive['Activity'] = url_for('static', filename='activity/car.png')
        archive['ActivityDescription'] = 'Driving'

    elif archiveActivity == 'walking':
        archive['Activity'] = url_for('static', filename='activity/walk.png')
        archive['ActivityDescription'] = 'Walking'

    elif archiveActivity == 'running':
        archive['Activity'] = url_for('static', filename='activity/run.png')
        archive['ActivityDescription'] = 'Running'

    elif archiveActivity == 'cycling':
        archive['Activity'] = url_for(
            'static', filename='activity/bicycle.png')
        archive['ActivityDescription'] = 'Cycling'

    elif archiveActivity == 'stationary':
        archive['Activity'] = url_for(
            'static', filename='activity/stationary.png')
        archive['ActivityDescription'] = 'Stationary'

    elif archiveActivity == '' or archiveActivity == None or archiveActivity == 'None':
        archive['Activity'] = url_for(
            'static', filename='activity/stationary.png')
        archive['ActivityDescription'] = 'Stationary'
    else:
        archive['Activity'] = url_for(
            'static', filename='activity/question_mark.png')
        archive['ActivityDescription'] = 'Unknown'

    # archiveSpeed, converts m/s to mph
    if archiveSpeed != '-1' or archiveSpeed != '' or archiveSpeed != None:
        archive['Speed'] = str(round(int(archiveSpeed) * 2.23694, 0)) + 'mph'
    elif archive['ActivityDescription'] == 'Stationary':
        archive['Speed'] = '0.0mph'
    else:
        archive['Speed'] = 'UNAVBL'

    # Write the last used time value to the file for the next use
    with fs.open(f"flaskbucketcd/data/archiveCurrentVals.txt", 'w') as f:
        f.write(str(archiveTimeVal) + '\n')
        f.write(str(archiveLongtitude) + '\n')
        f.write(str(archiveLatitude) + '\n')
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

    # Returns the filled dictionary with all images and text needed for the info
    return archive

# Add a header that says to always refresh a page
@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r


if __name__ == '__main__':
    if DEBUG:
        app.run(debug=True)
    else:
        app.run(debug=False)
