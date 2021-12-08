import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)


port = os.environ.get("PORT")


@app.route("/")
def hello_world():

    return render_template("index.html")


# Debug
if __name__ == "__main__":
    app.run(port=port)
