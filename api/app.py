from dotenv import load_dotenv
import os
from flask import Flask

load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

app = Flask(__name__)
import routes

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
