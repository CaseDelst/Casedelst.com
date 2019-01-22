from flask import Flask, render_template, url_for

app = Flask(__name__)


@app.route("/")
@app.route("/index")
def index():
    signature = url_for('static', filename='signature.png')
    return render_template('index.html', signature=signature)


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
    return render_template('blog.html', title='Blog', signature=signature, CruzHacks=CruzHacks)


@app.route("/blog/cruzhacks")
def cruzhacks():
    return render_template('cruzhacks.html', title='CruzHacks')


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


@app.route("/projects/googletasksproject")
def googletasksproject():
    signature = url_for('static', filename='signature.png')
    return render_template('Projects/googletasksproject.html', title='Google Tasks Project', signature=signature)


@app.route("/projects/graphicdesign")
def graphicdesign():
    signature = url_for('static', filename='signature.png')
    return render_template('Projects/graphic_design.html', title='Graphic Design', signature=signature)


if __name__ == '__main__':
    app.run(debug=True)
