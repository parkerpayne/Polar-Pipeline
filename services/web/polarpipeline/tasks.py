import sys
sys.path.append('/usr/src/app/polarpipeline')

from celery import Celery
# from lib import *
import time
import sys
import os
import configparser
import subprocess
from datetime import datetime

setup_parser = configparser.ConfigParser()
setup_parser.read('/usr/src/app/polarpipeline/resources/config.ini')
ip = setup_parser['Network']['host_ip']


app = Celery('tasks', broker=f'pyamqp://guest:guest@{ip}:5672/')

@app.task
def process(input_file_path, output_path, clair_model_name, gene_source_name, bed_file_name, reference_file_name, id):
    pass


@app.task
def processT2T(input_file_path, output_path, clair_model_name, bed_file_name, reference_file_name, id):
    pass
