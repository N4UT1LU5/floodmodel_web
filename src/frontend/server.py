import os
from flask import Flask, render_template, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

port = os.environ.get("PORT")


@app.route("/api/createFloodzone")
def getFloodzone():
    # /api/createFloodzone?x=12345&y=12345&r=1&h=1
    x = request.args.get("x")
    y = request.arg.get("y")
    radius = request.args.get("r")
    height = request.args.get("h")
    return


@app.route("/")
def hello_world():

    return render_template("index.html")


# Debug
if __name__ == "__main__":
    app.run(port=port)
