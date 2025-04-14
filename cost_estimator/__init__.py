from flask import Flask
from .app import app

app = Flask(__name__)

def run():
    app.run(host='0.0.0.0', port=8000)