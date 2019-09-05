#NOTE TO SELF: To push to heroku: "heroku login" then "git push heroku master"

from flask import Flask, render_template, url_for, jsonify, request, send_from_directory
import dataManager 
import pandas as pd
app = Flask(__name__, static_url_path='')


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

@app.route("/location")
def location():
   return render_template('location.html', title='Location History')

@app.route("/location/endpoint", methods=['POST'])
def locationendpoint():

    data = request.get_json()

    locations = data['locations']

    #Store every value sent by the endpoint to the main CSV file 'history.csv'
    for entry in locations:
        dataManager.storeCSVLine(entry)
    
    dataManager.createKMLFiles()


    return jsonify(data)


#@app.route("/location/endpoint")
#def location():

if __name__ == '__main__':
    app.run(debug=True)
