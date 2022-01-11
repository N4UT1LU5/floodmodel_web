import os

from backend import modeling as mdl

from flask import Flask, render_template, request, Response
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
    res = mdl.createFloodzoneMultiTileJSON(height, loc)
    if res == False:
        return Response(status=201)
    else:
        return res


@app.route("/api/createGeb", methods=["post"])
def getGebOverlap():
    flood_json = request.json
    res = mdl.getBuildingFloodOverlap(flood_json)
    if res == None:
        return Response(status=201)
    else:
        return res


@app.route("/")
def root():
    return render_template("index.html")


# Debug
if __name__ == "__main__":
    app.run(port=port)
