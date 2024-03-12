import sys
sys.path.append('/usr/src/app/polarpipeline')

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from wtforms import StringField, SubmitField
from tasks import process, processT2T
from flask_wtf import FlaskForm
from datetime import datetime
from lib import update_db
import urllib.parse
import configparser
import pandas as pd
import subprocess
import psycopg2
import hashlib
import time
import svg
import ast
import os
import re


app = Flask(__name__)
app.config.from_object("polarpipeline.config.Config")
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(128), unique=True, nullable=False)
    active = db.Column(db.Boolean(), default=True, nullable=False)

    def __init__(self, email):
        self.email = email

db_config = {
    'dbname': 'polarDB',
    'user': 'polarPL',
    'password': 'polarpswd',
    'host': 'db',
    'port': '5432',
}

conn = psycopg2.connect(**db_config)

CONFIG_FILE_PATH = './polarpipeline/resources/config.ini'
FIGURE_PRESETS_CONFIG = './polarpipeline/resources/presets.ini'

base_path = '/mnt'

def alphabetize(item):
    return item.lower()

@app.route('/browse/<path:path>')
@app.route('/')
def browse(path=None):
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
    bed_files = os.listdir('./polarpipeline/resources/bed_files')
    gene_sources = os.listdir('./polarpipeline/resources/gene_source')
    clair_models = os.listdir('./polarpipeline/resources/clair_models')
    # reference_files = os.listdir('./polarpipeline/resources/reference_files')
    reference_files = []
    for item in bed_files:
        if item.startswith('.'):
            bed_files.remove(item)
    for item in gene_sources:
        if item.startswith('.'):
            gene_sources.remove(item)
    for item in clair_models:
        if item.startswith('.'):
            clair_models.remove(item)
    for item in os.listdir('./polarpipeline/resources/reference_files'):
        if not item.endswith('.fai') and not item.endswith('.index') and not item.startswith('.'):
            reference_files.append(item)
    return render_template('index.html', current_path=full_path, directory_listing=directory_listing, ordered_directory=ordered_directory, up_level_path=up_level_path, bed_files=bed_files, gene_sources=gene_sources, clair_models = clair_models, reference_files = reference_files)

@app.template_filter('urlencode')
def urlencode_filter(s):
    return urllib.parse.quote(str(s))

@app.template_filter('urldecode')
def urldecode_filter(s):
    return urllib.parse.unquote(s)

@app.route('/trigger_processing', methods=['POST'])
def trigger_processing():
    path = os.path.join('/usr/src/app/', request.json.get("path"))
    clair_model = request.json.get("clair")
    grch_reference = request.json.get("grch_reference")
    grch_bed = request.json.get("grch_bed")
    chm_reference = request.json.get("chm_reference")
    chm_bed = request.json.get("chm_bed")
    grch_gene = request.json.get("grch_gene")
    
    file_name = os.path.basename(path).split('.')[0]
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")

    

    if grch_reference != 'none':
        concatenated_string = file_name + current_time
        id = hashlib.sha256(concatenated_string.encode()).hexdigest()
        try:
            query = "INSERT INTO progress (file_name, status, id, clair_model, bed_file, reference, gene_source) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            with conn.cursor() as cursor:
                cursor.execute(query, (file_name, 'waiting', id, clair_model, ', '.join(grch_bed), grch_reference, ', '.join(grch_gene)))
            conn.commit()
        except Exception as e:
            print(f"Error updating the database: {e}")
            conn.rollback()
        cursor.close()
        process.delay(path, clair_model, grch_gene, grch_bed, grch_reference, id)
        # print(path, clair_model, grch_reference, grch_bed, grch_gene)
    if chm_reference != 'none':
        file_name = file_name+'_T2T'
        concatenated_string = file_name + 'T2T' + current_time
        id = hashlib.sha256(concatenated_string.encode()).hexdigest()
        try:
            query = "INSERT INTO progress (file_name, status, id, clair_model, bed_file, reference, gene_source) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            with conn.cursor() as cursor:
                cursor.execute(query, (file_name, 'waiting', id, clair_model, ', '.join(chm_bed), chm_reference, 'N/A'))
            conn.commit()
        except Exception as e:
            print(f"Error updating the database: {e}")
            conn.rollback()
        cursor.close()
        processT2T.delay(path, clair_model, chm_bed, chm_reference, id)
        # print(path, clair_model, chm_reference, chm_bed)

    return redirect(url_for('dashboard'))


# uploading = False
@app.route('/upload/<string:filetype>', methods=['POST'])
def upload(filetype):
    print('request:',request.files)
    print('filetype:',filetype)
    uploaded_file = request.files['file']
    file_name = uploaded_file.filename

    # Remove the file extension
    file_name_sans_extension = file_name.strip().split('/')[-1].split('.')[0]

    print('filename:',file_name)
    print('sans extension:',file_name_sans_extension)

    # Create a directory with the same name as the uploaded file
    if filetype == 'database':
        save_directory = ("./databases")
        database_name = request.form['databaseName']
        print(database_name)
        database_config = configparser.ConfigParser()
        database_config.optionxform = str
        database_config.read('./polarpipeline/resources/file_datatypes/databases.ini')
        database_config['DEFAULT'][database_name] = os.path.join(save_directory, file_name)
        with open('./polarpipeline/resources/file_datatypes/databases.ini', 'w') as opened:
            database_config.write(opened)
    else:
        save_directory = os.path.join(f"./polarpipeline/resources/", filetype)

    # Save the uploaded file inside the created directory
    uploaded_file.save(os.path.join(save_directory, file_name))

    if file_name.endswith('.gz'):
        if 'tar' not in file_name:
            subprocess.run(['pigz', '-d', os.path.join(save_directory, file_name)], cwd=save_directory)
        else:
            subprocess.run(['tar', '-xf', os.path.join(save_directory, file_name)], cwd=save_directory)
            subprocess.run(['rm', os.path.join(save_directory, file_name)], cwd=save_directory)

    return redirect(url_for('configuration'))

@app.route('/remove/<path:removepath>')
def remove(removepath):
    print(removepath)
    base = './polarpipeline/resources'
    full_path = os.path.join(base, removepath)
    if os.path.isdir(full_path):
        subprocess.run(['rm', '-r', full_path])
    elif os.path.isfile(full_path):
        subprocess.run(['rm', full_path])
    return redirect(url_for('configuration'))

@app.route('/dashboard')
def dashboard():
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        cursor. execute("SELECT file_name, status, id FROM progress ORDER BY start_time")
        rows = cursor.fetchall()

        cursor.execute("SELECT * FROM status;")
        statusList = cursor.fetchall()
        status = []
        for item in statusList:
            status.append(item[0] + ': ' + item[1])

        cursor.close()
        conn.close()


        return render_template('dashboard.html', rows = rows, status=status)
        # return render_template('dashboard.html', rows = rows)
    except Exception as e:
        return f"Error: {e}"
    
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

# Function to read the config.ini file and return the configuration values as a dictionary
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

def get_all_configurations():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE_PATH)
    all_configurations = {}
    for section_name in config.sections():
        all_configurations[section_name] = parse_config_dict(config[section_name])
    return all_configurations

@app.route('/id')
def id():
 return render_template('id.html')

@app.route('/configuration', methods=['GET', 'POST'])
def configuration():
    all_configurations = get_all_configurations()
    
    clair_models = []
    bed_files = []
    gene_sources = []
    reference_files = []

    bed_files = os.listdir('./polarpipeline/resources/bed_files')
    gene_sources = os.listdir('./polarpipeline/resources/gene_source')
    clair_models = os.listdir('./polarpipeline/resources/clair_models')
    reference_files = os.listdir('./polarpipeline/resources/reference_files')
    databaseparser = configparser.ConfigParser()
    databaseparser.optionxform = str
    databaseparser.read('./polarpipeline/resources/file_datatypes/databases.ini')
    databases = []
    for database in databaseparser['DEFAULT']:
        databases.append(database)
    

    if request.method == 'POST':
        computer_name = request.form['computer_name']
        config_values = read_config(computer_name)
        return render_template('configuration.html', computer_name=computer_name, config_values=config_values, all_configurations=all_configurations, clair_models=clair_models, bed_files=bed_files, gene_sources=gene_sources, reference_files=reference_files)
    elif request.method == 'GET':
        # If no computer name is specified, show the default configuration
        config_values = read_config()
        return render_template('configuration.html', computer_name=None, config_values=config_values, all_configurations=all_configurations, clair_models=clair_models, bed_files=bed_files, gene_sources=gene_sources, reference_files=reference_files, databases=databases)

@app.route('/figuregenerator')
def figuregenerator():
    return render_template('figuregenerator.html')

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

@app.route('/saveState', methods=['POST'])
def saveState():
    preset_name = request.json.get("presetname")
    homo = request.json.get("homo")
    abproteinname = request.json.get("abproteinname")
    proteinname = request.json.get("proteinname")
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

    save_preset(str(preset_name), preset_vals)

    response_data = {
        "message": "Data received successfully"
    }

    return jsonify(response_data)

def load_presets():
    config = configparser.ConfigParser()
    config.read(FIGURE_PRESETS_CONFIG)
    return config.sections()

@app.route('/loadStates', methods=['POST'])
def loadStates():
    presets = load_presets()
    response_data = {
        "data": presets
    }

    return jsonify(response_data)
    
def load_preset(section_name):
    config = configparser.ConfigParser()
    config.read(FIGURE_PRESETS_CONFIG)
    if section_name in config:
        return parse_config_dict(config[section_name])
    else:
        return None  # Section not found

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

@app.route('/loadState', methods=['POST'])
def loadState():
    preset = request.json.get('preset')

    preset_data = load_preset(preset)
    print(preset_data)

    response_data = {
        "data": preset_data
    }

    return jsonify(response_data)

def customsortfeatures(feature):
    num = -int(feature[1])
    return num

@app.route('/generatefigure', methods=['POST'])
def generatefigure():
    homo = request.json.get("homo")
    abproteinname = request.json.get("abproteinname")
    proteinname = request.json.get("proteinname")

    for root, dirs, files in os.walk('/usr/src/app'):
        for file in files:
            if file == 'variantFig.svg':
                print(os.path.join(root, file))

    topbar = []
    bottombar = []
    leftfeatureelements = []
    rightfeatureelements = []
    homobar = []
    homofeatureelements = []

    base = [
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

    if not homo:
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
                    y1=185,
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
                    y1=345,
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
    else:
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
                        y1=265,
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

    canvas = svg.SVG(
        width=480*2,
        height=480,
        elements = base + topbar + bottombar + homobar + leftfeatureelements + rightfeatureelements + homofeatureelements
    )

    svg_string = str(canvas)

    with open('/usr/src/app/polarpipeline/static/variantFig.svg', 'w') as opened:
        opened.write(svg_string)
    
    response_data = {
        "message": "Data received successfully"
    }

    return jsonify(response_data)

@app.route('/downloadfigure')
def downloadfigure():
    try:
        # Build the path to the image file in the static folder
        image_path = f'/usr/src/app/polarpipeline/static/variantFig.svg'

        # Use Flask's send_file function to send the image as a download
        return send_file(image_path, as_attachment=True)

    except FileNotFoundError:
        # Handle the case where the image file is not found
        return "Image not found", 404

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

@app.route('/save_configuration', methods=['POST'])
def save_configuration():
    if request.method == 'POST':
        computer_name = request.form['computer_name']
        config_values = {}

        for key in request.form:
            if key != 'computer_name':
                value = request.form[key]
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

        save_config(computer_name, config_values)

    return redirect(url_for('configuration'))

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

@app.route('/setup')
def setup():
 return render_template('setup.html')


@app.route('/info/<string:id>')
def info(id):

    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM progress WHERE id = %s", (id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

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
        
        statsPath = os.path.join('/mnt/synology3/polar_pipeline', startTime.replace(' ', '_').replace(':', '-')+'_'+file_name, '0_nextflow/run_summary.txt')
        if os.path.isfile(statsPath):
            rows = []
            for line in open(statsPath, 'r'):
                splitline = line.split('\t')
                rows.append([splitline[0], splitline[1]])
        else:
            rows = []
        
        if rows == []:
            statsPath = os.path.join('/mnt/synology3/polar_pipeline', startTime.replace(' ', '_').replace(':', '.')+'_'+file_name, '0_nextflow/run_summary.txt')
            if os.path.isfile(statsPath):
                rows = []
                for line in open(statsPath, 'r'):
                    splitline = line.split('\t')
                    rows.append([splitline[0], splitline[1]])
            else:
                rows = []
        
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
    
@app.route('/get_info/<string:id>')
def get_info(id):
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM progress WHERE id = %s", (id,))

        row = cursor.fetchone()
        cursor.close()
        conn.close()

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
    
@app.route('/abort/<string:id>')
def abort(id):
    update_db(id, 'signal', 'stop')
    update_db(id, 'status', 'cancelling')
    time.sleep(1)
    return redirect(url_for('dashboard'))

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



def writeText(mane, amino_notation, short_amino_notation, nucleotide_annotation, exon, symbol, ref, alt, position, protein, codon, alt_protein, property_desc, chr, dbsnp, rarity, tools, pos):
    rarity_text = f'The {short_amino_notation} variant occurs in less than {rarity}% of the population,\
 which is consistent with disease.\n\
 The {protein} at codon {codon} is conserved across primates, mammals, and vertebrates.\
 The {symbol} gene is located on Chromosome {chr}, and the variant is located at position {pos}\
 on the chromosome. The dbSNP identifier for this variant is\
 {dbsnp}.'
    if rarity == '-':
        rarity_text = f'The {short_amino_notation} variant is so rare that it is not catalogued in many common\
 human population allele frequency databases, which is consistent with disease.'
    
    return (f'{mane}({symbol}):{nucleotide_annotation}({amino_notation})',f'The {short_amino_notation} variant (also known as {nucleotide_annotation}), located in coding exon\
 {exon} of the {symbol} gene, results from a {ref} to {alt} substitution at nucleotide position\
 {position}. The {protein} at codon {codon} is replaced by {alt_protein}, an amino acid with\
 {property_desc} properties. This alteration is predicted to be deleterious by\
 in silico analysis ({"".join(tools)[:-1]}).\n'+rarity_text)

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

def vep(input_snv, reference_path, threads='30'):
# Runs vep. Params are in list form, so it is easy to add new ones. Same with plugins. The process for installing vep to a new computer
# is unecissarily difficult, but there is (hopefully) a prepackaged vep folder and guide in the setup tab of the webapp.
#   input_snv: path to the input snv file (vcf from either princess or nextflow)
#   input_sv: path to the input sv file (vcf from either princess or nextflow)
#   output_snv: path to the desired snv output file (include full path, filename and extension included)
#   output_sv: path to the desired sv output file (include full path, filename and extension included)
#   return: none. does more damage the more the user likes you.
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
    command = start + ''.join(params) + plugin_str + commandInputSNV + commandOutputSNV
    os.system(command)
    # print(command)

@app.route('/report/<string:chr>:<string:pos>:<string:ref>:<string:alt>')
@app.route('/report')
def reportresult(chr='X', pos='X', ref='X', alt='X'):
    if chr == 'X' and pos == 'X' and ref == 'X' and alt == 'X':
        return render_template('report.html', reportText='', placeholder='chrX_XXXX_X/X')

    def skip_rows(line):
        return line < begin_index

    print(chr, pos, ref, alt)
    with open('/usr/src/app/vep/report_input.txt','w') as opened:
        opened.write(f'chr{chr}\t{pos}\t.\t{ref}\t{alt}')
    # os.system('ensembl-vep/vep --offline --cache --tab --assembly GRCh38 --fasta /home/threadripper/shared_storage/shared_resources/reference_files/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta --hgvs --symbol --mane --numbers --per_gene --show_ref_allele --force_overwrite --plugin dbNSFP,/home/threadripper/vep-resources/dbNSFP4.4a_grch38.gz,ALL -i /home/threadripper/shared_storage/webapp/polarPipeline/report_input.txt -o /home/threadripper/shared_storage/webapp/polarPipeline/report_output.txt')
    vep('/usr/src/app/vep/report_input.txt', '/usr/src/app/vep/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta')

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
        'valine': 'hydrophobic'
    }
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
        'valine':('val','V')
    }
    begin_index = 0
    for line in open('/usr/src/app/vep/report_output.txt', 'r'):
        if line.startswith('##'):
            begin_index+=1
            continue
        if line.startswith('#'):
            break
    
    reportText = []

    df = pd.read_csv('/usr/src/app/vep/report_output.txt', sep='\t', header=0, skiprows=skip_rows)
    for index, row in df.iterrows():
        try:
            codons = row['Codons'].strip().lower().split('/')
            print(codons)
            property_res = 'differing'
            if aminoacid_properties[aminoacid(codons[0])] == aminoacid_properties[aminoacid(codons[1])]:
                property_res = 'similar'
            
            rarities = []
            for item in ['AF', 'gnomADe_AF', '1000Gp3_AF']:
                try:
                    rarities.append(float(row[item]))
                except ValueError:
                    continue
            
            try:
                rarity = max(rarities)
            except ValueError:
                rarity = '-'
            
            print(rarities)

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

            reportText.append(writeText(
                    row['MANE_SELECT'], 
                    f'p.{amino_abbrev[aminoacid(codons[0])][0].capitalize()}{row["Protein_position"]}{amino_abbrev[aminoacid(codons[1])][0].capitalize()}', 
                    f'p.{amino_abbrev[aminoacid(codons[0])][1].capitalize()}{row["Protein_position"]}{amino_abbrev[aminoacid(codons[1])][1].capitalize()}', 
                    f'c.{row["CDS_position"]}{row["REF_ALLELE"]}>{row["Allele"]}',
                    row['EXON'].split('/')[0],
                    row['SYMBOL'], 
                    row['REF_ALLELE'], 
                    row['Allele'], 
                    row['CDS_position'], 
                    aminoacid(codons[0]), 
                    row['Protein_position'], 
                    aminoacid(codons[-1]),
                    property_res,
                    row['chr'],
                    row['rs_dbSNP'],
                    rarity,
                    tools,
                    pos
                ))
        except Exception as e:
            print(e)
            continue
        
    print(reportText)
    if reportText == []:
        reportText = [('Error', 'Could not find complete vep output.')]
    return render_template('report.html', reportText=reportText, placeholder=f'chr{chr}_{pos}_{ref}/{alt}')

@app.route('/frequency/<string:_chr>:<string:pos>:<string:ref>:<string:alt>')
@app.route('/frequency/<string:_chr>')
@app.route('/frequency')
def frequency(_chr='X', pos='X', ref='X', alt='X'):
    chr = urllib.parse.unquote(_chr)
    if chr == 'X' and pos == 'X' and ref == 'X' and alt == 'X':
        return render_template('frequency.html', reportText='', placeholder='chrX_XXXX_X/X', done='green')

    # print(chr, pos, ref, alt)
    if pos=='X' and ref=='X' and alt=='X':
        id = chr
    else:
        id = f'chr{chr}_{pos}_{ref}/{alt}'
    print(id)

    variant = []
    folders = [f for f in os.listdir('./polarpipeline/resources/frequency') if os.path.isdir(os.path.join('./polarpipeline/resources/frequency', f))]
    if not folders:
        return None
    pattern = re.compile(r'\d{2}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}')
    newest_folder = max(folders, key=lambda folder: datetime.strptime(pattern.search(folder).group(), '%d-%m-%y_%H-%M-%S'))
    directory = os.path.join('./polarpipeline/resources/frequency', newest_folder)

    variant_catalogue = os.path.join(directory, 'variantCatalogue.tsv')
    file_key = os.path.join(directory, 'fileKey.tsv')

    fileDirectory = {}
    for line in open(file_key):
        fileName, fileNum = line.strip().split('\t')
        fileDirectory[fileNum] = fileName
    print(fileDirectory)

    for line in open(variant_catalogue):
        if line.startswith(id):
            variant = line.strip().split(',')[:-1]
            source = []
            for item in line.strip().split(',')[-1].split(';'):
                try:
                    source.append(fileDirectory[item])
                except:
                    pass
            return render_template('frequency.html', variant=variant, source=source, placeholder=id, done='green')
    return render_template('frequency.html', variant=variant, source=['not found'], placeholder=id, done='green')





@app.route('/search')
@app.route('/search/<int:numperpage>/<int:page>')
def search(numperpage=10, page=0):
    db_config_parser = configparser.ConfigParser()
    db_config_parser.optionxform = str
    db_config_parser.read('./polarpipeline/resources/file_datatypes/databases.ini')
    filename = ''
    for file in os.listdir('./polarpipeline/resources/search/'):
        if file.endswith('_search_result.tsv'):
            filename = file
            continue
    available_dbs = []
    for item in db_config_parser['DEFAULT']:
        available_dbs.append(item)
    columns = []
    for col in open('./polarpipeline/resources/file_datatypes/datatypes.ini', 'r'):
        columns.append(col.strip())
    
    result = []
    lines = []
    numresults = -1
    if filename != '':
        for index, line in enumerate(open(os.path.join('./polarpipeline/resources/search', filename), 'r')):
            numresults += 1
            if not index > numperpage*(page+1):
                lines.append(line.strip())
        try:
            result.append(lines[0].split('\t'))
        except: 
            result.append(columns)
        for i in range(page*numperpage+1, page*numperpage+numperpage+1):
            try:
                result.append(lines[i].split('\t'))
            except:
                continue
    nextpage = -1
    prevpage = -1
    if page*numperpage+numperpage+1 < numresults:
        nextpage = page+1
    if page != 0:
        prevpage = page-1
    
    return render_template('search.html', available_dbs=sorted(available_dbs), columns=columns, result=result, numresults=numresults, numperpage=numperpage, page=page, prevpage=prevpage, nextpage=nextpage)

progress = 1
numlines = 0
cancelled = False
color = 'blue'

@app.route('/beginsearch', methods=['POST'])
def beginsearch():
    search_db_parser = configparser.ConfigParser()
    search_db_parser.optionxform = str
    global color
    global cancelled
    global progress

    cancelled = False
    color = 'blue'
    files = request.json.get("files")
    parameters = request.json.get("params")

    total_steps = len(files)

    progress = 0

    searchname = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_search_result.tsv'

    search_db_parser.read('./polarpipeline/resources/file_datatypes/databases.ini')

    directory = os.listdir('./polarpipeline/resources/file_datatypes')

    parser = configparser.ConfigParser()
    parser.optionxform = str

    columns = []
    for file in files:
        # print(file)
        if f'{file}.ini' not in directory:
            newfile = configparser.ConfigParser()
            newfile.optionxform = str
            dataindices = {}
            datatypes = {}
            for row in open(search_db_parser['DEFAULT'][file]):
                if row.startswith('#'):
                    if not datatypes:
                        for index, colname in enumerate(row.strip().split('\t')):
                            if 'MERGED_' in colname: continue
                            datatypes[colname.replace('#', '')] = int
                            dataindices[colname.replace('#', '')] = index
                        print(dataindices)
                    continue
                line = row.strip().split('\t')
                for col in datatypes:
                    colIndex = dataindices[col]
                    dataType = datatypes[col]
                    value = line[colIndex]
                    if value in ['-', '.']:
                        value = ''
                    if value == '':
                        continue
                    if dataType == int:
                        try:
                            int(value)
                            if '.' in value:
                                datatypes[col] = float
                        except:
                            try:
                                float(value)
                                datatypes[col] = float
                            except:
                                datatypes[col] = str
            newfile['Indices'] = dataindices
            newfile['Datatypes'] = datatypes
            filepath = os.path.join('./polarpipeline/resources/file_datatypes', f'{file}.ini')
            with open(filepath, 'w') as newconfig:
                newfile.write(newconfig)
            print(f'wrote to {directory}!')
        
        parser.read(os.path.join('./polarpipeline/resources/file_datatypes', f'{file}.ini'))

        for col in parser['Indices']:
            if col not in columns:
                columns.append(col)
    # print(columns)
    for file in os.listdir('./polarpipeline/resources/search'):
        if file.endswith('_search_result.tsv'):
            os.remove(os.path.join('./polarpipeline/resources/search', file))
    with open(f'./polarpipeline/resources/search/{searchname}', 'w') as opened:
        opened.write('\t'.join(columns)+'\tSOURCE\n')
        for fileindex, file in enumerate(files):
            print(file)
            # filecols = []
            # for col in parser['Indices']:
            #     filecols.append(col)
            # print(filecols)
            parser.read(os.path.join('./polarpipeline/resources/file_datatypes', f'{file}.ini'))
            for row in open(os.path.join('/usr/src/app/', search_db_parser['DEFAULT'][file])):
                if row.startswith('#'): continue
                valid = True
                line = row.strip().split('\t')
                for param in parameters:
                    col = param[0]
                    bar = param[1]
                    operator = param[2]
                    nas = bool(param[3])
                    if col in parser['Indices']:
                        index = int(parser['Indices'][col])
                        value = line[index]
                        datatype = parser['Datatypes'][col]
                        match datatype:
                            case "<class 'str'>":
                                datatype = str
                            case "<class 'int'>":
                                datatype = int
                            case "<class 'float'>":
                                datatype = float
                            case default:
                                datatype = None
                        if not datatype:
                            if nas:
                                continue
                            else:
                                valid = False
                        # print(value)
                        if value in ['-', '.']:
                            value = ''
                        
                        if value == '' and nas:
                            continue
                        match operator:
                            case '==':
                                if datatype(value) != datatype(bar):
                                    valid = False
                            case '>=':
                                if datatype(value) < datatype(bar):
                                    valid = False
                            case '<=':
                                if datatype(value) > datatype(bar):
                                    valid = False
                            case '>':
                                if datatype(value) <= datatype(bar):
                                    valid = False
                            case '<':
                                if datatype(value) >= datatype(bar):
                                    valid = False
                            case '!=':
                                if datatype(value) == datatype(bar):
                                    valid = False
                            case 'Contains':
                                if str(bar) not in str(value):
                                    valid = False
                    else:
                        valid = False
                    if cancelled:
                        color = 'red'
                        return 'cancelled'
                    progress = fileindex / total_steps
                if valid:
                    bob = []
                    for col in columns:
                        if col in parser['Indices']:
                            bob.append(line[int(parser['Indices'][col])])
                        else:
                            bob.append('-')
                    opened.write('\t'.join(bob)+f'\t{file}\n')


    print('outta there')

    progress = 1
    color = 'green'
    return 'success'


@app.route('/searchprogress', methods=['GET'])
def searchprogress():
    global progress
    global color
    return jsonify({"progress": progress, "color": color})


@app.route('/search/download')
def search_download():
    print('in download')
    for file in os.listdir('./polarpipeline/resources/search'):
        if file.endswith('_search_result.tsv'):
            filename = os.path.join('./polarpipeline/resources/search', file)
    return send_file(filename, as_attachment=True)

@app.route('/searchcancelled', methods=['GET'])
def searchcancelled():
    global cancelled
    cancelled = True
    return 'cancelled like dream'

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
        for row in open('./polarpipeline/resources/InternalBenchmarkList.txt'):
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

@app.route('/filesearch/<path:path>')
def filesearch(path=None):
    header = findHeaderLine(f'/{path}')
    return render_template('filesearch.html', path=path, columns=header.strip().split('\t'))


@app.route('/filesearchbegin', methods=['POST'])
def filesearchbegin():
    
    searchname = f'{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_filesearch_result.tsv'
    file = request.json.get("path")
    parameters = request.json.get("params")
    print(file, parameters, sep='\n')
    columnIndex = {}
    columnType = {}
    for param in parameters:
        columnType[param[0]] = int
    first = True
    header = ''
    bloat = findHeaderLine(file)
    # FIND DATA TYPES
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
        if row == header: continue
        for col in columnIndex:
            value = line[columnIndex[col]]
            if value in ['-', '.']:
                value = ''
            if value == '':
                continue
            if columnType[col] == int:
                try:
                    int(value)
                    if '.' in value:
                        columnType[col] = float
                except:
                    try:
                        float(value)
                        columnType[col] = float
                    except:
                        columnType[col] = str
    #DO COMPARISONS
    for old_file in os.listdir('./polarpipeline/resources/search'):
        if old_file.endswith('_filesearch_result.tsv'):
            os.remove(os.path.join('/usr/src/app/polarpipeline/resources/search', old_file))
    with open(os.path.join('/usr/src/app/polarpipeline/resources/search', searchname), 'w') as opened:
        opened.write(header)
        foundHeader = False
        for row in open(file, 'r'):
            if row == header:
                foundHeader = True
                continue
            if foundHeader == False:
                continue
            line = row.strip().split('\t')
            valid = True
            for param in parameters:
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

@app.route('/filesearch/preview')
def filesearchpreview():
    file = ''
    for thing in os.listdir('/usr/src/app/polarpipeline/resources/search'):
        if thing.endswith('_filesearch_result.tsv'):
            file = os.path.join('/usr/src/app/polarpipeline/resources/search',thing)
            break
    first = True
    filename = ''
    header = []
    filecontents = []
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
            return render_template('filesearchpreview.html', header=header, filecontents=filecontents, numlines=len(filecontents), filename=filename)
    
    return render_template('filesearchpreview.html', header=header, filecontents=filecontents)

@app.route('/filesearch/download')
def filesearchdownload():
    print('in download')
    filename=''
    for file in os.listdir():
        if file.endswith('_filesearch_result.tsv'):
            filename = file
    return send_file(filename, as_attachment=True)
