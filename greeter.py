from flask import Blueprint

greeter = Blueprint('greeter', __name__)

@greeter.route('/')
def index():
    return "Hello"