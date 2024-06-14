import subprocess
import re
import os
import math
import psycopg2
import shutil
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from bs4 import BeautifulSoup
import configparser


# returns the username of the machine executing this function
def whoami():
    completed_process = subprocess.run(['whoami'], text=True, capture_output=True)
    return completed_process.stdout.strip()

# read from config to get the ip of the web server
setup_parser = configparser.ConfigParser()
setup_parser.read('/mnt/pipeline_resources/config.ini')
ip = setup_parser['Network']['host_ip']

#  __          ________ ____      _____ ______ _______      ________ _____                                             
#  \ \        / /  ____|  _ \    / ____|  ____|  __ \ \    / /  ____|  __ \                                            
#   \ \  /\  / /| |__  | |_) |  | (___ | |__  | |__) \ \  / /| |__  | |__) |                                           
#    \ \/  \/ / |  __| |  _ <    \___ \|  __| |  _  / \ \/ / |  __| |  _  /                                            
#     \  /\  /  | |____| |_) |   ____) | |____| | \ \  \  /  | |____| | \ \                                            
#    __\/_ \/___|______|____/_ _|_____/|______|_|__\_\__\/___|______|_| _\_\_  _____ _______ _____ ____  _   _  _____ 
#   / ____|  __ \|  ____/ ____|_   _|  ____|_   _/ ____| |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |/ ____|
#  | (___ | |__) | |__ | |      | | | |__    | || |      | |__  | |  | |  \| | |       | |    | || |  | |  \| | (___  
#   \___ \|  ___/|  __|| |      | | |  __|   | || |      |  __| | |  | | . ` | |       | |    | || |  | | . ` |\___ \ 
#   ____) | |    | |___| |____ _| |_| |     _| || |____  | |    | |__| | |\  | |____   | |   _| || |__| | |\  |____) |
#  |_____/|_|    |______\_____|_____|_|    |_____\_____| |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|_____/ 
#   Functions needed specifically for the web server pipeline. These are called in tasks.py.                                                                                                              


def update_db(id, col, value):
# Used to update the database values.
#   id: file/row id. Generated in app.py.
#   col: column to update the value of
#   value: value to insert
#   returns: nothing. silence. probably not for the best.
    conn = connect()
    try:
        query = "UPDATE progress SET {} = %s WHERE id = %s".format(col)
        with conn.cursor() as cursor:
            cursor.execute(query, (value, id))
        conn.commit()
    except Exception as e:
        print(f"Error updating the database: {e}")
        conn.rollback()
    cursor.close()

def checksignal(id):
# Used to check if the run has been cancelled. Is called periodically throughout tasks.py.
#   id: file/row id. Generated in app.py
#   returns: current signal value in the database for given id
    conn = connect()
    try:
        # Create a cursor to execute SQL queries
        cursor = conn.cursor()

        # Query the database for the signal value based on the given id
        query = f"SELECT signal FROM progress WHERE id = '{id}'"
        cursor.execute(query)

        # Fetch the result
        signal = cursor.fetchone()

        if signal and signal[0] == 'stop':
            return 'stop'
        else:
            return 'continue'
    except:
        return 'error'
    finally:
        # Close the cursor
        cursor.close()

def abort(work_dir, id):
# Called in the event of database being cancelled. I could've called this in the checksignal function but I put it in tasks.py.
#   work_dir: working directory, where all the in-process files are being kept.
#   id: file/row id. Generated in __init__.py
#   returns: whether the working directory was successfully removed or not
    update_db(id, 'status', 'cancelled')
    update_db(id, 'end_time', datetime.now())
    command = f'rm -r {work_dir}'
    os.system(command)
    if os.path.isdir(work_dir):
        return 'failure'
    return 'success'

def dashListKey(input):
    return input[1]

#   _    _ _   _ _______      ________ _____   _____         _        ______ _    _ _   _  _____ _______ _____ ____  _   _  _____ 
#  | |  | | \ | |_   _\ \    / /  ____|  __ \ / ____|  /\   | |      |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |/ ____|
#  | |  | |  \| | | |  \ \  / /| |__  | |__) | (___   /  \  | |      | |__  | |  | |  \| | |       | |    | || |  | |  \| | (___  
#  | |  | | . ` | | |   \ \/ / |  __| |  _  / \___ \ / /\ \ | |      |  __| | |  | | . ` | |       | |    | || |  | | . ` |\___ \ 
#  | |__| | |\  |_| |_   \  /  | |____| | \ \ ____) / ____ \| |____  | |    | |__| | |\  | |____   | |   _| || |__| | |\  |____) |
#   \____/|_| \_|_____|   \/   |______|_|  \_\_____/_/    \_\______| |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|_____/                                                                                                                 
                                                                                                                                
def load_file(file_name):
# Used to load files into ram.
#   file_name: file path (confusing, i know. sorry.)
#   returns: a list containing all rows in the file
    file = []
    with open(file_name, 'r') as opened:
        for line in opened:
            file.append(line)
    return file

def getColumns(inputfile):
# Used to automate the generation of index values for columns. 
#   returns a dictionary with keys equaling column header names and values equaling corresponding index numbers.
    f = open(inputfile)
    headers = f.readline()
    columns = {}
    for index, item in enumerate(headers.strip().split()):
        columns[item.strip()] = index
    f.close()
    return columns


def connect():
    db_config = {
        'dbname': 'polarDB',
        'user': 'polarPL',
        'password': 'polarpswd',
        'host': ip,
        'port': '5432',
    }
    return psycopg2.connect(**db_config)



#   _____ __  __ _____   ____  _____ _______   ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  |_   _|  \/  |  __ \ / __ \|  __ \__   __| |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#    | | | \  / | |__) | |  | | |__) | | |    | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#    | | | |\/| |  ___/| |  | |  _  /  | |    |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#   _| |_| |  | | |    | |__| | | \ \  | |    | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_____|_|  |_|_|     \____/|_|  \_\ |_|    |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|


def samtoolsImport(input_file):
# Used to convert fastqs into unaligned bam files. unzips if the original file is zipped, zips original file after conversion into bam.
#   input_file: input file path
#   returns: new filepath of the bam, or False if it fails.
    try:
        run_name = input_file.strip().split('/')[-1].split('.fastq')[0]
        working_path = '/'.join(input_file.strip().split('/')[:-1])
        if input_file.endswith('.fastq.gz'):
            process = subprocess.Popen(["pigz", "-dk", run_name+".fastq.gz"], cwd=working_path)
            stdout, stderr = process.communicate()
        process = subprocess.Popen(["samtools", "import", "-@", "30" "-0", run_name+".fastq", "-o", run_name+".bam"], cwd=working_path)
        stdout, stderr = process.communicate()
        
        process = subprocess.Popen(["rm", run_name+".fastq"], cwd=working_path)
        stdout, stderr = process.communicate()
        return os.path.join(working_path, run_name+'.bam')
    except:
        return False

#   __  __ _____ _   _ _____ __  __          _____    ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  |  \/  |_   _| \ | |_   _|  \/  |   /\   |  __ \  |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#  | \  / | | | |  \| | | | | \  / |  /  \  | |__) | | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#  | |\/| | | | | . ` | | | | |\/| | / /\ \ |  ___/  |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#  | |  | |_| |_| |\  |_| |_| |  | |/ ____ \| |      | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_|  |_|_____|_| \_|_____|_|  |_/_/    \_\_|      |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|
                                                                                                                                                                              

def minimap2(input_path, reference_path, threads='30'):
    root = input_path.split('.fastq')[0]
    minimap_command = f'minimap2 -y -t {threads} -ax map-ont {reference_path} {root}.fastq > {root}.sam'
    os.system(minimap_command)
    return f"{root}.sam"

#  __      _______ ________          __    _____  ____  _____ _______    _____ _   _ _____  ________   __
#  \ \    / /_   _|  ____\ \        / /   / ____|/ __ \|  __ \__   __|  |_   _| \ | |  __ \|  ____\ \ / /
#   \ \  / /  | | | |__   \ \  /\  / /   | (___ | |  | | |__) | | |       | | |  \| | |  | | |__   \ V / 
#    \ \/ /   | | |  __|   \ \/  \/ /     \___ \| |  | |  _  /  | |       | | | . ` | |  | |  __|   > <  
#     \  /   _| |_| |____   \  /\  /      ____) | |__| | | \ \  | |      _| |_| |\  | |__| | |____ / . \ 
#      \/   |_____|______|   \/  \/      |_____/ \____/|_|  \_\ |_|     |_____|_| \_|_____/|______/_/ \_\
                                                                                                       
                                                                                                       
def viewSortIndex(input_path, threads='30'):
    root = input_path.split('.sam')[0].split('.bam')[0]

    if input_path.endswith('.sam'):
        view_command = f'samtools view -@ {threads} -bo {root}.bam {root}.sam'
        os.system(view_command)
        input_path = f'{root}.sam'
        # print(view_command)

    sort_command = f'samtools sort -m 2G -o {root}_sorted.bam -@ {threads} {root}.bam'
    os.system(sort_command)
    # print(sort_command)

    index_command = f'samtools index -b -@ {threads} -o {root}_sorted.bam.bai {root}_sorted.bam'
    os.system(index_command)
    # print(index_command)

    for file in [f'{root}.sam', f'{root}.bam']:
        if os.path.isfile(file):
            os.remove(file)
    # print(rm_command)

    shutil.move(f'{root}_sorted.bam', f'{root}.bam')
    # rename_bam = f'mv {root}_sorted.bam {root}.bam'
    # os.system(rename_bam)
    shutil.move(f'{root}_sorted.bam.bai', f'{root}.bam.bai')
    # rename_bam_bai = f'mv {root}_sorted.bam.bai {root}.bam.bai'
    # os.system(rename_bam_bai)

    return f"{root}.bam"

#   _   _ ________   _________ ______ _      ______          __  ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  | \ | |  ____\ \ / /__   __|  ____| |    / __ \ \        / / |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#  |  \| | |__   \ V /   | |  | |__  | |   | |  | \ \  /\  / /  | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#  | . ` |  __|   > <    | |  |  __| | |   | |  | |\ \/  \/ /   |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#  | |\  | |____ / . \   | |  | |    | |___| |__| | \  /\  /    | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_| \_|______/_/ \_\  |_|  |_|    |______\____/   \/  \/     |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|

#  ---------------------------------------------------------------------------------------------------------------
#  VERSION 2.2.3 (SNIFFLES DOES NOT COMPLETE?)
#  ---------------------------------------------------------------------------------------------------------------

# def nextflow(input_file, output_directory, reference_file, clair3_model_path, threads='30'):
# # Function to run the epi2me nextflow workflow. Assumes nextflow is installed into path.
# #   input_file: input file path
# #   output_directory: what folder the output and workspace folders will be generated in
# #   reference_file: full path to the reference file being used
# #   clair3_model_path: full path to the clair3 model folder
#     run_name = os.path.basename(input_file).split('.bam')[0].split('.fastq')[0]
#     command = f"nextflow run epi2me-labs/wf-human-variation -r v2.2.3 \
#         --out_dir {output_directory}/output \
#         -w {output_directory}/workspace \
#         -profile standard \
#         --snp \
#         --sv \
# 	      --str \
#         --cnv \
#         --bam {input_file} \
#         --ref {reference_file} \
#         --bam_min_coverage 0.01 \
#         --snp_min_af 0.25 \
#         --indel_min_af 0.25 \
#         --min_cov 10 \
#         --min_qual 10 \
#         --sex=\"XY\" \
#         --sample_name {run_name} \
#         --clair3_model_path {clair3_model_path} \
#         --depth_intervals \
#         --phased \
#         --threads {threads} \
#         --ubam_map_threads {math.floor(int(threads)/3)} \
#         --ubam_sort_threads {math.floor(int(threads)/3)} \
#         --ubam_bam2fq_threads {math.floor(int(threads)/3)} \
#         --disable_ping"
#     try:
#         os.system(command)
#         return True
#     except:
#         return False

# def y_nextflow(input_file, output_directory, reference_file, clair3_model_path, threads='30'):
#     run_name = os.path.basename(input_file).split('.bam')[0].split('.fastq')[0]
#     # run_name = input_file.strip().split('/')[-1].split('.bam')[0].split('.fastq')[0]
#     command = f"nextflow run epi2me-labs/wf-human-variation -r v2.2.3 \
#         --out_dir {output_directory}/output \
#         -w {output_directory}/workspace \
#         -profile standard \
#         --sv \
#         --bam {input_file} \
#         --ref {reference_file} \
#         --annotation=\"false\" \
#         --skip-annotation \
#         --bam_min_coverage 0.01 \
#         --snp_min_af 0.25 \
#         --indel_min_af 0.25 \
#         --min_cov 10 \
#         --min_qual 10 \
#         --sample_name {run_name} \
#         --clair3_model_path {clair3_model_path} \
#         --depth_intervals \
#         --phased \
#         --threads {threads} \
#         --ubam_map_threads {math.floor(int(threads)/3)} \
#         --ubam_sort_threads {math.floor(int(threads)/3)} \
#         --ubam_bam2fq_threads {math.floor(int(threads)/3)} \
#         --disable_ping"
#     try:
#         os.system(command)
#         return True
#     except:
#         return False


#  ---------------------------------------------------------------------------------------------------------------
#  VERSION 1.8.1
#  ---------------------------------------------------------------------------------------------------------------

def nextflow(input_file, output_directory, reference_file, clair3_model_path, threads='30'):
# Function to run the epi2me nextflow workflow. Assumes nextflow is installed into path.
#   input_file: input file path
#   output_directory: what folder the output and workspace folders will be generated in
#   reference_file: full path to the reference file being used
#   clair3_model_path: full path to the clair3 model folder
    run_name = os.path.basename(input_file).replace('.bam', '')
    command = f"nextflow run epi2me-labs/wf-human-variation -r v1.8.2 \
        --out_dir {output_directory}/output \
        -w {output_directory}/workspace \
        -profile standard \
        --snp \
        --sv \
	    --str \
        --cnv \
        --bam {input_file} \
        --ref {reference_file} \
        --bam_min_coverage 0.01 \
        --sv_types DEL,INS,DUP,INV,BND \
        --snp_min_af 0.25 \
        --indel_min_af 0.25 \
        --min_cov 10 \
        --min_qual 10 \
        --sex=\"male\" \
        --sample_name {run_name} \
        --clair3_model_path {clair3_model_path} \
        --depth_intervals \
        --phase_vcf \
        --phase_sv \
        --threads {math.floor(int(threads)/2)} \
        --ubam_map_threads {math.floor(int(threads)/3)} \
        --ubam_sort_threads {math.floor(int(threads)/3)} \
        --ubam_bam2fq_threads {math.floor(int(threads)/3)} \
        --merge_threads {math.floor(int(threads)/2)} \
        --annotation_threads {math.floor(int(threads)/2)} \
        --disable_ping"
    try:
        os.system(command)
        return True
    except:
        return False

def y_nextflow(input_file, output_directory, reference_file, clair3_model_path, threads='30'):
    run_name = os.path.basename(input_file).replace('.bam', '')
    command = f"nextflow run epi2me-labs/wf-human-variation -r v1.8.2 \
        --out_dir {output_directory}/output \
        -w {output_directory}/workspace \
        -profile standard \
        --sv \
        --bam {input_file} \
        --ref {reference_file} \
        --annotation=\"false\" \
        --skip-annotation \
        --bam_min_coverage 0.01 \
        --sv_types DEL,INS,DUP,INV,BND \
        --snp_min_af 0.25 \
        --indel_min_af 0.25 \
        --min_cov 10 \
        --min_qual 10 \
        --sample_name {run_name} \
        --clair3_model_path {clair3_model_path} \
        --depth_intervals \
        --phase_vcf \
        --phase_sv \
        --threads {threads} \
        --ubam_map_threads {math.floor(int(threads)/3)} \
        --ubam_sort_threads {math.floor(int(threads)/3)} \
        --ubam_bam2fq_threads {math.floor(int(threads)/3)} \
        --merge_threads {threads} \
        --disable_ping"
    try:
        os.system(command)
        return True
    except:
        return False

#    _____ ______ _____        _____         _______ ______             _   _______ _____ 
#   / ____|  ____|  __ \ /\   |  __ \     /\|__   __|  ____|      /\   | | |__   __/ ____|
#  | (___ | |__  | |__) /  \  | |__) |   /  \  | |  | |__        /  \  | |    | | | (___  
#   \___ \|  __| |  ___/ /\ \ |  _  /   / /\ \ | |  |  __|      / /\ \ | |    | |  \___ \ 
#   ____) | |____| |  / ____ \| | \ \  / ____ \| |  | |____    / ____ \| |____| |  ____) |
#  |_____/|______|_| /_/    \_\_|  \_\/_/    \_\_|  |______|  /_/    \_\______|_| |_____/ 
                                                                                        
                                                                                        
def parseAlts(evilstinkynogoodline):
# Function to take lines with multiple alts and separate them into two different lines.
#   evilstinkynogoodline: a potential threat. must be scrutinized.
#   returns: array of good lines. passed inspection. will not need brainwashing.

    # turns row into a bunch of variables
    chrm, pos, id, ref, alt, qual, fltr, info, frmt, traits = evilstinkynogoodline.strip().split('\t')
    goodlines = []
    # commas in both mean theres two alts in the row
    if ',' in alt and ',' in traits:
        # i have only seen 2 alts in a row but i wrote it so it can handle more just in case
        for i in range(len(alt.strip().split(','))):
            traitlist = []
            # comments below brought to you by ai because i literally cannot remember how it works and it is confusing to me
            for j in range(len(frmt.strip().split(':'))):
                # Check if the number of traits matches the number of alts
                if len(traits.strip().split(':')[j].split(',')) == len(alt.strip().split(',')):
                    # Append the trait corresponding to the current alternate allele to the trait list
                    traitlist.append(traits.strip().split(':')[j].split(',')[i])
                # Handle the case when AD format field has one more element than the number of alternate alleles
                elif (len(traits.strip().split(':')[j].split(',')) == len(alt.strip().split(','))+1 and frmt.strip().split(':')[j] == "AD"):
                    # Combine the first element with the corresponding alternate allele's element
                    traitlist.append(','.join([traits.strip().split(':')[j].split(',')[0], traits.strip().split(':')[j].split(',')[i+1]]))
                else:
                    # If no match is found, append the trait as is
                    traitlist.append(traits.strip().split(':')[j])
            # Append the fixed line to the list of good lines
            goodlines.append('\t'.join([chrm, pos, id, ref, alt.strip().split(',')[i], qual, fltr, info, frmt, ':'.join(traitlist)])+'\n')
    else:
        # If there's no need for separation, return the original line
        goodlines.append(evilstinkynogoodline)
    return goodlines


#  __      ________ _____    ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  \ \    / /  ____|  __ \  |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#   \ \  / /| |__  | |__) | | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#    \ \/ / |  __| |  ___/  |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#     \  /  | |____| |      | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#      \/   |______|_|      |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|
                                                                                
                                                                                
def vep(input_vcf, reference_path, threads='30', output_snv='output'):
# Runs vep. Params are in list form, so it is easy to add new ones. Same with plugins. The process for installing vep to a new computer
# is unecissarily difficult, but there is (hopefully) a prepackaged vep folder and guide in the setup tab of the webapp.
#   input_snv: path to the input snv file (vcf from either princess or nextflow)
#   input_sv: path to the input sv file (vcf from either princess or nextflow)
#   output_snv: path to the desired snv output file (include full path, filename and extension included)
#   output_sv: path to the desired sv output file (include full path, filename and extension included)
#   return: none. does more damage the more the user likes you.

    pc_name = whoami()
    # run_name = os.path.join(input_sv).split('.wf_')[0]
    run_name = os.path.basename(input_vcf).split('.vcf')[0]
    input_dir = os.path.dirname(os.path.abspath(input_vcf))
    output_name = os.path.join(input_dir, run_name+"_vep.tsv")

    start = f'vep --offline --cache --tab --everything --assembly GRCh38 --fasta {reference_path} --fork {threads} --buffer_size 20000'
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
        f' --plugin LoFtool,/home/{pc_name}/vep-resources/LoFtool_scores.txt',
        f' --plugin Mastermind,/home/{pc_name}/vep-resources/mastermind_cited_variants_reference-2023.04.02-grch38.vcf.gz',
        f' --plugin CADD,/home/{pc_name}/vep-resources/whole_genome_SNVs.tsv.gz',
        f' --plugin Carol',
        f' --plugin Condel,/home/{pc_name}/.vep/Plugins/config/Condel/config',
        f' --plugin pLI,/home/{pc_name}/vep-resources/pLI_values.txt',
        f' --plugin PrimateAI,/home/{pc_name}/vep-resources/PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz',
        f' --plugin dbNSFP,/home/{pc_name}/vep-resources/dbNSFP4.8a_grch38.gz,ALL',
        f' --plugin REVEL,/home/{pc_name}/vep-resources/new_tabbed_revel_grch38.tsv.gz',
        f' --plugin AlphaMissense,file=/home/{pc_name}/vep-resources/AlphaMissense_hg38.tsv.gz',
        f' --plugin EVE,file=/home/{pc_name}/vep-resources/eve_merged.vcf.gz',
        f' --plugin DisGeNET,file=/home/{pc_name}/vep-resources/all_variant_disease_pmid_associations_final.tsv.gz'
    ]
    if pc_name == "prom":
        plugins = [
        f' --plugin LoFtool,/data/vep-resources/LoFtool_scores.txt',
        f' --plugin Mastermind,/data/vep-resources/mastermind_cited_variants_reference-2023.04.02-grch38.vcf.gz',
        f' --plugin CADD,/data/vep-resources/whole_genome_SNVs.tsv.gz',
        f' --plugin Carol',
        f' --plugin Condel,/data/.vep/Plugins/config/Condel/config',
        f' --plugin pLI,/data/vep-resources/pLI_values.txt',
        f' --plugin PrimateAI,/data/vep-resources/PrimateAI_scores_v0.2_GRCh38_sorted.tsv.bgz',
        f' --plugin dbNSFP,/data/vep-resources/dbNSFP4.8a_grch38.gz,ALL',
        f' --plugin REVEL,/data/vep-resources/new_tabbed_revel_grch38.tsv.gz',
        f' --plugin AlphaMissense,file=/data/vep-resources/AlphaMissense_hg38.tsv.gz',
        f' --plugin EVE,file=/data/vep-resources/eve_merged.vcf.gz',
        f' --plugin DisGeNET,file=/data/vep-resources/all_variant_disease_pmid_associations_final.tsv.gz'
    ]
    
    commandInputSNV = f' -i {input_vcf}'
    if output_snv == 'output':
        commandOutputSNV = ' -o ' + output_name
    else:
        commandOutputSNV = f' -o {output_snv}'

    command = start + ''.join(params) + ''.join(plugins) + commandInputSNV + commandOutputSNV
    print(f'starting vep for {input_vcf}...')
    os.system(command)

    print('vep complete!')
    return output_name

#    _____ ____  _    _ _   _ _______   _______ ____   ____  _       _____ 
#   / ____/ __ \| |  | | \ | |__   __| |__   __/ __ \ / __ \| |     / ____|
#  | |   | |  | | |  | |  \| |  | |       | | | |  | | |  | | |    | (___  
#  | |   | |  | | |  | | . ` |  | |       | | | |  | | |  | | |     \___ \ 
#  | |___| |__| | |__| | |\  |  | |       | | | |__| | |__| | |____ ____) |
#   \_____\____/ \____/|_| \_|  |_|       |_|  \____/ \____/|______|_____/      
#    ___   
#   ( _ )  
#   / _ \/\
#  | (_>  <
#   \___/\/       
#    _____ ______ _   _ ______    _____  ____  _    _ _____   _____ ______ 
#   / ____|  ____| \ | |  ____|  / ____|/ __ \| |  | |  __ \ / ____|  ____|
#  | |  __| |__  |  \| | |__    | (___ | |  | | |  | | |__) | |    | |__   
#  | | |_ |  __| | . ` |  __|    \___ \| |  | | |  | |  _  /| |    |  __|  
#  | |__| | |____| |\  | |____   ____) | |__| | |__| | | \ \| |____| |____ 
#   \_____|______|_| \_|______| |_____/ \____/ \____/|_|  \_\\_____|______|
                                                                         
                                                                  
def buildGeneSourceDict(geneSourceFile):
# Creates a dictionary with keys equaling the gene symbols and values equaling the source. the files are custom made.
# function is called in the addToolsColumn_addGeneSource function.
#   geneSourceFile: LOADED (from load_file function) file containing gene symbols and corresponding source
#   returns: dictionary containing the same info as the input just in a dictionary (for O(1) calls! wow!)
    gene_dict = {}
    for line in geneSourceFile:
        tabbed_line = line.strip().split('\t')
        gene_dict[tabbed_line[0]] = tabbed_line[1]
    return gene_dict

# Old code to add gene symbols to variants that did not have them. Was told to do it, then not to. Not currently used. leaving it here in case the mind gets changed again
# def addSymbols(inputfile, inputbed):
#     outputfile = []
#     columns = getColumns(inputfile)
#     for line in inputfile:
#         tabline = line.split('\t')
#         chr = tabline[columns['#CHROM']]
#         symbol = tabline[columns['SYMBOL']]
#         if line.strip().startswith('#'):
#             outputfile.append(line)
#             continue

#         start = tabline[columns['#START']]
#         stop = tabline[columns['#STOP']]

#         bedsymbol = lookup(inputbed, chr, start, stop)

#         if bedsymbol == '-':
#             bedsymbol = '-'

#         if symbol == '-':
#             tabline[columns['SYMBOL']] = bedsymbol

#         newline = '\t'.join(tabline)
#         outputfile.append(newline)
#     return outputfile

def addToolsColumn(bed_file, output):
# This function does two things (adds an SV/SNV column and tool info), probably should have split it up but it avoids an extra loop through the file. It first determines 
# if a tool considers a variant dangerous (deliterious? idk) and if it does it adds it to a total and to a list, then adds both of those to the file in separate columns. 
# This allows for both a ballpark estimate as to how bad a variant is as well as knowing what tools were to blame for that accusation. (how rude of them!)
#   bed_file: LOADED (using the load_file function) input file. i don't know why i called it bed file, probably because it is in bed format at this point.
#   gene_source_file: LOADED (using the load_file function) gene source file. 
#   returns: whole file with added columns for number of tools claiming deliterious on a variant and the tools themselves(the jury perhaps?)
    with open(output, 'w') as opened:
        columns = getColumns(bed_file)
        for line in open(bed_file, 'r'):
            tabbed_line = line.strip().split('\t')
            if line.strip().startswith('#'):
                opened.write('\t'.join(tabbed_line[:columns['QUAL']] + ['SV_SNV', 'NUM_TOOLS', 'TOOLS'] + tabbed_line[columns['QUAL']:])+'\n')
                continue
            start = tabbed_line[:columns['QUAL']]
            gene = tabbed_line[columns['SYMBOL']]
            id = tabbed_line[columns['ID']]
            tools = []
            info = tabbed_line[columns['QUAL']:]
            tools.append('IM,' if 'HIGH' in tabbed_line[columns['IMPACT']] else '')
            tools.append('SF,' if 'deleterious' in tabbed_line[columns['SIFT']] else '')
            tools.append('PP,' if 'probably_damaging' in tabbed_line[columns['PolyPhen']] else '')
            tools.append('CS,' if 'likely_pathogenic' in tabbed_line[columns['CLIN_SIG']] else '')
            tools.append('CD,' if tabbed_line[columns['CADD_PHRED']] != '-' and float(tabbed_line[columns['CADD_PHRED']]) >= 20 else '')
            tools.append('CR,' if 'Deleterious' in tabbed_line[columns['CAROL']] else '')
            tools.append('CL,' if 'deleterious' in tabbed_line[columns['Condel']] else '')
            tools.append('CP,' if 'D' in tabbed_line[columns['ClinPred_pred']] else '')
            tools.append('DN,' if tabbed_line[columns['DANN_score']] != '-' and float(tabbed_line[columns['DANN_score']]) >= 0.96 else '')
            tools.append('DG,' if 'D' in tabbed_line[columns['DEOGEN2_pred']] else '')
            tools.append('FM,' if 'D' in tabbed_line[columns['FATHMM_pred']] else '')
            tools.append('LS,' if 'D' in tabbed_line[columns['LIST-S2_pred']] else '')
            tools.append('LR,' if 'D' in tabbed_line[columns['LRT_pred']] else '')
            tools.append('ML,' if 'D' in tabbed_line[columns['MetaLR_pred']] else '')
            tools.append('MA,' if 'H' in tabbed_line[columns['MutationAssessor_pred']] else '')
            tools.append('MT,' if 'D' in tabbed_line[columns['MutationTaster_pred']] else '')
            tools.append('PR,' if 'D' in tabbed_line[columns['PROVEAN_pred']] else '')
            tools.append('PD,' if 'D' in tabbed_line[columns['Polyphen2_HDIV_pred']] else '')
            tools.append('PV,' if 'D' in tabbed_line[columns['Polyphen2_HVAR_pred']] else '')
            tools.append('PA,' if 'D' in tabbed_line[columns['PrimateAI_pred']] else '')
            tools.append('S4,' if 'D' in tabbed_line[columns['SIFT4G_pred']] else '')
            tools.append('RV,' if tabbed_line[columns['REVEL']] != '-' and float(tabbed_line[columns['REVEL']]) > 0.75  else '')
            tools.append('AM,' if 'likely_pathogenic' in tabbed_line[columns['am_class']] else '')
            tools.append('EV,' if 'Pathogenic' in tabbed_line[columns['EVE_CLASS']] else '')
            num_tools = int(len(''.join(tools).replace(',',''))/2)

            # i was told to set tools to 6 for SVs because they dont get detected by the prediction tools
            if 'Snif' not in id:
                snv_or_sv = 'SNV'
            else:
                num_tools = 6
                snv_or_sv = 'SV'
            # commas are attached to the tool ID rather than being used in the join bc he said "i can use the commas to count the number of tools" which is true
            built_line = '\t'.join(start + [snv_or_sv] + [str(num_tools)] + [''.join(tools)] + info)+'\n'
            opened.write(built_line)

    return 'success'

def addGeneSource(input, output, gene_source_file):
    # set up resources 
    columns = getColumns(input)
    gene_source = buildGeneSourceDict(gene_source_file)

    with open(output, 'w') as output_file:
        for line in open(input, 'r'):
            tabbed_line = line.strip().split('\t')
            # if line is header, write header to output file
            if line.strip().startswith('#'):
                output_file.write('\t'.join(tabbed_line[:columns['QUAL']] + ['GENE_SOURCE'] + tabbed_line[columns['QUAL']:])+'\n')
                continue
            # gets the row prior to column insertion, the gene to use with the dictionary, and the line after the column insertion
            start = tabbed_line[:columns['QUAL']]
            gene = tabbed_line[columns['SYMBOL']]
            info = tabbed_line[columns['QUAL']:]
            if gene in gene_source:
                gene_source_info = gene_source[gene]
            else:
                gene_source_info = '-'
            # combines the row prior to insertion, the column to insert, and the row after insertion
            built_line = '\t'.join(start + [gene_source_info] + info)+'\n'
            output_file.write(built_line)
    return output



#   _____  ______ __  __  ______      ________   _____  _    _ _____  ______ _____    _____   ______          _______ 
#  |  __ \|  ____|  \/  |/ __ \ \    / /  ____| |  __ \| |  | |  __ \|  ____|  __ \  |  __ \ / __ \ \        / / ____|
#  | |__) | |__  | \  / | |  | \ \  / /| |__    | |  | | |  | | |__) | |__  | |  | | | |__) | |  | \ \  /\  / / (___  
#  |  _  /|  __| | |\/| | |  | |\ \/ / |  __|   | |  | | |  | |  ___/|  __| | |  | | |  _  /| |  | |\ \/  \/ / \___ \ 
#  | | \ \| |____| |  | | |__| | \  /  | |____  | |__| | |__| | |    | |____| |__| | | | \ \| |__| | \  /\  /  ____) |
#  |_|  \_\______|_|  |_|\____/   \/   |______| |_____/ \____/|_|    |______|_____/  |_|  \_\\____/   \/  \/  |_____/ 


def collapseDuplicateRows(inputfile, output):
# This function was made to combat a specific issue we were having where there would be sometimes hundreds of duplicate rows in the output files,
# only difference between them being in like 4 columns in the middle. This function 'squashes' these rows by combining rows that only differ in these
# columns. The differences are kept by listing them all in their corresponding columns, so that if someone wanted to (hasnt happened yet) they could
# delimit these 4 columns and recover all of the original repeated rows.
#   inputfile: self explanatory
#   returns: whole file with dupe rows squashed
    
    # Initialize a dictionary to store combined rows
    combined_rows = {}
    columns = getColumns(inputfile)
    # Initialize the last chromosome processed
    last_chrom = 'chr1'

    with open(output, 'w') as combined_output:
        for line in open(inputfile, 'r'):
            if line.strip().startswith('#'):
                # Write header lines to the output file
                combined_output.write(line)
                continue
            tabbed_line = line.strip().split('\t')
            # Generate a key based on specified columns for grouping
            key = ('.'.join(tabbed_line[:columns['Gene']] + tabbed_line[columns['cDNA_position']:]))
            # Check if the key exists in the combined rows dictionary
            if key in combined_rows:
                # Combine values for duplicate keys
                combined_rows[key][columns['Gene']] = ','.join([combined_rows[key][columns['Gene']], tabbed_line[columns['Gene']]])
                combined_rows[key][columns['Feature']] = ','.join([combined_rows[key][columns['Feature']], tabbed_line[columns['Feature']]])
                combined_rows[key][columns['Feature_type']] = ','.join([combined_rows[key][columns['Feature_type']], tabbed_line[columns['Feature_type']]])
                combined_rows[key][columns['Consequence']] = ','.join([combined_rows[key][columns['Consequence']], tabbed_line[columns['Consequence']]])
            else:
                # Add new key-value pair to the combined rows dictionary
                combined_rows[key] = tabbed_line
            # Check if the chromosome has changed
            curr_chrom = tabbed_line[columns['#CHROM']]
            if not last_chrom == curr_chrom:
                # Write combined rows to the output file and reset dictionary to lower memory usage
                last_chrom = curr_chrom
                for key in combined_rows:
                    combined_output.write('\t'.join(combined_rows[key]) + '\n')
                    combined_rows[key] = []
                combined_rows = {}
    return 'success'


#   __  __ ______ _____   _____ ______    ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  |  \/  |  ____|  __ \ / ____|  ____|  |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#  | \  / | |__  | |__) | |  __| |__     | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#  | |\/| |  __| |  _  /| | |_ |  __|    |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#  | |  | | |____| | \ \| |__| | |____   | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_|  |_|______|_|  \_\\_____|______|  |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|
#

def parse_vep_id(line):
# Parses the given line to create a unique id for it. (basically, if one is provided, uses it, if not, joins together chr, pos, ref and alt to make one)
#   line: yardyno
#   returns: id, either string or tuple depending on if an id existed prior
    if '_' not in line[0]:
        return line[0]
    chr = line[0].split('_')[0]
    pos = int(line[0].split('_')[1])
    ref = str(line[0].split('_')[2].split('/')[0])
    alt = ','.join(line[0].split('_')[2].split('/')[1:])
    ref = ref.replace('-', '')
    alt = alt.replace('-', '')
    return (chr, pos, ref, alt)

# variant from sniffles
class SFVariant:
    def __init__(self, CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, FORMATVALS):
        self.chrom = CHROM
        self.pos = POS
        if REF == '':
            self.ref = '-'
        else:
            self.ref = REF
        self.id = ID
        if ALT == '':
            self.alt = '-'
        else:
            self.alt = ALT
        self.qual = QUAL
        self.filter = FILTER
        self.info = {}
        for col in INFO.split(';'):
            if col in ['PRECISE', 'IMPRECISE']:
                self.info['PRECISION'] = col
            else:
                key, val = col.split('=')
                self.info[key] = val
        self.format = {}
        for index, datatype in enumerate(FORMAT):
            self.format[datatype] = FORMATVALS[index]

# variant from snipeff (wf-human-variation)
class NFVariant:
    def __init__(self, CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, FORMATVALS):
        self.chrom = CHROM
        self.pos = POS
        if REF == '':
            self.ref = '-'
        else:
            self.ref = REF
        self.id = ID
        if ALT == '':
            self.alt = '-'
        else:
            self.alt = ALT
        self.qual = QUAL
        self.filter = FILTER
        self.info = INFO
        self.format = {}
        for index, datatype in enumerate(FORMAT):
            self.format[datatype] = FORMATVALS[index]


def mergeFiles(nextflow_snv, nextflow_sv, vep_snv, vep_sv, output='output'):
    print('merging begin. preprocessing nextflow output')
    # Initialize a dictionary to store variants
    variants = {}

    # Initialize lists for merged header, Sniffles columns, and format columns
    merged_header = []
    snf_cols = []
    fmt_cols = []

    for nextflow_input in [nextflow_snv, nextflow_sv]:
        for line in open(nextflow_input):
            # Process header lines
            if line.startswith('#'):
                if line.startswith('#CHROM'):
                    for item in line.strip().split('\t'):
                        if (not item[:20] == os.path.basename(nextflow_input)[:20]) and (not item == 'FORMAT'):
                            if item not in merged_header:
                                merged_header.append(item)
                                if item == '#CHROM':
                                    merged_header += ['START', 'STOP']
                continue
            else:
                # Parse variant information
                variant = line.strip().split('\t')
                CHROM = variant[0]
                POS = int(variant[1])
                ID = variant[2]
                REF = variant[3]
                ALT = variant[4]
                QUAL = variant[5]
                FILTER = variant[6]
                INFO = variant[7]
                FORMAT = variant[8].split(':')
                FORMATVALS = variant[9].split(':')

                # Adjust position and alleles if REF and ALT start with the same nucleotide
                # (wf-human-variation includes preceding nucleotide and adjusts position by 1 to account for it, vep does not. this unifies them)
                if REF[0] == ALT[0]:
                    REF = REF[1:]
                    ALT = ALT[1:]
                    POS += 1

                # Create variant objects based on tool (Sniffles or Nextflow)
                if 'Sniffles' in ID:
                    currvar = SFVariant(CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, FORMATVALS)
                    for col in INFO.split(';'):
                        real_col = col.split('=')[0]
                        if col in ['PRECISE', 'IMPRECISE']:
                            real_col = 'PRECISION'
                        if col == 'AF':
                            real_col = 'SV_AF'
                        if real_col not in snf_cols:
                            snf_cols.append(real_col)
                else:
                    currvar = NFVariant(CHROM, POS, ID, REF, ALT, QUAL, FILTER, INFO, FORMAT, FORMATVALS)
                
                # Update format columns list
                for col in FORMAT:
                    if col not in fmt_cols:
                        fmt_cols.append(col)

                # Extract internal IDs and store variants in the dictionary
                internal_ids = []
                if not ID == '.':
                    for variant_id in ID.split(';'):
                        internal_ids.append(variant_id)
                else:
                    internal_ids.append((CHROM, POS, REF, ALT))
                for internal_id in internal_ids:
                    variants[internal_id] = currvar

    # Update merged header with format and Sniffles columns
    merged_header += fmt_cols + snf_cols

    print('preprocessing complete. merging')

    # Initialize list to store final output lines
    final_output = []

    # Open output file for writing if a specific output file is provided
    if not output == 'output':
        f = open(output, 'w')

    headered = False
    for vep_input in [vep_snv, vep_sv]:
        # Process each line in the VEP input file
        for line in open(vep_input):
            # Write header lines to output file
            if line.startswith('#'):
                if line.startswith('#Uploaded'):
                    if not headered:
                        headered = True
                        # Append additional header information to merged header
                        merged_header += line.strip().split('\t')
                        # Write merged header to output file
                        f.write('\t'.join(merged_header)+'\n')
                continue

            # Parse variant information into fields
            variant = line.strip().split('\t')

            # Extract internal ID from VEP input
            internal_id = parse_vep_id(variant)
            # Initialize list to store new line data
            newline = []
            # Parse variant position
            pos = variant[1].split(':')[-1].split('-')
            match len(pos):
                case 1:
                    start = pos[0]
                    stop = pos[0]
                case 2:
                    start, stop = pos
            # Get Nextflow data for current variant
            nfdata = variants[internal_id]
            # Calculate values depending on the type of variant (snv or sv)
            if 'Sniffles' in nfdata.id:
                info_val = '-'
                DR = nfdata.format['DR']
                DV = nfdata.format['DV']
                DP = str(float(DR) + float(DV))
                snf_vals = {}
                for col in snf_cols:
                    if col in nfdata.format:
                        snf_vals[col] = nfdata.format[col]
                    else:
                        snf_vals[col] = '-'
            else:
                info_val = nfdata.info
                DP = nfdata.format['DP']
                AF = nfdata.format['AF']
                dvs = []
                drs = []
                for subaf in AF.split(','):
                    dvs.append(str(int(float(DP) * float(subaf))))
                    drs.append(str(int(float(DP) * (1-float(subaf)))))
                DV = ','.join(dvs)
                DR = ','.join(drs)
                snf_vals = {}
                for col in snf_cols:
                    snf_vals[col] = '-'
            # Construct new line data
            newline += [nfdata.chrom, start, stop, nfdata.pos, nfdata.id, nfdata.ref, nfdata.alt, nfdata.qual, nfdata.filter, info_val]
            for col in fmt_cols:
                match col:
                    case 'DR':
                        newline.append(DR)
                    case 'DV':
                        newline.append(DV)
                    case 'DP':
                        newline.append(DP)
                    case default:
                        if col in nfdata.format:
                            newline.append(nfdata.format[col])
                        else:
                            newline.append('-')
            newline += [snf_vals[col] for col in snf_vals]
            newline += variant
            
            # Write line to output file if a specific output file is provided
            if not output == 'output':
                f.write('\t'.join(map(str, newline))+'\n')
            else:
                final_output.append('\t'.join(map(str, newline))+'\n')

    # Close output file if a specific output file is provided
    f.close()
    print('merge complete!')
    return final_output


#   _____ _   _ _______ ______ _____   _____ ______ _____ _______ _____ ____  _   _ 
#  |_   _| \ | |__   __|  ____|  __ \ / ____|  ____/ ____|__   __|_   _/ __ \| \ | |
#    | | |  \| |  | |  | |__  | |__) | (___ | |__ | |       | |    | || |  | |  \| |
#    | | | . ` |  | |  |  __| |  _  / \___ \|  __|| |       | |    | || |  | | . ` |
#   _| |_| |\  |  | |  | |____| | \ \ ____) | |___| |____   | |   _| || |__| | |\  |
#  |_____|_| \_|  |_|  |______|_|  \_\_____/|______\_____|  |_|  |_____\____/|_| \_|


# intersect file with bed file using bedtools intersect. can output to an array or to a file
def intersect(file, bed, output='output'):
    intersection = []
    completed_process = subprocess.run(['bedtools', 'intersect', '-header', '-u', '-a', file, '-b', bed], text=True, capture_output=True)
    for line in completed_process.stdout.strip().split('\n'):
        intersection.append(line)
    if output != 'output':
        with open(output, 'w') as opened:
            opened.write('\n'.join(intersection))
        
    return intersection


def qcReport(file_path):
    # Initialize dictionary to store QC data
    qcData = {}
    # Open the QC report file using BeautifulSoup
    with open(file_path) as fp:
        qcreport = BeautifulSoup(fp, 'html.parser')

    # Find the table containing QC metrics
    table = qcreport.find("table")
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        metric = columns[0].text
        value = columns[1].text
        
        # For each row, store metric and value in the QC data dictionary
        qcData[metric] = value

    # Find charts in the QC report
    pattern = re.compile(r"EZChart_.+")
    charts = qcreport.find_all(id=pattern)
    # Iterate through each chart
    for chart in charts:
        # Extract chart information
        chartText = str(chart)
        # Check if the chart is related to read quality
        if "Read quality" in chartText:
            # Extract and store read quality metrics
            info = chartText.split("'subtext': '")[1].split("'")[0]
            for item in info.split('. '):
                qcData['Read quality ' + item.lower().split(': ')[0]] = item.lower().split(': ')[1]
        # Check if the chart is related to read length
        elif "Read length" in chartText and 'yield' not in chartText:
            # Extract and store read length metrics
            info = chartText.split("'subtext': '")[1].split("'")[0]
            for item in info.split('. '):
                qcData['Read length ' + item.lower().split(': ')[0]] = item.lower().split(': ')[1]
        # Check if the chart is related to mapping accuracy
        elif "Mapping accuracy" in chartText:
            # Store mapping accuracy information
            info = chartText.split("'subtext': '")[1].split("'")[0]
            qcData['Mapping accuracy'] = info
        # Check if the chart is related to read coverage
        elif "Read coverage" in chartText:
            # Store read coverage information
            info = chartText.split("'subtext': '")[1].split("'")[0]
            qcData['Read coverage'] = info

    # Find the div with id starting with ParamsTable in the QC report
    pattern = re.compile(r"ParamsTable_.+")
    table = qcreport.find(id=pattern)
    # Iterate through each row in the parameter table
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        # Check if the row contains information about threads
        if columns != [] and columns[0].text == 'threads':
            # Store thread information
            qcData['Threads'] = columns[1].text
    # Return the QC data dictionary
    return qcData

def cnvReport(file_path):
    # Initialize dictionary to store CNV data
    cnvData = {}

    # Open the CNV report file using BeautifulSoup
    with open(file_path) as fp:
        cnvreport = BeautifulSoup(fp, 'html.parser')

    # Find the parent div starting with "Grid"
    pattern = re.compile(r"Grid_.+")
    parent_div = cnvreport.find(id=pattern)

    # Extract data from child divs within the parent div
    for child_div in parent_div.find_all('div', class_='container'):
        # Extract header and value from each child div
        header = child_div.find('h3', class_='h5').text.strip()
        value = child_div.find('p', class_='fs-2').text.strip()

        # Check if value ends with 'bp' and adjust header accordingly
        if value.endswith('bp'):
            header = header + ' (bp)'
            value = value.replace('bp', '')
        # Store header and value in the CNV data dictionary
        cnvData[header] = value

    # Find the table in html
    table = cnvreport.find("table")
    # Iterate through each column in the table
    for i in range(len(table.find_all("td"))):
        # Extract metric and value from each column
        metric = table.find_all("th")[i].text
        value = table.find_all("td")[i].text.strip().replace('\n', ',')
        # Store metric and value in the CNV data dictionary
        cnvData[metric] = value

    # Find the table containing version information
    table = cnvreport.find(id="versions")
    # Iterate through each row in the version table
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        # Check if the row contains information
        if columns != []:
            # Extract metric and value from each row
            metric = columns[0].text
            value = columns[1].text
            # Store metric and value in the CNV data dictionary
            cnvData[metric] = value
    # Return the CNV data dictionary
    return cnvData

def snpReport(file_path):
    # Initialize dictionary to store SNP data
    snpData = {}
    # Open the SNP report file using BeautifulSoup
    with open(file_path) as fp:
        snpreport = BeautifulSoup(fp, 'html.parser')

    # Find the parent div with id starting with "Grid"
    pattern = re.compile(r"Grid_.+")
    parent_div = snpreport.find(id=pattern)

    # Extract data from child divs within the parent div
    for child_div in parent_div.find_all('div', class_='container'):
        header = child_div.find('h3', class_='h5').text.strip()
        value = child_div.find('p', class_='fs-2').text.strip()
        # Store header and value in the SNP data dictionary
        snpData[header] = value

    # Find the table containing version information
    table = snpreport.find(id="versions")
    # Iterate through each row in the version table
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        # Check if the row contains information
        if columns != []:
            # Extract metric and value from each row
            metric = columns[0].text
            value = columns[1].text
            # Store metric and value in the SNP data dictionary
            snpData[metric] = value
    # Return the SNP data dictionary
    return snpData

def svReport(file_path):
    # Initialize dictionary to store SV data
    svData = {}
    # Open the SV report file using BeautifulSoup
    with open(file_path) as fp:
        svreport = BeautifulSoup(fp, 'html.parser')

    # Find the parent div with id starting with "Grid"
    pattern = re.compile(r"Grid_.+")
    parent_div = svreport.find(id=pattern)

    # Extract data from child divs within the parent div
    for child_div in parent_div.find_all('div', class_='container'):
        # Extract header and value from each child div
        header = child_div.find('h3', class_='h5').text.strip()
        value = child_div.find('p', class_='fs-2').text.strip()

        # Store header and value in the SV data dictionary
        svData[header] = value

    # Find the table containing SV types and their data
    pattern = re.compile(r"DataTable_.+")
    table = svreport.find(id=pattern)
    
    # Extract SV types from the table headers
    sv_types = []
    for item in table.find_all("tr"):
        if sv_types == []:
            for header in item.find_all("th"):
                sv_types.append(header.text)
            sv_types = sv_types[1:] # Skip the first header which is not a SV type
    
    # Iterate through SV types and their data in the table
    for i in range(len(sv_types)):
        for j in range(1, len(table.find_all("tr"))): # Start from index 1 to skip the header row
            # Store the SV data in the dictionary
            svData[sv_types[i] + '_' + table.find_all("tr")[j].find("th").text.replace('. ', '_')] = table.find_all("tr")[j].find_all("td")[i].text
            # print(sv_types[i] + '_' + table.find_all("tr")[j].find("th").text.replace('. ', '_'), table.find_all("tr")[j].find_all("td")[i].text)

    # Find the table containing version information
    table = svreport.find(id="versions")
    # Iterate through each row in the version table
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        # Check if the row contains information
        if columns != []:
            # Extract metric and value from each row
            metric = columns[0].text
            value = columns[1].text
            # Store metric and value in the SV data dictionary
            svData[metric] = value
    # Return the SV data dictionary
    return svData
    
def reportReport(file_path):
    # Initialize dictionary to store report data
    reportData = {}
    # Open the report file using BeautifulSoup
    with open(file_path) as fp:
        reportreport = BeautifulSoup(fp, 'html.parser')
    
    # Extract Nextflow command from the report
    command = reportreport.find("pre", class_="nfcommand")
    reportData['Nextflow command'] = command.text

    # Extract clair3 model path from the Nextflow command
    clairModel = command.text.split('--clair3_model_path ')[1].split(' ')[0].split('/')[-1]
    reportData['clair3 model'] = clairModel

    # Extract PC name from the Nextflow command
    pc_name = command.text.split('/home/')[1].split('/')[0]
    reportData['PC name'] = pc_name

    # Extract CPU hours from the report
    cpuHours = reportreport.find("dd", class_="col-sm-9").text
    reportData['CPU hours'] = cpuHours

    # Return the report data dictionary
    return reportData

def coverageReport(file_path):
    # Initialize an empty list to store coverage values
    coverageArray = []
    # Read coverage values from the file and append to coverage array
    for line in open(file_path):
        coverageArray.append(float(line.strip().split('\t')[3]))
    # Calculate median and mean coverage
    median = statistics.median(coverageArray)
    mean = statistics.mean(coverageArray)
    # Create a dictionary to store coverage data
    coverageData = {'Median coverage': str(median), 'Mean coverage': str(mean)}
    # Return the coverage data dictionary
    return coverageData

def createRunSummary(output, alignment, cnv, snp, sv, report, coverage):
    with open(os.path.join(output, 'run_summary.txt'), 'w') as opened:

        if snp != 'none':
            # If SNP data is available, extract and write QC, CNV, SNP, SV, report, and coverage data
            qcData = qcReport(alignment)
            cnvData = cnvReport(cnv)
            snpData = snpReport(snp)
            svData = svReport(sv)
            reportData = reportReport(report)
            coverageData = coverageReport(coverage)
            # Write the name of the run to the file
            opened.write('Name'+'\t'+output.split('/')[-2]+'\n')
            # Write QC data to the file
            for item in qcData:
                opened.write(item+'\t'+qcData[item]+'\n')
            # Write CNV data to the file
            for item in cnvData:
                opened.write(item+'\t'+cnvData[item]+'\n')
            # Write SNP data to the file
            for item in snpData:
                opened.write(item+'\t'+snpData[item]+'\n')
            # Write SV data to the file
            for item in svData:
                opened.write(item+'\t'+svData[item]+'\n')
            # Write report data to the file
            for item in reportData:
                opened.write(item+'\t'+reportData[item]+'\n')
            # Write coverage data to the file
            for item in coverageData:
                opened.write(item+'\t'+coverageData[item]+'\n')
        else:
            # If SNP data is not available, extract and write QC, SV, report, and coverage data
            qcData = qcReport(alignment)
            svData = svReport(sv)
            reportData = reportReport(report)
            coverageData = coverageReport(coverage)
            # Write the name of the run to the file
            opened.write('Name'+'\t'+output.split('/')[-2]+'\n')
            # Write QC data to the file
            for item in qcData:
                opened.write(item+'\t'+qcData[item]+'\n')
            # Write SV data to the file
            for item in svData:
                opened.write(item+'\t'+svData[item]+'\n')
            # Write report data to the file
            for item in reportData:
                opened.write(item+'\t'+reportData[item]+'\n')
            # Write coverage data to the file
            for item in coverageData:
                opened.write(item+'\t'+coverageData[item]+'\n')

def vcftobed(inputpath):
    # Initialize lists and indices
    header = [] # Store header lines
    output = [] # Store processed VCF lines
    format = []  # Store FORMAT field
    refIndex = 0  # Index of REF field in VCF
    altIndex = 0  # Index of ALT field in VCF
    formatIndex = 0  # Index of FORMAT field in VCF

    # Read VCF file line by line
    for line in open(inputpath, 'r'):
        # Store header lines
        if line.startswith('##'):
            header.append(line)
        elif line.startswith('#'):
            # Process header line to get field indices
            tabbed = line.split('\t')
            for i in range(len(tabbed)):
                if tabbed[i] == "REF":
                    refIndex = i
                if tabbed[i] == "ALT":
                    altIndex = i
                if tabbed[i] == "FORMAT":
                    formatIndex = i
            # Modify header to add START and STOP columns
            header.append('\t'.join([tabbed[0]] + ['START', 'STOP'] + tabbed[2:formatIndex])+'\t')
        else:
            tabbed = line.split('\t')
            # Extract FORMAT field
            if format == []:
                for item in tabbed[formatIndex].split(':'):
                    format.append(item)
            # Process VCF line based on different conditions
            if 'END=' in line:
                # Handle lines with 'END='
                output.append('\t'.join(tabbed[:2] + [line.split('END=')[1].split(';')[0]] + tabbed[2:formatIndex] + [tabbed[formatIndex+1].replace(':', '\t')]))
            elif refIndex != 0 and altIndex != 0:
                # Calculate STOP position
                stop = int(tabbed[1]) + max(0, int(len(tabbed[refIndex]))-int(len(tabbed[altIndex])))
                output.append('\t'.join(tabbed[:2] + [str(stop)] + tabbed[2:formatIndex] + [tabbed[formatIndex+1].replace(':', '\t')]))
    # Write processed data to a new BED file
    with open(inputpath.replace('.vcf', '_bedded.bed'), 'w') as opened:
        opened.write(''.join(header + ['\t'.join(format),'\n']+output))
    # Return header and processed VCF lines
    return header + output
