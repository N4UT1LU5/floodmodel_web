import os
from backend import modeling as mdl

# import src.backend.modeling as modl
from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

port = os.environ.get("PORT")


@app.route("/api/createFloodzone")
def getFloodzone():
    # /api/createFloodzone?x=12345&y=12345&r=1&h=1
    x = int(request.args.get("x"))
    y = int(request.args.get("y"))
    radius = int(request.args.get("r"))
    height = int(request.args.get("h"))
    loc = (x, y, radius)
    return mdl.createFloodzoneMultiTile(height, loc)


@app.route("/")
def hello_world():

    return render_template("index.html")


# Debug
if __name__ == "__main__":
    app.run(port=port)
