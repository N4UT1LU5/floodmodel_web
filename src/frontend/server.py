import os
from backend import modeling as mdl

from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

port = os.environ.get("PORT")


@app.route("/api/createFloodzone")
def getFloodzone():
    # /api/createFloodzone?x=12345&y=12345&r=1&h=1
    x = int(request.args.get("x")) / 100000
    y = int(request.args.get("y")) / 100000
    point = mdl.convertToUTM32(x, y)

    radius = int(request.args.get("r"))
    height = float(request.args.get("h"))
    loc = (point[0], point[1], radius)
    return mdl.createFloodzoneMultiTileJSON(height, loc)


@app.route("/api/createGeb")
def getGebOverlap():
    x = int(request.args.get("x")) / 100000
    y = int(request.args.get("y")) / 100000
    point = mdl.convertToUTM32(x, y)

    radius = int(request.args.get("r"))
    loc = (point[0], point[1], radius)
    return mdl.getBuildingFloodOverlap(loc)


@app.route("/")
def hello_world():

    return render_template("index.html")


# Debug
if __name__ == "__main__":
    app.run(port=port)
