#NOTE TO SELF: To push to heroku: "heroku login" then "git push heroku master"

from flask import Flask, render_template, url_for, jsonify, request, send_from_directory
import dataManager 
import pandas as pd
import socket
app = Flask(__name__, static_url_path='')

#Setup a tool to let me see the local IP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect(("8.8.8.8", 80))

#Prints the IP address I need to connect to
print(' * IP: ' + str(s.getsockname()[0]) + ':' + str(5000) + '') 
s.close()

@app.route("/")
@app.route("/index")
def index():
    signature = url_for('static', filename='signature.png')
    return render_template('index.html', signature=signature)

@app.route("/data/<path:path>")
def send_kml(path):
    return send_from_directory('data', path)

@app.route("/about")
def about():
    signature = url_for('static', filename='signature.png')
    image_file = url_for('static', filename='me_pic.png')
    return render_template('about.html', image_file=image_file, signature=signature)


@app.route("/projects")
def projects():
    signature = url_for('static', filename='signature.png')
    return render_template('projects.html', title='Projects', signature=signature)


@app.route("/blog")
def blog():
    signature = url_for('static', filename='signature.png')
    CruzHacks = url_for('static', filename='CruzHacks.jpg')
    FitByte   = url_for('static', filename='fitbit.png')
    return render_template('blog.html', title='Blog', signature=signature, CruzHacks=CruzHacks, FitByte=FitByte)


@app.route("/blog/cruzhacks")
def cruzhacks():
    signature = url_for('static', filename='signature.png')
    return render_template('cruzhacks.html', title='CruzHacks', signature=signature)

@app.route("/blog/fitbyte")
def fitbyte():
    signature = url_for('static', filename='signature.png')
    return render_template('fitbyte.html', title='FitByte', signature=signature)


@app.route("/portfolio")
def portfolio():
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
    return render_template('portfolio.html', title='Portfolio', blue_ref=blue_ref, purple_horizon=purple_horizon, boss=boss, dozer=dozer, drop=drop, ninten=ninten, shades=shades, trapcity=trapcity, tumbleweed=tumbleweed, prom=prom, signature=signature)

#Main location webpage
@app.route("/location")
def location():
    signature = url_for('static', filename='signature.png')
    return render_template('location.html', title='Location', signature=signature)

@app.route("/location/all")
def locationAll():
    return render_template('location_all.html', title='All Time Location')

@app.route("/location/year")
def locationYear():
    return render_template('location_year.html', title='Year Location')

@app.route("/location/month")
def locationMonth():
    return render_template('location_month.html', title='Month Location')

@app.route("/location/week")
def locationWeek():
    return render_template('location_week.html', title='Week Location')

@app.route("/location/day")
def locationDay():
    return render_template('location_day.html', title='Day Location')

@app.route("/location/test")
def locationTest():
    return render_template('location_test.html', title='Test Location')

#Reciever for Location Data
@app.route("/location/endpoint", methods=['POST'])
def locationendpoint():
    print('Retrieving Data From Phone\n\n')
    data = request.get_json()
    dataHeader = request.headers
    print(dataHeader)
    locations = data['locations']
    i = 0

    #Store every value sent by the endpoint to the main CSV file 'history.csv', and makes a shortened history csv
    dataManager.massStoreCSV(locations)
    print('Stored CSV Data')

    return jsonify({"result":"ok"})

@app.route("/location/refresh")
def kmlrefresh():
    dataManager.createKMLFiles()
    signature = url_for('static', filename='signature.png')
    return render_template('location.html', title='Location', signature=signature)

#@app.route("/location/endpoint")
#def location():

#Add a header that says to always refresh a page
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
    app.run(debug=True)
