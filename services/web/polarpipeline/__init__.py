import sys
sys.path.append('/usr/src/app/polarpipeline')

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory
from selenium.webdriver.chrome.options import Options
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, SubmitField
from flask_socketio import SocketIO, emit
from tasks import process, processT2T
from flask_wtf import FlaskForm
from selenium import webdriver
from datetime import datetime
from bs4 import BeautifulSoup
from pyfaidx import Fasta
import urllib.parse
import configparser
import pandas as pd
import numpy as np
import subprocess
import threading
import psycopg2
import pyhgvsv
import pyhgvsv.utils as pu
import hashlib
import zipfile
import shutil
import time
import json
import svg
import csv
import ast
import os
import re

app = Flask(__name__)
app.config.from_object("polarpipeline.config.Config")
socketio = SocketIO(app)
db = SQLAlchemy(app)

# idk what this is i followed a guide probably for database initialization or something idk
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    active = db.Column(db.Boolean(), default=True, nullable=False)

    def __init__(self, email):
        self.email = email

# docker database connection info
db_config = {
    'dbname': 'polarDB',
    'user': 'polarPL',
    'password': 'polarpswd',
    'host': 'db',
    'port': '5432',
}


def update_db(id, col, value):
# Used to update the database values.
#   id: file/row id. Generated in app.py.
#   col: column to update the value of
#   value: value to insert
#   returns: nothing. silence. probably not for the best.
    
    try:
        conn = psycopg2.connect(**db_config)
        query = "UPDATE progress SET {} = %s WHERE id = %s".format(col)
        with conn.cursor() as cursor:
            cursor.execute(query, (value, id))
        conn.commit()
    except Exception as e:
        print(f"Error updating the database: {e}")
        conn.rollback()
        cursor.close()


# path to config file, the one that configuration page gets its values from and updates
CONFIG_FILE_PATH = './polarpipeline/resources/config.ini'
# path to the figure generator's preset file. it just stores any presets that might have been saved
FIGURE_PRESETS_CONFIG = './polarpipeline/static/presets.ini'

base_path = '/mnt'
def alphabetize(item):
    return item.lower()

@app.route('/')
def home():
    return redirect(url_for('dashboard'))

# route for the pipeline file browser, populates the run options modal as well, see reportbrowse for more thorough description of filebrowser code
@app.route('/browse/<path:path>')
@app.route('/browse')
def browse(path=None):
    if path is None:
        path = base_path

    # builds what is shown in the browser, such as current path, the previous level's path, and the files to show
    full_path = os.path.join('/', path)
    directory_listing = {}
    for item in os.listdir(full_path):
        is_dir = False
        if os.path.isdir(os.path.join(full_path, item)):
            is_dir = True
        directory_listing[item] = is_dir
    up_level_path = os.path.dirname(path)
    
    # gets all necessary options for the job queueing, such as bed files, output directories, etc
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    outputs = []
    for output_path in config['Output']['output'].split(';'):
        outputs.append(output_path)
    ordered_directory = sorted(os.listdir(full_path), key=alphabetize)
    bed_files = os.listdir('./polarpipeline/resources/bed_files')
    gene_sources = os.listdir('./polarpipeline/resources/gene_source')
    clair_models = os.listdir('./polarpipeline/resources/clair_models')
    reference_files = []
    # removes placeholder files (for github) from options
    for item in bed_files:
        if item.startswith('.'):
            bed_files.remove(item)
    for item in gene_sources:
        if item.startswith('.'):
            gene_sources.remove(item)
    for item in clair_models:
        if item.startswith('.'):
            clair_models.remove(item)
    # removes reference index files from reference options
    for item in os.listdir('./polarpipeline/resources/reference_files'):
        if not item.endswith('.fai') and not item.endswith('.index') and not item.startswith('.'):
            reference_files.append(item)
    return render_template('index.html', current_path=full_path, directory_listing=directory_listing, ordered_directory=ordered_directory, up_level_path=up_level_path, bed_files=bed_files, gene_sources=gene_sources, clair_models = clair_models, reference_files = reference_files, outputs=outputs)

# encodes urls so that you can pass things that would normally break a browser through the url to the flask app (like /)
@app.template_filter('urlencode')
def urlencode_filter(s):
    return urllib.parse.quote(str(s))

# decodes above encoding
@app.template_filter('urldecode')
def urldecode_filter(s):
    return urllib.parse.unquote(s)

# the submit button on the job options modal takes you here
@app.route('/trigger_processing', methods=['POST'])
def trigger_processing():
    # just getting stuff from the frontend
    path = os.path.join('/usr/src/app/', request.json.get("path"))
    output_path = request.json.get("output_path")
    clair_model = request.json.get("clair")
    grch_reference = request.json.get("grch_reference")
    grch_bed = request.json.get("grch_bed")
    chm_reference = request.json.get("chm_reference")
    chm_bed = request.json.get("chm_bed")
    grch_gene = request.json.get("grch_gene")
    
    file_name = os.path.basename(path).split('.')[0]
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")

    # runs this if grch has been checked on the modal. if not, the javascript turns the reference into 'none'
    if grch_reference != 'none':
        # creates unique id by hashing the name and time
        concatenated_string = file_name + current_time
        id = hashlib.sha256(concatenated_string.encode()).hexdigest()
        try:
            # initializes database entry for the dashboard/info pages
            conn = psycopg2.connect(**db_config)
            query = "INSERT INTO progress (file_name, status, id, clair_model, bed_file, reference, gene_source) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            with conn.cursor() as cursor:
                cursor.execute(query, (file_name, 'waiting', id, clair_model, ', '.join(grch_bed), grch_reference, ', '.join(grch_gene)))
            conn.commit()
        except Exception as e:
            print(f"Error updating the database: {e}")
            conn.rollback()
        cursor.close()
        process.delay(path, output_path, clair_model, grch_gene, grch_bed, grch_reference, id)

    # runs this if t2t has been checked on the modal. if not, the javascript turns the reference into 'none'
    if chm_reference != 'none':
        file_name = file_name+'_T2T'
        # creates unique id by hashing the name and time
        concatenated_string = file_name + 'T2T' + current_time
        id = hashlib.sha256(concatenated_string.encode()).hexdigest()
        try:
            # initializes database entry for the dashboard/info pages
            conn = psycopg2.connect(**db_config)
            query = "INSERT INTO progress (file_name, status, id, clair_model, bed_file, reference, gene_source) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            with conn.cursor() as cursor:
                cursor.execute(query, (file_name, 'waiting', id, clair_model, ', '.join(chm_bed), chm_reference, 'N/A'))
            conn.commit()
        except Exception as e:
            print(f"Error updating the database: {e}")
            conn.rollback()
        cursor.close()
        processT2T.delay(path, output_path, clair_model, chm_bed, chm_reference, id)
        # print(path, clair_model, chm_reference, chm_bed)

    return redirect(url_for('dashboard'))


# upload files to the configuration page
# kind of a weird method of getting to this route. the + buttons on the configuration page call a function in the javascript that redirects to this route
@app.route('/upload/<string:filetype>', methods=['POST'])
def upload(filetype):
    # print('request:',request.files)
    print('filetype:',filetype)
    uploaded_file = request.files['file']
    file_name = uploaded_file.filename

    # Remove the file extension
    file_name_sans_extension = file_name.strip().split('/')[-1].split('.')[0]

    print('filename:',file_name)
    print('sans extension:',file_name_sans_extension)

    # Defines directory as 
    save_directory = os.path.join(f"/usr/src/app/polarpipeline/resources/", filetype)

    # Save the uploaded file inside the created directory
    uploaded_file.save(os.path.join(save_directory, file_name))

    # unzips the file if the one provided was zipped
    if file_name.endswith('.gz'):
        if 'tar' in file_name:
            subprocess.run(['tar', '-xf', os.path.join(save_directory, file_name)], cwd=save_directory)
        else:
            subprocess.run(['pigz', '-dk', os.path.join(save_directory, file_name)], cwd=save_directory)
        subprocess.run(['rm', os.path.join(save_directory, file_name)], cwd=save_directory)
    elif file_name.endswith('.zip'):
        with zipfile.ZipFile(os.path.join(save_directory, file_name), 'r') as zip_ref:
            zip_ref.extractall(save_directory)
        subprocess.run(['rm', os.path.join(save_directory, file_name)], cwd=save_directory)
    return redirect(url_for('configuration'))

# route to remove any configurations that have been added
# accessed by the x buttons that appear when clicking edit on any section in the configuration
@app.route('/remove/<path:removepath>')
def remove(removepath):
    # print(removepath)
    base = './polarpipeline/resources'
    full_path = os.path.join(base, removepath)
    # this checks to see if the configuration to remove is a file or a directory, and removes accordingly
    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
    elif os.path.isfile(full_path):
        os.remove(full_path)
    return redirect(url_for('configuration'))

@app.route('/exportProgress')
def exportprogress():
    try:
        # Connect to the database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Execute your query
        cursor.execute("SELECT * FROM progress")
        rows = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        # Write the data to a CSV file
        formattedTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not os.path.isdir('/tmp/pipeline_export'):
            os.mkdir('/tmp/pipeline_export')
        for file in os.listdir('/tmp/pipeline_export'):
            os.remove(os.path.join('/tmp/pipeline_export', file))
        export_file = f'/tmp/pipeline_export/{formattedTime}_pipeline_history.csv'
        with open(export_file, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile)
            csvwriter.writerow(column_names)  # Write the header
            csvwriter.writerows(rows)  # Write the data

        # Close the database connection
        cursor.close()
        conn.close()

        # Send the file to the client
        return send_file(export_file, as_attachment=True)
    except Exception as e:
        conn.rollback()
        return f"Error: {e}"
    
@app.route('/importProgress', methods=['POST'])
def importprogress():
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({"error": "No file part in the request"}), 400

        file = request.files['file']

        # If the user does not select a file, the browser may submit an empty part without filename
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400

        # Save the file to the /tmp/pipeline_export directory
        file_path = os.path.join('/tmp/pipeline_export', file.filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)

        # Connect to the database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Use COPY FROM to import data from the CSV file
        with open(file_path, 'r') as f:
            cursor.copy_expert("COPY progress FROM STDIN WITH CSV HEADER", f)

        # Commit the transaction
        conn.commit()

        # Close the database connection
        cursor.close()
        conn.close()

        return jsonify({"message": "Data imported successfully."}), 200

    except Exception as e:
        if conn and not conn.closed:
            conn.rollback()
        return jsonify({"error": str(e)}), 500


# route for the dashboard
@app.route('/dashboard')
@app.route('/dashboard/')
@app.route('/dashboard/<int:page>')
def dashboard(page=0):
    try:
        if page < 0: page = 0 # just in case
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # get all of the runs to display on the main page, ordered by recency
        cursor.execute("SELECT file_name, status, id FROM progress ORDER BY start_time")
        rawrows = cursor.fetchall()
        reverserawrows = rawrows[::-1]

        # get the average runtime per computer for graphing
        cursor.execute("SELECT computer, AVG(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600) AS avg_runtime_seconds FROM progress WHERE status = 'complete' GROUP BY computer;")
        timings = cursor.fetchall()
        formatted_timings = [{
            'computer': row[0],
            'runtime': row[1]
        } for row in timings]
        formatted_data_json = json.dumps(formatted_timings)

        # get how many of each reference have been run for more graphing
        cursor.execute("SELECT reference, COUNT(*) AS instances FROM progress WHERE status = 'complete' GROUP BY reference;")
        reference_counts = cursor.fetchall()
        formatted_references = [{
            'reference': row[0],
            'count': row[1]
        } for row in reference_counts]
        formatted_reference_counts = json.dumps(formatted_references)

        # get average runtime per computer per reference for even more graphing
        cursor.execute("""
            SELECT computer, reference, AVG(EXTRACT(EPOCH FROM (end_time - start_time)) / 3600) AS avg_runtime_hours 
            FROM progress 
            WHERE status = 'complete' 
            GROUP BY computer, reference
        """)
        ref_timings = cursor.fetchall()
        ref_formatted_timings = [{
            'computer': row[0],
            'reference': row[1],
            'runtime': row[2]
        } for row in ref_timings]
        ref_formatted_data_json = json.dumps(ref_formatted_timings)
        # print(ref_formatted_data_json)

        # get the worker statuses from the database (this gets updated by the status container)
        cursor.execute("SELECT * FROM status;")
        statusList = cursor.fetchall()
        status = []
        for item in statusList:
            status.append(item[0] + ': ' + item[1])

        # calculate the total number of pages based on the total number of rows and rows per page
        totalpages = (len(reverserawrows)//14) + int(bool(len(reverserawrows)%14))
        print(totalpages)
        if page*14 >= len(reverserawrows):
            page = 0
        rowstart = page*14
        rowend = min(rowstart+14, len(rawrows))
        rowselection = reverserawrows[rowstart:rowend]
        rows = rowselection[::-1]

        cursor.close()
        conn.close()

        # return page with all collected data
        return render_template('dashboard.html', rows=rows, status=status, currpage=page+1, totalpages=totalpages, formatted_data=formatted_data_json, reference_counts=formatted_reference_counts, ref_timings=ref_formatted_data_json)
        # return render_template('dashboard.html', rows = rows)
    except Exception as e:
        conn.rollback()
        return f"Error: {e}"

# there are times (like if a worker is shut down while there are things in queue) where things will be abandoned in the queue, this just clears all of them.
# this only deals with the database, so if they still exist unconsumed in the broker, they can still be picked up even if their database entry is gone
# accessed by the clear button under the queue on dashboard
@app.route('/clear_queue')
def clear_queue():
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM progress WHERE status = %s", ('waiting',))
        conn.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        cursor.rollback()
        return f"Error: {e}"

# remove entry from database. accessed by the delete buttons that are shown when clicking edit on dashboard
@app.route('/deleteRun/<string:id>')
def deleteRun(id):
    conn = psycopg2.connect(**db_config)
    try:
        query = f"DELETE FROM progress WHERE id = '{id}'"
        with conn.cursor() as cursor:
            cursor.execute(query)
        conn.commit()
    except Exception as e:
        print(f"Error updating the database: {e}")
        conn.rollback()
    finally:
        conn.close()
    return redirect(url_for('dashboard'))

# Functions to read the config.ini file and return the configuration values as a dictionary for given computer_name
def read_config(computer_name=None):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)

    if computer_name is None or computer_name not in config.sections():
        computer_name = 'Default'

    return parse_config_dict(config[computer_name])

def parse_config_dict(config_dict):
    parsed_dict = {}
    for key, value in config_dict.items():
        key = key
        value = value

        parsed_dict[key] = value

    return parsed_dict

# Function to save the updated configurations to the config.ini file
def save_config(computer_name, config_values):
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)

    if not config.has_section(computer_name):
        config.add_section(computer_name)

    for key, value in config_values.items():
        value = str(value)  # Convert other data types to strings

        config.set(computer_name, key, value)

    with open(CONFIG_FILE_PATH, 'w') as configfile:
        config.write(configfile)

# returns all configurations in the config.ini for all "computer_names"
def get_all_configurations():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    all_configurations = {}
    for section_name in config.sections():
        all_configurations[section_name] = parse_config_dict(config[section_name])
    return all_configurations

# ID generator page route
@app.route('/id')
def id():
    all_configurations = get_all_configurations()
    pattern = str(all_configurations['ID']['encode']).split(',')
    static = str(all_configurations['ID']['static'])
    return render_template('id.html', pattern=pattern, static=static)

# route to save the specified configuration
# accessed through the 'save' button in the 'Define Pattern' modal
# Patterns are saved in an array, where the order of the encoded ID is stored in the same line as the static/omitted values separated by '|'.
@app.route('/save_pattern', methods=['POST'])
def save_pattern():
    data = request.get_json()
    # retrieve the encode positions as well as the static/omitted numbers
    encode = data.get('encode')
    static = data.get('static')
    # print(static)
    # when the input for static/omitted numbers goes away (when there are none) it still technically has one left, so this handles the case so
    # a static number is not stored when there should not be one
    omit = encode.index('|')
    if not len(encode[omit+1:]):
        static = []
    # print(encode, static, sep='\n')
    # error case, if the number of static/omitted positions do not match the number of provided numbers, returns error
    if not len(encode[omit+1:]) == len(static):
        return 'lengths'
    omitted = encode[omit+1:]
    # error case, checks that all omitted numbers are adjacent to each other, returns error if they are not
    for i in omitted:
        if len(omitted) > int(i):
            # print(str(int(i)+int(omitted[0])), omitted[int(i)])
            if not str(int(i)+int(omitted[0])) == omitted[int(i)]:
                print(i, omitted[int(i)])
                return "adjacent"
    #  error case, checks that there are actually positions to encode, if not returns error
    if len(encode[:omit]) == 0:
        return "nopositions"
    # error case checks if there are any omitted positions that do not have a provided value, returns error if there are
    if "" in static:
        return "emptyomission"

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)

    config.set('ID', 'encode', ','.join(encode))
    config.set('ID', 'static', ''.join(static))

    # Write changes back to the configuration file
    with open(CONFIG_FILE_PATH, 'w') as configfile:
        config.write(configfile)

    return 'success'

# route to actually do the encoding/decoding of the ID
# accessed by the convert button on the ID generator page
@app.route('/id_coding', methods=['POST'])
def id_coding():
    data = request.get_json()
    input_string = data.get('input')
    # if there is no inputtype in the request, handle it since this will be the case when the encode/decode specification is uneccessary
    try:
        input_type = data.get('inputtype')
    except:
        input_type = ''
    # retreive the encoding and static values from the config.ini
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    config_pattern = config['ID']['encode'].split(',')
    omission = config['ID']['static']
    separator_index = config_pattern.index('|')
    encode_pattern = config_pattern[:separator_index]
    omission_pattern = config_pattern[separator_index + 1:]
    # print(encode_pattern, omission_pattern)
    # if the inputted string is not possible to encode or decode, return an error 
    if len(input_string) not in [len(encode_pattern + omission_pattern), len(encode_pattern)]:
        return 'length'
    # this is the expected case, if there are no omitted positions, it cannot be known from input alone whether the user wants to encode or decode, so it will send a response requesting
    # further clarification. in the javascript, this response will prompt a modal to appear that asks the user whether they want to encode or decode, which will reaccess this route with the input_type set
    elif omission_pattern == [] and not input_type:
        return 'specify'
    else:
        # decides whether the user wants to encode or decode based on length of input
        if not input_type:
            if len(input_string) > len(encode_pattern):
                input_type = 'encode'
            elif len(encode_pattern) == len(input_string):
                input_type = 'decode'
        if not input_type:
            return 'failure'
        # handles each case appropriately, encoding or decoding and returning the output
        match input_type:
            case 'encode':
                # print('encode')
                return id_encode(input_string, encode_pattern)
            case 'decode':
                # print('decode')
                return id_decode(input_string, encode_pattern, omission_pattern, omission)
        return 'failure'
    
# function to encode the input using the config.ini encoding pattern. straightforward
def id_encode(input_string, encode_pattern):
    print(input_string, encode_pattern)
    output = ''
    for index in encode_pattern:
        output += input_string[int(index)-1]
    return output

# decodes using the config.ini encoding pattern. less straightforward, but still is. just does the encoding in reverse essentially
def id_decode(input_string, encode_pattern, omission_pattern, omission):
    output = ''
    intended_pos = {}
    for i, char in enumerate(encode_pattern):
        intended_pos[int(char)] = input_string[i]
    for i, char in enumerate(omission_pattern):
        intended_pos[int(char)] = omission[i]
    # print(intended_pos)
    for i in range(len(encode_pattern + omission_pattern)):
        output += intended_pos[i+1]
    return output

# route to add a new worker configuration (threads and sudo password)
# accessed by the + button by the worker configuration header on the configuration page
@app.route('/add_computer', methods=['POST'])
def add_computer():
    if request.method == 'POST':
        computer_name = request.form['computer_name']

        # Read the default configuration
        default_config_values = read_config()

        # Create a new section in the config for the new computer and copy the default configurations
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_PATH)
        if not config.has_section(computer_name):
            config.add_section(computer_name)
            for key, value in default_config_values.items():
                config.set(computer_name, str(key), str(value))

            # Save the updated config.ini file
            with open(CONFIG_FILE_PATH, 'w') as configfile:
                config.write(configfile)

        # Save the default values for the new computer
        save_config(computer_name, default_config_values)

    return redirect(url_for('configuration'))

# route to save a worker configuration after making a change
# accessed by the save button in any dropdown section
@app.route('/save_configuration', methods=['POST'])
def save_configuration():
    computer_name = request.form['computer_name']
    config_values = {}

    # iterates through the keys in the request that will be saved
    for key in request.form:
        print(key)
        if key != 'computer_name':
            value = request.form[key]
            print(value)
            if value.lower() == 'true':
                value = True
            elif value.lower() == 'false':
                value = False
            else:
                try:
                    value = int(value)
                except ValueError:
                    pass  # Keep the value as a string

            config_values[key] = value

    # runs function to save the section
    save_config(computer_name, config_values)

    return 'success'

# route to remove a worker configuration
# accessed from the delete button in the worker configuration dropdowns
@app.route('/delete_configuration', methods=['POST'])
def delete_configuration():
    if request.method == 'POST':
        computer_name = request.form['computer_name']

        # Read the config file
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_PATH)

        # Check if the configuration exists
        if config.has_section(computer_name):
            # Remove the configuration section
            config.remove_section(computer_name)

            # Save the updated config.ini file
            with open(CONFIG_FILE_PATH, 'w') as configfile:
                config.write(configfile)

    return redirect(url_for('configuration'))

# route for the configuration page
@app.route('/configuration')
def configuration():
    # loads all the dropdown configurations
    all_configurations = get_all_configurations()
    # print(all_configurations)
    
    # creates the arrays for all types of uploadable options
    clair_models = []
    bed_files = []
    gene_sources = []
    reference_files = []

    # populates said uploadable options
    bed_files = os.listdir('./polarpipeline/resources/bed_files')
    gene_sources = os.listdir('./polarpipeline/resources/gene_source')
    clair_models = os.listdir('./polarpipeline/resources/clair_models')
    reference_files = os.listdir('./polarpipeline/resources/reference_files')
    
    return render_template('configuration.html', all_configurations=all_configurations, clair_models=clair_models, bed_files=bed_files, gene_sources=gene_sources, reference_files=reference_files)

# loads the figure generator page (simple wow)
@app.route('/figuregenerator')
def figuregenerator():
    return render_template('figuregenerator.html')

# takes in a dictionary of values to save to the presets file for later use in the figure generator
def save_preset(preset_name, preset_vals):
    config = configparser.ConfigParser()
    config.read(FIGURE_PRESETS_CONFIG)

    if not config.has_section(preset_name):
        config.add_section(preset_name)

    for key, value in preset_vals.items():
        value = str(value)  # Convert other data types to strings

        config.set(preset_name, key, value)

    with open(FIGURE_PRESETS_CONFIG, 'w') as configfile:
        config.write(configfile)

# the route to save the preset
# accessed from the save preset button on the figure generator page
@app.route('/saveState', methods=['POST'])
def saveState():
    # retrieves all universal fields (ones that are used regardless of whether it is homozygous or not)
    preset_name = request.json.get("presetname")
    homo = request.json.get("homo")
    abproteinname = request.json.get("abproteinname")
    proteinname = request.json.get("proteinname")
    # retrieves fields that are only present when homozygous
    if homo == True:
        homolen = request.json.get("homolen")
        homostructures = request.json.get("homostructures")
        homofeatures = request.json.get("homofeatures")

        preset_vals = {
            "homo": homo,
            "abproteinname": abproteinname,
            "proteinname": proteinname,
            "homolen": homolen,
            "homostructures": homostructures,
            "homofeatures": homofeatures
        }
    # retrieves fields that are only present when heterozygous
    else:
        leftlen = request.json.get("leftlen")
        leftstructures = request.json.get("leftstructures")
        rightlen = request.json.get("rightlen")
        rightstructures = request.json.get("rightstructures")
        leftfeatures = request.json.get("leftfeatures")
        rightfeatures = request.json.get("rightfeatures")

        preset_vals = {
            "homo": homo,
            "abproteinname": abproteinname,
            "proteinname": proteinname,
            "leftlen": leftlen,
            "leftstructures": leftstructures,
            "rightlen": rightlen,
            "rightstructures": rightstructures,
            "leftfeatures": leftfeatures,
            "rightfeatures": rightfeatures
        }

    # saves preset using all retrieved fields
    save_preset(str(preset_name), preset_vals)

    response_data = {
        "message": "Data received successfully"
    }

    return jsonify(response_data)

# function to retrieve all presets in the presets.ini file
def load_presets():
    config = configparser.ConfigParser()
    config.read(FIGURE_PRESETS_CONFIG)
    return config.sections()

# route to load all presets
# accessed from the load preset button at the top of the figure generator page. loads upon clicking the button
@app.route('/loadStates', methods=['POST'])
def loadStates():
    presets = load_presets()
    response_data = {
        "data": presets
    }

    return jsonify(response_data)
    
# function to actually return the values of a given preset
def load_preset(section_name):
    config = configparser.ConfigParser()
    config.read(FIGURE_PRESETS_CONFIG)
    if section_name in config:
        return parse_config_dict(config[section_name])
    else:
        return None  # Section not found

# helper function to convert the data in the preset.ini into a dictionary
def parse_config_dict(config_section):
    parsed_data = {}
    for key, value in config_section.items():
        try:
            # Attempt to evaluate the value as literal Python expression
            parsed_value = ast.literal_eval(value)
            if isinstance(parsed_value, list):
                parsed_data[key] = parsed_value
            else:
                parsed_data[key] = parsed_value
        except (SyntaxError, ValueError):
            # If evaluation fails, store the value as is
            parsed_data[key] = value
    return parsed_data

# route to begin loading a saved preset
# accessed by the load preset button on the load preset modal (the one with the dropdown of presets)
@app.route('/loadState', methods=['POST'])
def loadState():
    preset = request.json.get('preset')

    preset_data = load_preset(preset)
    print(preset_data)

    response_data = {
        "data": preset_data
    }

    return jsonify(response_data)

# key for sorting features (i don't remember what this is for)
def customsortfeatures(feature):
    num = -int(feature[1])
    return num

# the meaty function to actually make the figure svg
# accessed by clicking generate on the figure generator page
@app.route('/generatefigure', methods=['POST'])
def generatefigure():
    # retrieve fields
    homo = request.json.get("homo")
    abproteinname = request.json.get("abproteinname")
    proteinname = request.json.get("proteinname")

    # i think this was for debugging, finds and prints the directory of the svg so i knew where it was going
    for root, dirs, files in os.walk('/usr/src/app'):
        for file in files:
            if file == 'variantFig.svg':
                print(os.path.join(root, file))

    # initializes the layers of the figure so that they are layered on top of each other correctly (you want labels to go on top of boxes etc)
    topbar = []
    bottombar = []
    leftfeatureelements = []
    rightfeatureelements = []
    homobar = []
    homofeatureelements = []

    # makes the background of the image
    bg = [
        svg.Rect( # BACKGROUND
            fill="white",
            x=0,
            y=0,
            width=480*2,
            height=480
        ),
        svg.Text( # PROTEIN NAME
            text=f'{abproteinname} | {proteinname}',
            x=5,
            y=45,
            fill="black",
            font_family="Sans,Arial",
            font_weight="bold",
            font_size="30",
            font_stretch="ultra-condensed"
        ),
    ]

    base = []
    # if the protein is heterozygous
    if not homo:
        # retrieves the features for a heterozygous protein
        leftlen = request.json.get("leftlen")
        leftstructures = request.json.get("leftstructures")
        rightlen = request.json.get("rightlen")
        rightstructures = request.json.get("rightstructures")
        leftfeatures = request.json.get("leftfeatures")
        rightfeatures = request.json.get("rightfeatures")

        maxlen = max(int(leftlen), int(rightlen))

        base.append(svg.Line( # FIRST LINE
            stroke_width=5,
            stroke="grey",
            x1=50,
            y1=200,
            x2=50+((int(leftlen)/maxlen) * 550) + ((1/maxlen) * 550),
            y2=200
        ))
        base.append(svg.Line( # SECOND LINE
            stroke_width=5,
            stroke="grey",
            x1=50,
            y1=360,
            x2=50+((int(rightlen)/maxlen) * 550) + ((1/maxlen) * 550),
            y2=360
        ))
        base.append(svg.Text( # 0|1 TEXT
            text='0|1',
            x=5,
            y=205,
            fill="black",
            font_family="monospace",
            stroke_width=1,
            font_size=20
        ))
        base.append(svg.Text( # 1|0 TEXT
            text='1|0',
            x=5,
            y=365,
            fill="black",
            font_family="monospace",
            stroke_width=1,
            font_size=20
        ))
        base.append(svg.Text( # TOP AA LENGTH
            text=f'{leftlen} AA',
            x=50+((int(leftlen)/maxlen) * 550) + ((1/maxlen) * 550) + 10,
            y=205,
            fill="black",
            font_family="monospace",
            stroke_width=1,
            font_size=20
        ))
        base.append(svg.Text( # BOTTOM AA LENGTH
            text=f'{rightlen} AA',
            x=50+((int(rightlen)/maxlen) * 550) + ((1/maxlen) * 550) + 10,
            y=365,
            fill="black",
            font_family="monospace",
            stroke_width=1,
            font_size=20
        ))
        # makes the left structures for the heterozygous protein
        for item in leftstructures:
            if len(item) != 4: continue
            fontsize = 20
            if (len(item[0]) * fontsize * (3/5)) > (((int(item[2])-int(item[1]))/maxlen)*550):
                fontsize = (((((int(item[2])-int(item[1]))/maxlen)*550) * 0.9) / (3/5)) / len(item[0])
            topbar.append(
                svg.Rect(
                    fill=item[3],
                    x=50+((int(item[1])/maxlen)*550),
                    y=185,
                    width=(((int(item[2])-int(item[1]))/maxlen)*550),
                    height=30,
                )
            )
            fontcol = "black"
            if item[0] == "DEGEN": fontcol="red"
            print(50+((int(item[1])+int(item[2]))/2))
            topbar.append(
                svg.Text(
                    text=item[0],
                    x=50+((((int(item[1])+int(item[2]))/2)/maxlen)*550)-(fontsize*(3/5)*len(item[0])/2),
                    y=205,
                    fill=fontcol,
                    font_family="monospace",
                    font_size=fontsize
                )
            )
        # makes the right structures for the heterozygous protein
        for item in rightstructures:
            if len(item) != 4: continue
            fontsize = 20
            if (len(item[0]) * fontsize * (3/5)) > (((int(item[2])-int(item[1]))/maxlen)*550):
                fontsize = (((((int(item[2])-int(item[1]))/maxlen)*550) * 0.9) / (3/5)) / len(item[0])
            bottombar.append(
                svg.Rect(
                    fill=item[3],
                    x=50+((int(item[1])/maxlen)*550),
                    y=345,
                    width=(((int(item[2])-int(item[1]))/maxlen)*550),
                    height=30,
                )
            )
            fontcol = "black"
            if item[0] == "DEGEN": fontcol="red"
            bottombar.append(
                svg.Text(
                    text=item[0],
                    x=50+((((int(item[1])+int(item[2]))/2)/maxlen)*550)-(fontsize*(3/5)*len(item[0])/2),
                    y=365,
                    fill=fontcol,
                    font_family="monospace",
                    font_size=fontsize
                )
            )
        # i attempted to make this in such a way that it would detect overlap in feature names, but it did not work for some reason so now it just counts the instances of '^' and raises it that many rows
        # the sorting key was for this, because it would let me iterate through the features right to left raising the level if there was overlap
        leftfeaturestemp = sorted([x for x in leftfeatures if x], key=customsortfeatures)
        leftfeatureswithoverlap = []
        for i in range(len(leftfeaturestemp)):
            height = 0
            if '^' in leftfeaturestemp[i][0]:
                height = (len(leftfeaturestemp[i][0].split('^'))-1)*30
            leftfeatureswithoverlap.append(leftfeaturestemp[i]+[height])
            print(leftfeatureswithoverlap)
        for item in leftfeatureswithoverlap:
            leftfeatureelements.append(
                svg.Line(
                    stroke_width=3,
                    stroke="red",
                    x1=50+((int(item[1])/maxlen) * 550),
                    y1=200,
                    x2=50+((int(item[1])/maxlen) * 550),
                    y2=155-item[2]
                )
            )
            leftfeatureelements.append(
                svg.Text(
                    text=item[0].replace('^', ''),
                    x=50 + ((int(item[1]) / maxlen) * 550) + 6,
                    y=170-item[2],
                    font_family="monospace",
                    font_size=20
                )
            )
        # same story as the left features with the autodetection and such but for the right
        rightfeaturestemp = sorted([x for x in rightfeatures if x], key=customsortfeatures)
        rightfeatureswithoverlap = []
        for i in range(len(rightfeaturestemp)):
            height = 0
            if '^' in rightfeaturestemp[i][0]:
                height = (len(rightfeaturestemp[i][0].split('^'))-1)*30
            rightfeatureswithoverlap.append(rightfeaturestemp[i]+[height])
            print(rightfeatureswithoverlap)
        for item in rightfeatureswithoverlap:
            rightfeatureelements.append(
                svg.Line(
                    stroke_width=3,
                    stroke="red",
                    x1=50+((int(item[1])/maxlen) * 550),
                    y1=360,
                    x2=50+((int(item[1])/maxlen) * 550),
                    y2=315-item[2]
                )
            )
            rightfeatureelements.append(
                svg.Text(
                    text=item[0].replace('^', ''),
                    x=50 + ((int(item[1]) / maxlen) * 550) + 6,
                    y=330-item[2],
                    font_family="monospace",
                    font_size=20
                )
            )
    # if the protein is homozygous
    else:
        # retrieves the features for a homozygous protein
        homolen = request.json.get("homolen")
        homostructures = request.json.get("homostructures")
        homofeatures = request.json.get("homofeatures")

        base.append(svg.Line( # SECOND LINE
            stroke_width=5,
            stroke="grey",
            x1=50,
            y1=280,
            x2=50+((int(homolen)/int(homolen)) * 550) + ((1/int(homolen)) * 550),
            y2=280
        ))
        base.append(svg.Text( # 1|1 TEXT
            text='1|1',
            x=5,
            y=285,
            fill="black",
            font_family="monospace",
            stroke_width=1,
            font_size=20
        ))
        base.append(svg.Text( # TOP AA LENGTH
            text=f'{homolen} AA',
            x=50+((int(homolen)/int(homolen)) * 550) + ((1/int(homolen)) * 550) + 10,
            y=285,
            fill="black",
            font_family="monospace",
            stroke_width=1,
            font_size=20
        ))
        # makes the structures for a homozygous protein
        for item in homostructures:
            if len(item) != 4: continue
            fontsize = 20
            if (len(item[0]) * fontsize * (3/5)) > (((int(item[2])-int(item[1]))/int(homolen))*550):
                fontsize = (((((int(item[2])-int(item[1]))/int(homolen))*550) * 0.9) / (3/5)) / len(item[0])
            homobar.append(
                svg.Rect(
                    fill=item[3],
                    x=50+((int(item[1])/int(homolen))*550),
                    y=265,
                    width=(((int(item[2])-int(item[1]))/int(homolen))*550),
                    height=30,
                )
            )
            fontcol = "black"
            if item[0] == "DEGEN": fontcol="red"
            homobar.append(
                svg.Text(
                    text=item[0],
                    x=50+((((int(item[1])+int(item[2]))/2)/int(homolen))*550)-(fontsize*(3/5)*len(item[0])/2),
                    y=285,
                    fill=fontcol,
                    font_family="monospace",
                    font_size=fontsize
                )
            )
        # makes the features for a homozygous protein. once again attempted to sort them for the purpose of raising, now just counts the '^' to determine feature height
        homofeaturestemp = sorted([x for x in homofeatures if x], key=customsortfeatures)
        homofeatureswithoverlap = []
        for i in range(len(homofeaturestemp)):
            height = 0
            if '^' in homofeaturestemp[i][0]:
                height = (len(homofeaturestemp[i][0].split('^'))-1)*30
            homofeatureswithoverlap.append(homofeaturestemp[i]+[height])
            print(homofeatureswithoverlap)
        for item in homofeatureswithoverlap:
            homofeatureelements.append(
                svg.Line(
                    stroke_width=3,
                    stroke="red",
                    x1=50+((int(item[1])/int(homolen)) * 550),
                    y1=280,
                    x2=50+((int(item[1])/int(homolen)) * 550),
                    y2=235-item[2]
                )
            )
            homofeatureelements.append(
                svg.Text(
                    text=item[0],
                    x=50 + ((int(item[1]) / int(homolen)) * 550) + 6,
                    y=250-item[2],
                    font_family="monospace",
                    font_size=20
                )
            )

        # print(homolen)
        # print(homostructures)
        # print(homofeatures)

    # uses the library to make the svg class wow
    canvas = svg.SVG(
        width=480*2,
        height=480,
        # these are the layers i was talking about you can see how things go bottom (left) to top (right)
        elements = bg + leftfeatureelements + rightfeatureelements + homofeatureelements + base + topbar + bottombar + homobar
    )

    # converts the class to a string
    svg_string = str(canvas)

    # writes the svg to a file
    with open('/usr/src/app/polarpipeline/static/variantFig.svg', 'w') as opened:
        opened.write(svg_string)
    
    response_data = {
        "message": "Data received successfully"
    }
    # returns reponse, which updates the page with the new figure
    return jsonify(response_data)

# route to download the figure
# accessed by the download button beneath the figure on the figure generator page
@app.route('/downloadfigure')
def downloadfigure():
    try:
        image_path = f'/usr/src/app/polarpipeline/static/variantFig.svg'
        return send_file(image_path, as_attachment=True)
    except FileNotFoundError:
        return "Image not found", 404

# route to the setup page (not even javascript, simplest page by far)
@app.route('/setup')
def setup():
 return render_template('setup.html')

# route to load the info page for the run with the given ID
# accessed by any info button on the dashboard
@app.route('/info/<string:id>')
def info(id):
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # gets all columns from the row with the same ID
        cursor.execute("SELECT * FROM progress WHERE id = %s", (id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        # parses the row, finding out the times based on the presence of start and end times
        if row[3]:
            runtime = str(row[3] - row[1])
            runtime = runtime.split('.')[0]
            startTime = str(row[1])
            startTime = startTime.split('.')[0]
            endTime = str(row[3])
            endTime = endTime.split('.')[0]
        elif row[1]:
            runtime = str(datetime.now() - row[1])
            runtime = runtime.split('.')[0]
            startTime = str(row[1])
            startTime = startTime.split('.')[0]
            endTime = 'N/A'
        else:
            runtime = 'N/A'
            startTime = 'N/A'
            endTime = 'N/A'
        
        file_name = row[0]
        status = str(row[2])
        computer = str(row[4])

        # folder_list = os.listdir('/home/threadripper/shared_storage/workspace')
        # if the run is complete, there will be a run_summary file generated by the worker. this will find that file so it can be displayed
        statsPath = ''
        for path in config['Output']['output'].split(';'):
            if os.path.isfile(os.path.join(path, startTime.replace(' ', '_').replace(':', '-')+'_'+file_name, '0_nextflow/run_summary.txt')):
                statsPath = os.path.join(path, startTime.replace(' ', '_').replace(':', '-')+'_'+file_name, '0_nextflow/run_summary.txt')

        # loads the run summary file if it exists
        # statsPath = os.path.join(config['Output']['output'], startTime.replace(' ', '_').replace(':', '-')+'_'+file_name, '0_nextflow/run_summary.txt')
        if os.path.isfile(statsPath):
            rows = []
            for line in open(statsPath, 'r'):
                splitline = line.split('\t')
                rows.append([splitline[0], splitline[1]])
        else:
            rows = []
        
        # loads the rest of the info from the database
        clair_model = row[7]
        bed_file = row[8].split(',')
        reference = row[9]
        gene_source = row[10]
        if gene_source == 'N/A':
            gene_source = []
            for item in bed_file:
                gene_source.append('N/A')
        else:
            gene_source = row[10].split(',')
        
        return render_template('info.html', file_name = file_name, startTime = startTime, endTime = endTime, status = status, runtime=runtime, computer=computer, id=id, rows=rows, clair_model=clair_model, bed_file=bed_file, reference=reference, gene_source=gene_source)
    except Exception as e:
        return f"Error: {e}"

# retrieves the info that gets updated live (the time, current step, etc)
# is accessed once per second by the info page inherently
@app.route('/get_info/<string:id>')
def get_info(id):
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM progress WHERE id = %s", (id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        # same logic as the inital info page loading for finding the time
        if row[3]:
            runtime = str(row[3] - row[1])
            runtime = runtime.split('.')[0]
            startTime = str(row[1])
            startTime = startTime.split('.')[0]
            endTime = str(row[3])
            endTime = endTime.split('.')[0]
        elif row[1]:
            runtime = str(datetime.now() - row[1])
            runtime = runtime.split('.')[0]
            startTime = str(row[1])
            startTime = startTime.split('.')[0]
            endTime = 'N/A'
        else:
            runtime = 'N/A'
            startTime = 'N/A'
            endTime = 'N/A'

        status = str(row[2])
        computer = str(row[4])

        print(datetime.now())

        # builds dict for the response
        info = {
            "startTime": startTime,
            "endTime": endTime,
            "runtime": runtime,
            "status": status,
            "computer": computer
        }

        return jsonify(info)
    except Exception as e:
        return str(e)

# opens a socket with a log file as the output. this lets the info page display the terminal output from the respective worker if the worker is outputting the log to a file
@socketio.on('request_file')
def handle_request_file(worker_name):
    alreadyprocessed = ''
    file_path = f'{worker_name}.log'
    event_name = f'log_{worker_name}'

    with open(f'/usr/src/app/polarpipeline/resources/{file_path}', 'r', buffering=1) as file:

        # line = file.readline()
        # while line:
        #     if not "process > " in line and not line.startswith("executor >  local") and not line.startswith('WARN:') and not line.startswith("\n"):
        #         alreadyprocessed += line
        #     line = file.readline()

        # socketio.emit(event_name, alreadyprocessed)
        while True:
            line = file.readline()
            if not line:
                socketio.sleep(0.1)
                continue
            # this if blocks all the repetitive lines that get spammed like the nextflow pipeline output as well as the vep warning lines
            if not "process > " in line and not line.startswith("executor >  local") and not 'WARN' in line and not line.startswith("\n") and not line.startswith('merging:') and not line.startswith('Use of uninitialized value $aa_string') and not line.startswith('Argument "4:5UTR') and not line.startswith('Use of uni'):
                socketio.emit(event_name, line)

# route that cancels a job by setting the signal to stop in the database. worker should periodically check this and if the signal is set to cancelled it should stop
# accessed by the cancelled button on the info page for any job that is running
@app.route('/abort/<string:id>')
def abort(id):
    update_db(id, 'signal', 'stop')
    update_db(id, 'status', 'cancelling')
    time.sleep(1)
    return redirect(url_for('dashboard'))

# dict used by the report function to convert codons to acid(?) names
def aminoacid(codon):
    codon = codon.lower()
    match codon:
        case 'ggg': return 'glycine'
        case 'gga': return 'glycine'
        case 'ggc': return 'glycine'
        case 'ggt': return 'glycine'
        case 'gag': return 'glutamate'
        case 'gaa': return 'glutamate'
        case 'gac': return 'aspartate'
        case 'gat': return 'aspartate'
        case 'gcg': return 'alanine'
        case 'gca': return 'alanine'
        case 'gcc': return 'alanine'
        case 'gct': return 'alanine'
        case 'gtg': return 'valine'
        case 'gta': return 'valine'
        case 'gtc': return 'valine'
        case 'gtt': return 'valine'
        case 'tgg': return 'tryptophan'
        case 'tga': return 'stop'
        case 'tgc': return 'cysteine'
        case 'tgt': return 'cysteine'
        case 'tag': return 'stop'
        case 'taa': return 'stop'
        case 'tac': return 'tyrosine'
        case 'tat': return 'tyrosine'
        case 'tcg': return 'serine'
        case 'tca': return 'serine'
        case 'tcc': return 'serine'
        case 'tct': return 'serine'
        case 'ttg': return 'leucine'
        case 'tta': return 'leucine'
        case 'ttc': return 'phenylalanine'
        case 'ttt': return 'phenylalanine'
        case 'agg': return 'arginine'
        case 'aga': return 'arginine'
        case 'agc': return 'serine'
        case 'agt': return 'serine'
        case 'aag': return 'lysine'
        case 'aaa': return 'lysine'
        case 'aac': return 'asparagine'
        case 'aat': return 'asparagine'
        case 'acg': return 'threonine'
        case 'aca': return 'threonine'
        case 'acc': return 'threonine'
        case 'act': return 'threonine'
        case 'atg': return 'methionine'
        case 'ata': return 'isoleucine'
        case 'atc': return 'isoleucine'
        case 'att': return 'isoleucine'
        case 'cgg': return 'arginine'
        case 'cga': return 'arginine'
        case 'cgc': return 'arginine'
        case 'cgt': return 'arginine'
        case 'cag': return 'glutamine'
        case 'caa': return 'glutamine'
        case 'cac': return 'histidine'
        case 'cat': return 'histidine'
        case 'ccg': return 'proline'
        case 'cca': return 'proline'
        case 'ccc': return 'proline'
        case 'cct': return 'proline'
        case 'ctg': return 'leucine'
        case 'cta': return 'leucine'
        case 'ctc': return 'leucine'
        case 'ctt': return 'leucine'
        case default:
            return codon

# properties of acids to see if they can be classified as having similar properties 
aminoacid_properties = {
    'alanine': 'hydrophobic',
    'arginine': 'positive',
    'asparagine': 'polar_uncharged',
    'aspartate': 'negative',
    'cysteine': 'special_3',
    'glutamate': 'negative',
    'glutamine': 'polar_uncharged',
    'glycine': 'hydrophobic',
    'histidine': 'positive',
    'isoleucine': 'hydrophobic',
    'leucine': 'hydrophobic',
    'lysine': 'positive',
    'methionine': 'hydrophobic',
    'phenylalanine': 'hydrophobic_aromatic',
    'proline': 'special_2',
    'serine': 'polar_uncharged',
    'threonine': 'polar_uncharged',
    'tryptophan': 'hydrophobic_aromatic',
    'tyrosine': 'special_4',
    'valine': 'hydrophobic',
    'stop': 'stop'
}
# dict to give abbreviations of an acid based on its full government name
amino_abbrev = {
    'alanine':('ala','A'),
    'arginine':('arg','R'),
    'asparagine':('asn','N'),
    'aspartate':('asp','D'),
    'cysteine':('cys','C'),
    'glutamate':('glu','E'),
    'glutamine':('gln','Q'),
    'glycine':('gly','G'),
    'histidine':('his','H'),
    'isoleucine':('ile','I'),
    'leucine':('leu','L'),
    'lysine':('lys','K'),
    'methionine':('met','M'),
    'phenylalanine':('phe','F'),
    'proline':('pro','P'),
    'serine':('ser','S'),
    'threonine':('thr','T'),
    'tryptophan':('trp','W'),
    'tyrosine':('tyr','Y'),
    'valine':('val','V'),
    'stop':('ter','X')
}
# dict to get base compliments
alternate_strand_base = {
    'G':'C',
    'C':'G',
    'A':'T',
    'T':'A',
    '-':'-'
}

# function to run vep to get the vep output of a given variant
def vep(input_snv, reference_path, threads='2'):
    print(os.listdir('/root/'))
    start = f'/usr/src/app/vep/ensembl-vep/vep --offline --cache --tab --everything --assembly GRCh38 --fasta {reference_path} --fork {threads} --buffer_size 120000'
    params = [
        ' --sift b',
        ' --polyphen b',
        ' --ccds',
        ' --hgvs',
        ' --symbol',
        ' --numbers',
        ' --domains',
        ' --regulatory',
        ' --canonical',
        ' --protein',
        ' --biotype',
        ' --af',
        ' --af_1kg',
        ' --af_gnomade',
        ' --af_gnomadg',
        ' --max_af',
        ' --pubmed',
        ' --uniprot',
        ' --mane',
        ' --tsl',
        ' --appris',
        ' --variant_class',
        ' --gene_phenotype',
        ' --mirna',
        ' --per_gene',
        ' --show_ref_allele',
        ' --force_overwrite'
    ]
    plugins = [
        f' --plugin LoFtool,/usr/src/app/vep/vep-resources/LoFtool_scores.txt',
        f' --plugin Mastermind,/usr/src/app/vep/vep-resources/mastermind_cited_variants_reference-2023.04.02-grch38.vcf.gz',
        f' --plugin CADD,/usr/src/app/vep/vep-resources/whole_genome_SNVs.tsv.gz',
        f' --plugin Carol',
        f' --plugin Condel,/home/threadripper/.vep/Plugins/config/Condel/config',
        f' --plugin pLI,/usr/src/app/vep/vep-resources/pLI_values.txt',
        f' --plugin PrimateAI,/usr/src/app/vep/vep-resources/PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz',
        f' --plugin dbNSFP,/usr/src/app/vep/vep-resources/dbNSFP4.4a_grch38.gz,ALL',
        f' --plugin REVEL,/usr/src/app/vep/vep-resources/new_tabbed_revel_grch38.tsv.gz',
        f' --plugin AlphaMissense,file=/usr/src/app/vep/vep-resources/AlphaMissense_hg38.tsv.gz',
        f' --plugin EVE,file=/usr/src/app/vep/vep-resources/eve_merged.vcf.gz',
        f' --plugin DisGeNET,file=/usr/src/app/vep/vep-resources/all_variant_disease_pmid_associations_final.tsv.gz'
    ]

    plugin_str = ''.join(plugins)
    
    commandInputSNV = f' -i {input_snv}'
    commandOutputSNV = ' -o ' + '/usr/src/app/vep/report_output.txt'
    # command builder
    command = start + ''.join(params) + plugin_str + commandInputSNV + commandOutputSNV
    os.system(command)

# like map(float, array) but with error handling and exceptions
def list_to_float(input):
    returnlist = []
    for item in input:
        try:
            returnlist.append(float(item))
        except:
            continue
    if returnlist == []:
        return [0]
    return returnlist

# function that generates portion of the report for what the variant resulted in
def stopText(alt_protein, property_desc):
    if alt_protein == 'stop':
        return 'a premature stop codon.'
    return f'{alt_protein}, an amino acid with {property_desc} properties.'

# function that generates portion of the report for the clinvar significance
def clinvarText(clnsig, review, trait):
    if clnsig == '-':
        return 'This variant is currently not curated in ClinVar.'
    return f'This variant is curated as {clnsig.replace("_", " ").lower()} in ClinVar for the following disease(s): {trait.replace("_", " ").replace("&", "; ")} ({review.replace("_", " ").replace("&", ", ")}).'

# function that will format a number to include a smaller amount of precision, i believe to make it a percentage from a decimal while shortening the decimal
def round_to_nonzero(num):
    return round(num, -int(np.floor(np.log10(abs(num)))))
def format_float(num):
    rounded_num = round_to_nonzero(num)
    return np.format_float_positional(rounded_num, trim='-')

# function that returns the rarity text with alternate phrasing depending on the provided rarity
def rarityText(rarity):
    if rarity == 0.0:
        return f' is so rare that it is not catalogued in many common human population allele frequency databases, which is consistent with disease.'
    return f' occurs in less than {format_float(rarity*100)}% of the population, which is consistent with disease.'

# function that writes the actual report paragraph, using all the different pieces passed in
def writeText(chrom, pos, protein_pos, nm_id, c_id, p_id, aka_p_id, symbol, og_protein, new_protein, description, coding_exon, effect, tools_text, rarity_text, dbsnp_text, clinvar_text):
    if new_protein == 'stop':
        new_protein = 'a premature stop codon'
        description = 'terminating the protein'
    return (f"{nm_id}({symbol}):{c_id}({p_id})",f"The {aka_p_id} variant (also known as {c_id}), located in coding exon {coding_exon} of the {symbol} gene, results from a{effect}.\
            The {og_protein} at codon {protein_pos} is replaced by {new_protein}, {description}. This alteration is predicted to be deleterious{tools_text}. The {aka_p_id} variant {rarity_text}\
            The {symbol} gene is located on Chromosome {chrom}, and the variant is located at position {pos} on the chromosome. {dbsnp_text}{clinvar_text}")

# function to generate the report text from the chromosome, position, ref allele, and alt allele. 
def generateReport(chr, pos, ref, alt):
    global aminoacid_properties
    global amino_abbrev
    global alternate_strand_base
    
    var_id = f'chr{chr}_{pos}_{ref}/{alt}'

    # function to tell pandas if a row is skippable when reading it in (used to skip over header rows)
    def skip_rows(line):
        return line < begin_index

    print(chr, pos, ref, alt)
    # write the file to be run through vep
    with open('/usr/src/app/vep/report_input.txt','w') as opened:
        opened.write(f'chr{chr}\t{pos}\t.\t{ref}\t{alt}')
    # run vep using file that just got written
    vep('/usr/src/app/vep/report_input.txt', '/usr/src/app/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta')

    # identify the index at which the actual content starts in the vep output
    begin_index = 0
    for line in open('/usr/src/app/vep/report_output.txt', 'r'):
        if line.startswith('##'):
            begin_index+=1
            continue
        if line.startswith('#'):
            break
    
    # initialize an array in which all rows of the vep output will be recorded
    alternate_futures = []

    # for each row in the vep output, it will attempt to identify as many of the columns needed for a report as possible, adding a point to a row's 'score' for each field it identifies
    df = pd.read_csv('/usr/src/app/vep/report_output.txt', sep='\t', header=0, skiprows=skip_rows)
    for index, row in df.iterrows():
        score = 0
        print(row["Gene"])
        true_ref = row["REF_ALLELE"]
        true_alt = row["Allele"]
        # do some strand shenanigans 
        try:
            if int(row['STRAND']) == int(-1):
                true_ref = ''.join([alternate_strand_base[x] for x in row["REF_ALLELE"] if not x == '-'])[::-1]
                true_alt = ''.join([alternate_strand_base[x] for x in row["Allele"] if not x == '-'])[::-1]
        except:
            print('failed strand')
        # determine variant type
        variant_type = ''
        variant_comparison = len(true_ref)-len(true_alt)
        if variant_comparison > 0:
            variant_type = 'deletion'
        elif variant_comparison < 0:
            variant_type = 'insertion'
        else:
            variant_type = 'single'
        # find the protein position, adding a score if successful, using a placeholder otherwise
        try:
            protein_pos = row['Protein_position']
            score += 1
        except Exception as e:
            print('PROTEIN_POS ERROR')
            print(e)
            protein_pos = '[PROTEIN_POSITION]'

        # find the transcript ID, adding a score if successful, using a placeholder otherwise
        try:
            nm_id = row['MANE_SELECT']
            score += 1
        except Exception as e:
            print('NM_ID ERROR')
            print(e)
            nm_id = '[NM_ID]'
        
        # find the HGVS consequence ID, adding a score if successful, using a placeholder otherwise
        try:
            c_id = row['HGVSc'].split(':')[1]
            score += 1
        except Exception as e:
            print('HGVSc ID ERROR')
            print(e)
            c_id = '[HGVSc ID]'
        
        # find the HGVS protein ID, adding a score if successful, using a placeholder otherwise
        try:
            p_id = row['HGVSp'].split(':')[1]
            score += 1
        except Exception as e:
            print('HGVSp ID ERROR')
            print(e)
            p_id = '[HGVSp ID]'

        # find the original protein, adding a score if successful, using a placeholder otherwise
        matches = re.findall(r'[A-Z][a-z]{2}', p_id)
        try:
            og_three_letter = matches[0]
            og_protein = '[ORIGINAL_PROTEIN]'
            for item in amino_abbrev:
                if amino_abbrev[item][0] == og_three_letter.lower():
                    og_protein = item
            score += 1
        except Exception as e:
            print('ORIGINAL_PROTEIN ERROR')
            print(e)
            og_protein = '[ORIGINAL_PROTEIN]'

        # find the new protein, adding a score if successful, using a placeholder otherwise
        try:
            new_three_letter = matches[1]
            new_protein = '[NEW_PROTEIN]'
            for item in amino_abbrev:
                if amino_abbrev[item][0] == new_three_letter.lower():
                    new_protein = item
            score += 1
        except Exception as e:
            print('NEW_PROTEIN ERROR')
            print(e)
            new_protein = '[NEW_PROTEIN]'
        
        # find the short protein ID, adding a score if successful, using a placeholder otherwise
        try:
            aka_p_id = p_id.replace(og_three_letter, amino_abbrev[og_protein][1]).replace(new_three_letter, amino_abbrev[new_protein][1]).replace('Ter', '*')
            score += 1
        except Exception as e:
            aka_p_id = '[SHORT_PID]'
            print(e)

        # find the gene symbol, adding a score if successful, using a placeholder otherwise
        try:
            symbol = row['SYMBOL']
            score += 1
        except Exception as e:
            print('SYMBOL ERROR')
            print(e)
            symbol = '[SYMBOL]'

        try:
            # find the consequence of the variant, adding a score if successful, using a placeholder otherwise
            description = '[ALTERATION DESC]'
            match variant_type:
                case 'single':
                    property_res = 'differing'
                    if aminoacid_properties[og_protein] == aminoacid_properties[new_protein]:
                        property_res = 'similar'
                    description = f'an amino acid with {property_res} properties'
                case 'insertion':
                    matches = re.findall(r'\d+\b', p_id)
                    amino_acids = '[NUM ACIDS]'
                    if matches:
                        amino_acids = int(matches[-1])-2
                    description = f"followed by a frameshift that introduces {amino_acids} different amino acids prior to a premature stop codon"
                case 'deletion':
                    matches = re.findall(r'\d+\b', p_id)
                    amino_acids = '[NUM ACIDS]'
                    if matches:
                        amino_acids = int(matches[-1])-2
                    description = f'followed by a frameshift that introduces {amino_acids} different amino acids prior to a premature stop codon'
            score += 1
        except Exception as e:
            print('ALTERATION DESC ERROR')
            print(e)
            description = '[ALTERATION DESC]'
        
        # find the coding exon, adding a score if successful, using a placeholder otherwise
        try:
            coding_exon = row['EXON'].split('/')[0]
            score += 1
        except Exception as e:
            print('CODING EXON ERROR')
            print(e)
            coding_exon = '[CODING EXON]'
        
        # find the consequence, and position, adding a score if successful, using a placeholder otherwise
        try:
            match variant_type:
                case 'single':
                    n = ''
                    if true_ref.lower().startswith('a'):
                        n = 'n'
                    effect = f'{n} {true_ref} to {true_alt} substitution'
                case 'insertion':
                    match len(true_alt):
                        case 1:
                            cds_start, cds_stop = row['CDS_position'].split('-')
                            effect = f" single nucleotide ({true_alt}) insertion between positions {cds_start} and {cds_stop}"
                        case default:
                            cds_start, cds_stop = row['CDS_position'].split('-')
                            effect = f" {len(true_alt)} nucleotide ({true_alt}) insertion between positions {cds_start} and {cds_stop}"
                case 'deletion':
                    cds_start = str(row['CDS_position']).split('-')[0]
                    cds_stop = str(row['CDS_position']).split('-')[-1]
                    print(cds_start)
                    match len(true_ref):
                        case 1:
                            effect = f" single nucleotide ({true_ref}) deletion at position {cds_start}"
                        case default:
                            effect = f" {len(true_ref)} nucleotide ({true_ref}) deletion between positions {cds_start} and {cds_stop}"
            score += 1
        except Exception as e:
            print('EFFECT DESC ERROR')
            print(e)
            effect = '[EFFECT DESC]'
        
        # find the allele frequency, adding a score if successful, using a placeholder otherwise
        try:
            rarities = []
            for item in ['AF', 'gnomADe_AF', '1000Gp3_AF']:
                try:
                    rarities.append(float(row[item]))
                except ValueError as v:
                    print(v)
                    continue
            if rarities == []:
                rarity = 0.0
            else:
                rarity = max(rarities)
            rarity_text = rarityText(rarity)
            score += 1
        except Exception as e:
            print('RARITY TEXT ERROR')
            print(e)
            rarity_text = '[RARITY TEXT]'
        
        # find the dbSNP ID, adding a score if successful, using a placeholder otherwise
        try:
            dbsnp_text = f"The dbSNP identifier for this variant is {row['rs_dbSNP']}. "
            if row['rs_dbSNP'] == '-':
                dbsnp_text = "There is currently no dbSNP identifier for this variant. "
            score += 1
        except Exception as e:
            print('DNSNP RS ERROR')
            print(e)
            dbsnp_text = '[DNSNP RS]'

        # find the clinvar consequence, adding a score if successful, using a placeholder otherwise
        try:
            clinvar_text = clinvarText(row['clinvar_clnsig'], row['clinvar_review'], row['clinvar_trait'])
            score += 1
        except Exception as e:
            print('CLINVAR TEXT ERROR')
            print(e)
            clinvar_text = '[CLINVAR TEXT]'

        # find the tools that identified the variant as deleterious, adding a score if successful, using a placeholder otherwise
        try:
            tools = []
            tools.append('AM,' if 'likely_pathogenic' in row['am_class'] else '')
            tools.append('BA,' if 'D' in row['BayesDel_addAF_pred'] else '')
            tools.append('BN,' if 'D' in row['BayesDel_noAF_pred'] else '')
            tools.append('CD,' if row['CADD_PHRED'] != '-' and float(row['CADD_PHRED']) >= 20 else '')
            tools.append('CL,' if 'deleterious' in row['Condel'] else '')
            tools.append('CP,' if 'D' in row['ClinPred_pred'] else '')
            tools.append('CR,' if 'Deleterious' in row['CAROL'] else '')
            tools.append('CS,' if 'likely_pathogenic' in row['CLIN_SIG'] else '')
            tools.append('CV,' if 'Pathogenic' in row['clinvar_clnsig'] else '')
            tools.append('DG,' if 'D' in row['DEOGEN2_pred'] else '')
            tools.append('DN,' if row['DANN_score'] != '-' and float(row['DANN_score']) >= 0.96 else '')
            tools.append('EV,' if 'Pathogenic' in row['EVE_CLASS'] else '')
            tools.append('FK,' if 'D' in row['fathmm-MKL_coding_pred'] else '')
            tools.append('FM,' if 'D' in row['FATHMM_pred'] else '')
            tools.append('FX,' if 'D' in row['fathmm-XF_coding_pred'] else '')
            tools.append('IM,' if 'HIGH' in row['IMPACT'] else '')
            tools.append('LR,' if 'D' in row['LRT_pred'] else '')
            tools.append('LS,' if 'D' in row['LIST-S2_pred'] else '')
            tools.append('MA,' if 'H' in row['MutationAssessor_pred'] else '')
            tools.append('MC,' if 'D' in row['M-CAP_pred'] else '')
            tools.append('ML,' if 'D' in row['MetaLR_pred'] else '')
            tools.append('MP,' if row['MPC_score'] != '-' and max(list_to_float(str(row['MPC_score']).split(','))) > 0.5  else '')
            tools.append('MR,' if 'D' in row['MetaRNN_pred'] else '')
            tools.append('MS,' if 'D' in row['MetaSVM_pred'] else '')
            tools.append('MT,' if 'D' in row['MutationTaster_pred'] else '')
            tools.append('MV,' if row['MVP_score'] != '-' and max(list_to_float(str(row['MVP_score']).split(','))) > 0.7  else '')
            tools.append('PA,' if 'D' in row['PrimateAI_pred'] else '')
            tools.append('PD,' if 'D' in row['Polyphen2_HDIV_pred'] else '')
            tools.append('PP,' if 'probably_damaging' in row['PolyPhen'] else '')
            tools.append('PR,' if 'D' in row['PROVEAN_pred'] else '')
            tools.append('PV,' if 'D' in row['Polyphen2_HVAR_pred'] else '')
            tools.append('RV,' if row['REVEL'] != '-' and float(row['REVEL']) > 0.75  else '')
            tools.append('SF,' if 'deleterious' in row['SIFT'] else '')
            tools.append('S4,' if 'D' in row['SIFT4G_pred'] else '')
            tools.append('V4,' if row['VEST4_score'] != '-' and max(list_to_float(str(row['VEST4_score']).split(','))) > 0.5  else '')
            # num_tools = int(len(''.join(tools).replace(',',''))/2)

            while("" in tools):
                tools.remove("")
            print(tools)
            if tools:
                tools_text = f" by in silico analysis ({''.join(tools)[:-1]})"
            else:
                tools_text = "."
            score += 1
        except Exception as e:
            print('TOOL ERROR')
            print(e)
            tools_text = "[TOOLS TEXT]"
            continue
        
        # generate the text using all the fields/placeholders above
        header, body = writeText(
            chr,
            "{:,}".format(int(pos)),
            protein_pos,
            nm_id,
            c_id,
            p_id,
            aka_p_id,
            symbol,
            og_protein,
            new_protein,
            description,
            coding_exon,
            effect,
            tools_text,
            rarity_text,
            dbsnp_text,
            clinvar_text
            )

        # write the variation of the text to the array
        alternate_futures.append((score, (f'chr{chr}_{pos}_{ref}/{alt}', header, body)))
    
    # sets worst case scenario line
    max_line = ('Error', "Could not retrieve vep output.")
    max_score = 0
    # finds the row with the highest score (most found rows)
    for future in alternate_futures:
        if future[0] > max_score:
            max_score = future[0]
            max_line = future[1]
    
    # returns most complete row
    return max_line


# route to return the progress when using a file upload on the report page
@app.route('/report_progress', methods=['GET'])
def report_progress():
    global report_progress_val
    return jsonify({"progress": report_progress_val, "color": 'blue'})

# route to generate the report text for a single variant
# accessed through navbar, as well as by clicking the submit button on the SNV report page
@app.route('/report/<string:chr>:<string:pos>:<string:ref>:<string:alt>')
@app.route('/report')
@app.route('/report/')
def reportresult(chr='X', pos='X', ref='X', alt='X'):
    if chr == 'X' and pos == 'X' and ref == 'X' and alt == 'X':
        return render_template('report.html', reportText='', placeholder='chrX_XXXX_X/X')

    # error case where the fasta fiel is missing
    if not os.path.isfile('/usr/src/app/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta'):
        reportText = [('Error', 'Missing ..polar-pipeline/services/web/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta')]
    else:
        reportText = [generateReport(chr, pos, ref, alt)]


    # in the event that there is no report text, outputs a line saying so
    print(reportText)
    if reportText == [None]:
        reportText = [('Error', 'Could not find complete vep output.')]
    return render_template('report.html', reportText=reportText, placeholder=f'chr{chr}_{pos}_{ref}/{alt}')

# route to run the report for all variants in a provided file. one per line, with format "chr{chr#}_pos_ref/alt"
# accessed by the file upload button on the SNV report page
@app.route('/report/fileupload', methods=['POST'])
def reportfileupload():
    global report_progress_val
    report_progress_val = 0

    # if no file is found
    if 'file' not in request.files:
        return 'No file part'
    
    file = request.files['file']
    
    # if no fils is found pt 2
    if file.filename == '':
        return 'No selected file'
    
    # make a temp folder to save the uploaded report file in
    if not os.path.isdir('/usr/src/temp'):
        os.mkdir('/usr/src/temp')

    # save the file
    file_path = os.path.join('/usr/src/temp', 'reportlist.txt')
    if file:
        file.save(file_path)

    # retrieve all variants to generate a report for from the file
    variants = []
    try:
        for line in open(file_path):
            if line:
                chr, pos, ref_alt = line.strip().split('_')
                ref, alt = ref_alt.split('/')
                variants.append((chr, pos, ref, alt))
    except:
        # if there is an error, return that the file is in the wrong format
        return render_template('report.html', reportText=[('Error', 'Incorrect file format.')], placeholder=file.filename)
    
    # iterate through variants, generating reports and updating the progress bar with the current percent completion
    reportText = []
    for variant_index, variant in enumerate(variants):
        report_progress_val = (variant_index+1)/len(variants)
        variantreport = (generateReport(variant[0].replace('chr', ''), variant[1], variant[2], variant[3]))
        if variantreport:
            reportText.append(variantreport)
        else:
            reportText.append((f'{variant[0]}_{variant[1]}_{variant[2]}/{variant[3]}', 'Could not find complete vep output.'))

    # if the array is empty after iterating through everything, say so
    if reportText == [None]:
        reportText = [('Error', 'Could not find complete vep output.')]
    
    return render_template('report.html', reportText=reportText, placeholder=file.filename)


# route to generate the HGVS ID for structural variants
# accessed through the submit button residing on the SV report page, after a file has been selected (usually an N0 file), on the modal that pops up.
@app.route('/extractsniffles', methods=['POST'])
def extractsniffles():
    # check all necessary files are present
    missing = []
    if not os.path.isfile('/usr/src/app/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta'):
        missing.append('..polar-pipeline/services/web/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta')
    if not os.path.isfile('/usr/src/app/vep/hg38.refGene'):
        missing.append('..polar-pipeline/services/web/vep/hg38.refGene')
    if missing:
        return jsonify(f'Error: Missing {", ".join(missing)}')
    # load reference fasta
    genome = Fasta('/usr/src/app/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta')
    # load transcripts from the refgene file
    with open('/usr/src/app/vep/hg38.refGene') as infile:
        transcripts = pu.read_transcripts(infile)
    data = request.get_json()
    
    # Extract the variables from the JSON data
    filepath = data.get('path')
    sniffles = data.get('id')

    # set default case as error
    hgvs = 'error'

    # open the selected file, iterating through it
    cols = {}
    header = True
    variants = []
    for line in open(filepath):
        variant = line.strip().split('\t')
        # grab column header indexes
        if header:
            header = False
            for index, col in enumerate(variant):
                cols[col] = index
            continue
        # if the row has a matching sniffles ID, it is going to be checked
        if variant[cols['#Uploaded_variation']] == sniffles:
            chrom = variant[cols['#CHROM']]
            pos = int(variant[cols['POS']])
            ref = variant[cols['REF']].replace('N', '')
            alt = variant[cols['ALT']].replace('<DEL>', '').replace('<DUP>', '').replace('<INS>', '').replace('<INV>', '')
            if len(alt) > 0 and alt[0] in ['[', ']']:
                alt = ''
            svlen = variant[cols['SVLEN']]
            try:
                svlen = int(svlen)
            except:
                svlen = 0
            mane = variant[cols['MANE_SELECT']]
            # ID cannot be generated without the transcript ID, so it is skipped if the ID is missing
            if mane == '-':
                continue
                hgvs = 'no transcript ID'
            else:
                hgvs = pyhgvsv.format_hgvs_name(chrom, pos, ref, alt, genome, transcripts[mane], sv_length=svlen)
            # otherwise, append the generated ID to the list of IDs
            variants.append(hgvs)

    # return the list of generated IDs
    return jsonify(variants)

# route to do the file browser on the SV report page
@app.route('/svreport/<path:path>')
@app.route('/svreport')
def reportbrowse(path=None):
    # if path outside of the allowed directory, redirect to the mount directory
    if path is None or not path.startswith('mnt'):
        path = base_path

    # build the actual path
    full_path = os.path.join('/', path)
    directory_listing = {}
    # keeps track of folders/files through the directory_listing dict so that the folders can be displayed first
    for item in os.listdir(full_path):
        is_dir = False
        if os.path.isdir(os.path.join(full_path, item)):
            is_dir = True
        directory_listing[item] = is_dir
    # record the previous directory so the user can go back up a level
    up_level_path = os.path.dirname(path)
    
    # alphabetize the directory
    ordered_directory = sorted(os.listdir(full_path), key=alphabetize)

    return render_template('reportsvbrowse.html', current_path=full_path, directory_listing=directory_listing, ordered_directory=ordered_directory, up_level_path=up_level_path)

def count_lines(filename):
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            return sum(1 for _ in file)
    else:
        return '0'
    
def convert_timestamp(timestamp):
    datetime_obj = datetime.strptime(timestamp, '%y-%m-%d_%H-%M-%S')
    formatted_datetime = datetime_obj.strftime('%d-%m-%Y;%H:%M:%S')
    return formatted_datetime

def buildfreqlist():
    path = './polarpipeline/resources/frequency'
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
    output = []
    for folder in folders:
        output.append((folder, convert_timestamp(folder), count_lines(os.path.join(path, folder, 'fileKey.tsv'))))
    print(output)
    return output

frequency_progress = 0
# route to return the frequency of a specific variant within the database
# accessed both by the navbar as well as the submit button on the frequency page
@app.route('/frequency/<string:_chr>:<string:pos>:<string:ref>:<string:alt>')
@app.route('/frequency/<string:_chr>')
@app.route('/frequency')
def frequency(_chr='X', pos='X', ref='X', alt='X'):
    global frequency_progress
    if frequency_progress == 100:
        frequency_progress = 0
    chr = urllib.parse.unquote(_chr)
    # if not searching for anything, just return placeholders
    if chr == 'X' and pos == 'X' and ref == 'X' and alt == 'X':
        return render_template('frequency.html', reportText='', placeholder='chrX_XXXX_X/X', done='green', folders=buildfreqlist())

    # print(chr, pos, ref, alt)
    # build id to search for in the frequency file
    if pos=='X' and ref=='X' and alt=='X':
        id = chr
    else:
        id = f'chr{chr}_{pos}_{ref}/{alt}'
    print(id)

    # check for generated frequency folders
    variant = []
    folders = [f for f in os.listdir('./polarpipeline/resources/frequency') if os.path.isdir(os.path.join('./polarpipeline/resources/frequency', f))]
    if not folders:
        return None
    # find the folder with the newest timestamp (indicating newest frequency data)
    pattern = re.compile(r'\d{2}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')
    newest_folder = max(folders, key=lambda folder: datetime.strptime(pattern.search(folder).group(), '%d-%m-%y_%H-%M-%S'))
    directory = os.path.join('./polarpipeline/resources/frequency', newest_folder)

    # grab filepaths for the files in the newest frequency folder
    variant_catalogue = os.path.join(directory, 'variantCatalogue.tsv')
    file_key = os.path.join(directory, 'fileKey.tsv')

    # the files a variant is found in are encoded by numbers since the names are so long, so there is a file to make a key for these. this builds that key from the file
    fileDirectory = {}
    for line in open(file_key):
        fileName, fileNum = line.strip().split('\t')
        fileDirectory[fileNum] = fileName
    print(fileDirectory)

    # iterate through the variant list, checking if the id matches
    for line in open(variant_catalogue):
        if line.startswith(id):
            variant = line.strip().split(',')[:-1]
            source = []
            for item in line.strip().split(',')[-1].split(';'):
                try:
                    source.append(fileDirectory[item])
                except:
                    pass
            # if line matches, return it along with all files the variant is in
            return render_template('frequency.html', variant=variant, source=source, placeholder=id, done='green', folders=buildfreqlist())
    # if not found, return not found
    return render_template('frequency.html', variant=variant, source=['not found'], placeholder=id, done='green', folders=buildfreqlist())

@app.route('/frequencyprogress', methods=['GET'])
def frequencyprogress():
    global frequency_progress
    return jsonify({'progress': frequency_progress})

@app.route('/deletefrequency/<filename>')
def deletefrequency(filename):
    path = os.path.join('./polarpipeline/resources/frequency', filename)
    if os.path.isdir(path):
        shutil.rmtree(path)
    return redirect(url_for('frequency'))

# recursive function to find fist file ending in merged_N0.bed in a given directory (used breadth first search bc its only like 2 layers down)
def findmergedfile(path, suffix):
    for item in os.listdir(path):
        founditem = os.path.join(path, item)
        if os.path.isfile(founditem):
            if founditem.endswith(suffix):
                return founditem
    searchresult = ''
    for item in os.listdir(path):
        founditem = os.path.join(path, item)
        if os.path.isdir(founditem):
            searchresult = findmergedfile(founditem, suffix)
            if searchresult:
                return searchresult
    return searchresult

@app.route('/makefrequency', methods=['POST'])
def makefrequency():
    global frequency_progress
    class Variant:
        def __init__(self, id, gt, file):
            self.id = id
            self._1_0 = 0
            self._0_1 = 0
            self._1__1 = 0
            self._d__d = 0
            self._0__0 = 0
            self._0__1 = 0
            self._1__2 = 0
            match gt:
                case '1|0':
                    self._1_0 = 1
                case '0|1':
                    self._0_1 = 1
                case '1/1':
                    self._1__1 = 1
                case './.':
                    self._d__d = 1
                case '0/0':
                    self._0__0 = 1
                case '0/1':
                    self._0__1 = 1
                case '1/2':
                    self._1__2 = 1
            self.total = 1
            self.fileList = [file]
        def updateCount(self, gt, file):
            if file not in self.fileList:
                match gt:
                    case '1|0':
                        self._1_0 += 1
                    case '0|1':
                        self._0_1 += 1
                    case '1/1':
                        self._1__1 += 1
                    case './.':
                        self._d__d += 1
                    case '0/0':
                        self._0__0 += 1
                    case '0/1':
                        self._0__1 += 1
                    case '1/2':
                        self._1__2 += 1
                self.total += 1
                if file not in self.fileList:
                    self.fileList.append(file)
        def printLine(self):
            filenums = map(str, self.fileList)
            output = f'{self.id},{self._1_0},{self._0_1},{self._1__1},{self._d__d},{self._0__0},{self._0__1},{self._1__2},{self.total},{";".join(filenums)}\n'
            return output

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)

    filelist = []
    for output_path in config['Output']['output'].split(';'):
        for item in os.listdir(output_path):
            mergedfile = ''
            # attempts to identify directories made by the pipeline via the timestamp in front (since things get shoved everywhere with reckless abandon)
            output_item = os.path.join(output_path, item)
            pattern = r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'
            matches = re.findall(pattern, item)
            # skipping over T2T directories, if it meets critera for a pipeline output folder
            if os.path.isdir(output_item) and matches and not output_item.endswith('_T2T'):
                # here it gets the date and filepath of the N0 file within the directory for entry into the database
                date = matches[0]
                timestamp = datetime.strptime(date.replace('_', ' '), '%Y-%m-%d %H-%M-%S')
                # print(date, filename)
                mergedfile = findmergedfile(output_item, '_merged.bed')
            
            # if the N0 file was found
            if mergedfile:
                filelist.append(mergedfile)


    current_datetime = datetime.now()
    _formatted_datetime = current_datetime.strftime("%d-%m-%y_%H-%M-%S")
    formatted_datetime = os.path.join('./polarpipeline/resources/frequency', _formatted_datetime)
    os.mkdir(formatted_datetime)

    variants = {}
    filekey = {}
    for fileindex, file in enumerate(filelist):
        print(os.path.basename(file))
        frequency_progress = (fileindex+1)/len(filelist)
        if file not in filekey:
            filekey[file] = fileindex
        colkey = {}
        for row in open(file):
            line = row.strip().split('\t')
            if row.startswith('#'):
                for index, col in enumerate(line):
                    colkey[col] = index
                continue
            id = f'{line[colkey["#CHROM"]]}_{line[colkey["POS"]]}_{line[colkey["REF"]]}/{line[colkey["ALT"]]}'
            if id in variants:
                variants[id].updateCount(line[colkey['GT']], fileindex)
            else:
                variant = Variant(id, line[colkey['GT']], fileindex)
                variants[id] = variant

        with open(f'{formatted_datetime}/variantCatalogue.tsv', 'w') as opened:
            for variant in variants:
                opened.write(variants[variant].printLine())

        with open(f'{formatted_datetime}/fileKey.tsv', 'w') as opened:
            for file in filekey:
                opened.write(f'{file}\t{filekey[file]}\n')
    return 'success'



def getOutputs(config):
    outputs = []
    for item in config['Output']['output'].strip().split(';'):
        outputs.append(item)
    return outputs

# updated to automatically search in the output directories and add any N0 files it finds to the database
# database schema is one for N0 files, another for the possible column values, and one more to define what columns are in what files
# allows for pretty quick retrieval of what columns are in what files, as well as what datatypes those columns are
@app.route('/search')
@app.route('/search/<int:numperpage>/<int:page>')
def search(numperpage=10, page=0):
    # just to get output directories for the N0 locater
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)

    N0s = {}
    columns = []
    for path in getOutputs(config):
        for file in os.listdir(path):
            if os.path.isdir(os.path.join(path, file)):
                found_N0 = findmergedfile(os.path.join(path, file), '_N0.bed')
                if found_N0:
                    for line in open(found_N0):
                        for item in line.strip().split('\t'):
                            if item not in columns:
                                columns.append(item)
                        break
                    N0s[file] = found_N0

    # finds a preexisting search result file
    filename = ''
    for file in os.listdir('./polarpipeline/search/'):
        if file.endswith('_search_result.tsv'):
            filename = file
            continue

    # this is the code to get the appropriate lines from the file for the preview but looking back at it now i think its probably really stupid
    # like why do i have two different arrays even i cannot answer that question
    result = []
    lines = []
    numresults = -1
    if filename != '':
        for index, line in enumerate(open(os.path.join('./polarpipeline/search', filename), 'r')):
            numresults += 1
            if not index > numperpage*(page+1):
                lines.append(line.strip())
        try:
            result.append(lines[0].split('\t'))
        except: 
            result.append('')
        for i in range(page*numperpage+1, page*numperpage+numperpage+1):
            try:
                result.append(lines[i].split('\t'))
            except:
                continue
    # this code determines the appropriate page numbers for use on the buttons at the bottom of the preview box
    nextpage = -1
    prevpage = -1
    if page*numperpage+numperpage+1 < numresults:
        nextpage = page+1
    if page != 0:
        prevpage = page-1
    
    return render_template('search.html', available_dbs=sorted([x for x in N0s]), paths=N0s, columns=columns, result=result, numresults=numresults, numperpage=numperpage, page=page, prevpage=prevpage, nextpage=nextpage)

class Parameter:
    def __init__(self, column, operator, value, NAs):
        # print(column, operator, value)
        self.column = column
        self.operator = operator
        self.value = value
        self.NAs = bool(NAs)

    def compare(self, comp_value):
        if comp_value in ['-', '.', '']:
            if self.NAs:
                return True
            return False
        match self.operator:
            case '>':
                return float(comp_value) > float(self.value)
            case '<':
                return float(comp_value) < float(self.value)
            case '>=':
                return float(comp_value) >= float(self.value)
            case '<=':
                return float(comp_value) <= float(self.value)
            case '==':
                return str(comp_value) == str(self.value)
            case '!=':
                return str(comp_value) != str(self.value)
            case 'Contains':
                return str(self.value) in str(comp_value)

def get_array_length(data):
    if not data:
        return 0
    first_key = next(iter(data))
    array_length = len(data[first_key])
    return array_length


def contains_date_pattern(s):
    pattern = r'\d{4}-\d{2}-\d{2}'
    return bool(re.search(pattern, s))

# initialization of some things for the search progress bar. used to check if the user cancelled, sets the color, and percent completion
progress = 1
cancelled = False
color = 'blue'
remainingsearchtime = {'minutes': '--', 'seconds': '--'}

# actually does the search when you click search ikr creative name
# accessed by the search button on the database search page
@app.route('/beginsearch', methods=['POST'])
def beginsearch():
    global color
    global cancelled
    global progress
    global remainingsearchtime

    # sets everything to default at beginning of search, gets search querey
    cancelled = False
    color = 'blue'
    progress = 0
    files = request.json.get("files")
    parameters = [Parameter(x[0], x[2], x[1], x[3]) for x in request.json.get("params")]
    remainingsearchtime['minutes'] = '--'
    remainingsearchtime['seconds'] = '--'
    deltas = []

    print(parameters[0].column, parameters[0].operator, parameters[0].value)
    print(files)

    # finds number of 'steps' for progress calculation
    # total_steps = len(files) * len(parameters)
    # creates search result filename 
    searchname = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_search_result.tsv'
    try:
        search_result = {'SOURCE': []}
        # finds and removes old search file

        # iterates through all files to be searched
        _time = time.time()
        rows=0
        for fileindex, file in enumerate(files):
            # print(file)
            cols = {}
            for line in open(file):
                variant = line.strip().split('\t')
                if line[:5] in ['#CHRO', 'CHROM']:
                    if not cols:
                        for colindex, col in enumerate(variant):
                            if not contains_date_pattern(col):
                                cols[col] = colindex
                                if col not in search_result:
                                    search_result[col] = ['-' for _ in range(rows)]
                    continue
                valid = True
                for param in parameters:
                    if not valid:
                        continue
                    if not param.column in cols:
                        valid = False
                        continue
                    else:
                        if not param.compare(variant[cols[param.column]]):
                            if 'PA' in variant[cols[param.column]]:
                                print(variant[cols[param.column]])
                            valid = False
                            continue
                if valid:
                    for col in search_result:
                        if col == 'SOURCE':
                            search_result['SOURCE'].append(file)
                        else:
                            if col in cols:
                                search_result[col].append(variant[cols[col]])
                            else:
                                search_result[col].append('-')
                rows +=1
            currtime = time.time()
            deltas.append((currtime - _time))
            seconds_remaining = sum(deltas)/len(deltas) * (len(files) - (fileindex + 1))
            _time = currtime
            remainingsearchtime['minutes'] = seconds_remaining // 60
            remainingsearchtime['seconds'] = int(seconds_remaining % 60)
            progress = (fileindex+1)/len(files)
        for file in os.listdir('./polarpipeline/search'):
            if file.endswith('_search_result.tsv'):
                os.remove(os.path.join('./polarpipeline/search', file))
        # opens new search file and writes header
        with open(f'./polarpipeline/search/{searchname}', 'w') as opened:
            opened.write('\t'.join([x for x in search_result if x != 'SOURCE'] + ['SOURCE'])+'\n')
            for i in range(get_array_length(search_result)):
                row = []
                for col in search_result:
                    if col != 'SOURCE':
                        row.append(search_result[col][i])
                row.append(search_result['SOURCE'][i])
                opened.write('\t'.join(row)+'\n')
    # in case something breaks
    except Exception as e:
        print(e)
        progress = 1
        color = 'yellow'
        return 'cancelled'

    # complete progress, green bar, success is supposed to refresh the page in the javascript but it is inconsistent idk how 
    progress = 1
    color = 'green'
    remainingsearchtime['minutes'] = 00
    remainingsearchtime['seconds'] = 00
    return 'success'

# polled by the database search page once per second to update the bar
@app.route('/searchprogress', methods=['GET'])
def searchprogress():
    global progress
    global color
    global remainingsearchtime
    return jsonify({"progress": progress, "color": color, 'remaining': remainingsearchtime})

# kindly provides the search result file to the user
# accessed by the download button beneath the file preview on the database search page
@app.route('/search/download')
def search_download():
    print('in download')
    filename = ''
    for file in os.listdir('./polarpipeline/search'):
        if file.endswith('_search_result.tsv'):
            return send_file(f'/usr/src/app/polarpipeline/search/{file}', as_attachment=True)
    return send_file(os.path.join(filename), as_attachment=True)

# just sets cancelled to true, main searchbegin function finds its dead body
# accessed by the cancel button on the info page of an ongoing run
@app.route('/searchcancelled', methods=['GET'])
def searchcancelled():
    global cancelled
    cancelled = True
    return 'cancelled like an influencer'

# the file browser for qc
# accessed by the newqc button on the QC page, see reportbrowse for a more thorough description of the function 
@app.route('/qcbrowse/<path:path>')
@app.route('/qcbrowse')
def qcbrowse(path=None):
    if path is None:
        path = base_path

    full_path = os.path.join('/', path)
    directory_listing = {}
    for item in os.listdir(full_path):
        is_dir = False
        if os.path.isdir(os.path.join(full_path, item)):
            is_dir = True
        directory_listing[item] = is_dir
    up_level_path = os.path.dirname(path)
    
    ordered_directory = sorted(os.listdir(full_path), key=alphabetize)

    return render_template('qcbrowse.html', current_path=full_path, directory_listing=directory_listing, ordered_directory=ordered_directory, up_level_path=up_level_path)

missing_variants = []
present_variants = 0
total_variants = 1
qc_path = ''

# route to actually do the QC
# accessed by browsing for a file on qcbrowse, clicking on a file, and then clicking submit on the modal
@app.route('/qc/<path:path>')
@app.route('/qc')
def qc(path=None):
    global missing_variants
    global present_variants
    global total_variants
    global qc_path
    if not path == None:
        full_path = os.path.join('/', path)
        qc_path = full_path
        print(full_path)
        expected_variants = {}
        for row in open('./polarpipeline/static/InternalBenchmarkList.txt'):
            variant, rs = row.strip().split('\t')
            expected_variants[variant] = rs
        found_variants = []
        chr_i = 0
        pos_i = 0
        ref_i = 0
        alt_i = 0
        for row in open(full_path):
            if row.startswith('#'):
                for index, col in enumerate(row.strip().split('\t')):
                    match col:
                        case '#CHROM':
                            chr_i = index
                        case 'POS':
                            pos_i = index
                        case 'REF':
                            ref_i = index
                        case 'ALT':
                            alt_i = index
                            break
                if [pos_i, ref_i, alt_i] == [0,0,0]:
                    return 'error'
                print(chr_i, pos_i, ref_i, alt_i)
                continue
            line = row.strip().split('\t')
            id = f'{line[chr_i]}_{line[pos_i]}_{line[ref_i]}/{line[alt_i]}'
            if id in expected_variants:
                found_variants.append(id)
        print(found_variants)
        missing_variants = []
        total_variants = 0
        present_variants = 0
        for i in expected_variants:
            if i in found_variants:
                present_variants += 1
            else:
                missing_variants.append((i, expected_variants[i]))
            total_variants += 1
    return render_template('qc.html', score=present_variants/total_variants, missing=missing_variants, filepath=qc_path)

# file browser for the file search
# see reportbrowse for a more thorough description of the filebrowser functionality
@app.route('/filesearchbrowse/<path:path>')
@app.route('/filesearchbrowse/')
def filesearchbrowse(path=None):
    if path is None:
        path = base_path

    full_path = os.path.join('/', path)
    directory_listing = {}
    for item in os.listdir(full_path):
        is_dir = False
        if os.path.isdir(os.path.join(full_path, item)):
            is_dir = True
        directory_listing[item] = is_dir
    up_level_path = os.path.dirname(path)
    ordered_directory = sorted(os.listdir(full_path), key=alphabetize)
    return render_template('filesearchbrowse.html', current_path=full_path, directory_listing=directory_listing, ordered_directory=ordered_directory, up_level_path=up_level_path)

# function to return the header of a given file
def findHeaderLine(file):
    oldline = ''
    first = True
    for line in open(file):
        if first:
            oldline = line
            first = False
        if line.startswith('#'):
            oldline = line
        else:
            return oldline

# route to go to the search parameter builder for the file search. populates the column autofill with the above function
# accessed by selecting a file on the filesearch browse page
@app.route('/filesearch/<path:path>')
def filesearch(path=None):
    header = findHeaderLine(f'/{path}')
    return render_template('filesearch.html', path=path, columns=header.strip().split('\t'))


# route to begin the filesearch using the provided parameters. returns the search preview page
# accessed by the search button on the file search page
@app.route('/filesearchbegin', methods=['POST'])
def filesearchbegin():
    # makes the name of the filesearch result
    searchname = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_filesearch_result.tsv'
    # retrieves the parameters and filename from the request
    file = request.json.get("path")
    parameters = request.json.get("params")
    print(file, parameters, sep='\n')
    columnIndex = {}
    columnType = {}
    # assume all columns are floats at first
    for param in parameters:
        columnType[param[0]] = float
    first = True
    header = ''
    bloat = findHeaderLine(file)
    # impute the datatypes
    for row in open(file, 'r'):
        line = row.strip().split('\t')
        if first:
            if not bloat == row:
                continue
            
            first = False
            header = row
            for index, col in enumerate(line):
                if col in columnType:
                    columnIndex[col] = index
            continue
        if row == header: continue # repetitive? uneccessary? bad coding????? idk not testing it (i think it accounts for a time in which i accidentally had the header written twice to files so it checks)
        # for any case where it was assumed it was a float, it fact checks it by trying to cast it and upon failure changes it to a string
        for col in columnIndex:
            value = line[columnIndex[col]]
            if value in ['-', '.']:
                value = ''
            if value == '':
                continue
            if columnType[col] == float:
                try:
                    float(value)
                except:
                    columnType[col] = str
    # actually DO COMPARISONS, remove old search result
    for old_file in os.listdir('./polarpipeline/search'):
        if old_file.endswith('_filesearch_result.tsv'):
            os.remove(os.path.join('/usr/src/app/polarpipeline/search', old_file))
    # open new search result
    with open(os.path.join('/usr/src/app/polarpipeline/search', searchname), 'w') as opened:
        opened.write(header)
        foundHeader = False
        for row in open(file, 'r'):
            # yeah see checks again here
            if row == header:
                foundHeader = True
                continue
            if foundHeader == False:
                continue
            line = row.strip().split('\t')
            valid = True
            # for each row, like the database search (see that function for more detail), appends to file if it was not disqualified by a parameter. once disqualified, it skips the row
            for param in parameters:
                if not valid: continue
                col = param[0]
                bar = param[1]
                operator = param[2]
                nas = param[3]

                value = line[columnIndex[col]]
                if value in ['-', '.']:
                    value = ''
                
                if value == '' and nas:
                    continue
                match operator:
                    case '==':
                        if columnType[col](value) != columnType[col](bar):
                            valid = False
                    case '>=':
                        if columnType[col](value) < columnType[col](bar):
                            valid = False
                    case '<=':
                        if columnType[col](value) > columnType[col](bar):
                            valid = False
                    case '>':
                        if columnType[col](value) <= columnType[col](bar):
                            valid = False
                    case '<':
                        if columnType[col](value) >= columnType[col](bar):
                            valid = False
                    case '!=':
                        if columnType[col](value) == columnType[col](bar):
                            valid = False
                    case 'Contains':
                        if str(bar) not in str(value):
                            valid = False
            if valid:
                opened.write(row)
    return 'success'

# route for the file search result
# redirected here after a successful file search (i think in the response section of the javascript on the filesearch page)
@app.route('/filesearch/preview')
def filesearchpreview():
    file = ''
    # finds a filesearch file in the search directory
    for thing in os.listdir('/usr/src/app/polarpipeline/search'):
        if thing.endswith('_filesearch_result.tsv'):
            file = os.path.join('/usr/src/app/polarpipeline/search',thing)
            break
    first = True
    filename = ''
    header = []
    filecontents = []
    # just opens the file and copies 50 lines to an array
    for line in open(file):
        if first:
            first = False
            header = line.strip().split('\t')
            for col in header:
                if 'MERGED_' in col: 
                    filename = col
            continue
        filecontents.append(line.strip().split('\t'))
        if len(filecontents) >= 50:
            # returns the 50 preview lines to the page
            return render_template('filesearchpreview.html', header=header, filecontents=filecontents, numlines=len(filecontents), filename=filename)
    # if more than 50 lines, returns all the lines
    return render_template('filesearchpreview.html', header=header, filecontents=filecontents, numlines=len(filecontents), filename=filename)

# route to download the file search result
# accessed by the download button on the filesearchpreview page
@app.route('/filesearch/download')
def filesearchdownload():
    # logging
    print('in download')
    directory = '/usr/src/app/polarpipeline/search'
    filename=''
    # finds the filesearch result file
    for file in os.listdir('/usr/src/app/polarpipeline/search'):
        if file.endswith('_filesearch_result.tsv'):
            filename = os.path.join(directory, file)
    # delivers the file to the user
    return send_file(filename, as_attachment=True)
