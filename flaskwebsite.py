from flask import Flask, render_template, url_for
app = Flask(__name__)


@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/projects")
def projects():
    return render_template('projects.html', title='Projects')


@app.route("/projects/googletasksproject")
def googletasksproject():
    return render_template('Projects/googletasksproject.html', title='Google Tasks Project')


@app.route("/projects/graphicdesign")
def graphicdesign():
    return render_template('Projects/graphic_design.html', title='Graphic Design')


@app.route("/contact")
def contact():
    return render_template('contact.html', title='Contact')


if __name__ == '__main__':
    app.run(debug=True)
