from flask import render_template, jsonify, request, flash, redirect, url_for, session, abort, send_from_directory
import os
import copy
from datetime import datetime
import json
import time

from . import public_bp
from app.models import User
from app import db
from app.source.chowlk.services.transformations import transform_ontology
from app.source.chowlk.resources.utils import read_drawio_xml
from app.source.chowlk.resources.generate_xml_errors import generate_xml_error

# Load favicon
@public_bp.route('/favicon.ico')
def favicon():
    print(public_bp.root_path)
    return send_from_directory(os.path.join(public_bp.root_path, '../static/images/favicon_io'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Load main web page
@public_bp.route("/")
@public_bp.route("/index")
def index():
    return render_template("index.html")

# Load notation web page
@public_bp.route("/notation")
def notation():
    return render_template("notation.html")

# Load example web page
@public_bp.route("/examples")
def examples():
    return render_template("examples.html")

# Load notation web page
@public_bp.route("/about")
def about():
    return render_template("about.html")

# Load version history web page
@public_bp.route("/versionHistory")
def versionHistory():
    return render_template("versionHistory.html")

# Load secondary web pages
@public_bp.route("/<path:path>")
def send_static(path):
    return render_template(path)

# Chowlk application
@public_bp.route("/api", methods=["GET", "POST"])
def api():

    if request.method == "POST":
        #inicio = time.time()
        file = request.files["data"]
        filename = file.filename

        if filename == "":
            error = "No file choosen. Please choose a diagram."
            flash(error)
            return redirect(url_for("index"))

        # output file name 
        ttl_filename = filename[:-3] + "ttl"

        # Temporal folder called input to store the xml file (input)
        os.makedirs("data/input", exist_ok=True)
        input_path = os.path.join("data/input", filename)

        # Temporal folder called output to store the ttl file (output)
        os.makedirs("data/output", exist_ok=True)
        ttl_filepath = os.path.join("data/output", ttl_filename)

        # Store the diagram
        file.save(input_path)

        xml_error_generated = True

        try:
            # Transforming the diagram
            root = read_drawio_xml(input_path)
            turtle_file_string, xml_file_string, new_namespaces, errors, warnings = transform_ontology(root)
        except:
            return {'ttl_data': "", "errors": {'Server Error': {'message': 'Server error, review the input diagram'}}, 'new_namespaces': {}, 'xml_error_generated': False, 'xml_error_file': "", 'warnings': ""}

        try:
            xml_error_file, xml_error_generated = generate_xml_error(input_path, errors, os.path.join("data/output", filename[:-3] + "xml"))
        except:
            errors['Server Error'] = {'message': 'Server error, something wrong happened trying to generate the xml file with the errors'}
            xml_error_generated = False
            xml_error_file = ""


        # write output file in the tmp folder
        with open(ttl_filepath, "w") as file:
            file.write(turtle_file_string)

        # Eliminating keys that do not contain errors
        new_errors = {}
        for key, error in errors.items():
            if len(error) > 0:
                new_errors[key] = error
        
        # Eliminating keys that do not contain warnings
        new_warnings = {}
        for key, warning in warnings.items():
            if len(warning) > 0:
                new_warnings[key] = warning

        session["ttl_filename"] = ttl_filename

        # store the results of the converter in the database
        # user = User(date = datetime.now(), input = input_path, output = ttl_filepath, errors = errors)
        # user.save()

        #fin = time.time()
        #print(fin-inicio)

        return {'ttl_data': turtle_file_string, "errors": new_errors, "new_namespaces": new_namespaces, 'xml_error_generated': xml_error_generated, 'xml_error_file': xml_error_file, 'warnings': new_warnings}
    
    