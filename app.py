from flask import Flask
from greeter import greeter
from flask_cors import CORS

#import custom modules
from user import user
from well import well
from welldata import welldata
from dashboard import dashboard
from test import test

app = Flask(__name__)
CORS(app)
app.register_blueprint(greeter)
app.register_blueprint(user)
app.register_blueprint(well)
app.register_blueprint(welldata)
app.register_blueprint(dashboard)
app.register_blueprint(test)