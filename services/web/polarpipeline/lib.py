from tqdm import tqdm
import subprocess
import re
import os
import math
import psycopg2
import statistics
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from bs4 import BeautifulSoup


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
#   id: file/row id. Generated in app.py
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
#   inputfile: a LOADED file (using the above function) 
#   returns a dictionary with keys equaling column header names and values equaling corresponding index numbers.
    headers = inputfile[0].strip().split('\t')
    columns = {}
    column_index = 0
    for item in headers:
        columns[item.strip()] = column_index
        column_index += 1
    return columns

# Depricated. was going to see if it helped with time since its in the cool kid's club for being tied for most efficient
# algorithm bc I didn't know what python's sorted() function used and I didn't think to look it up. (I just did and it uses
# Timsort. I have never heard of that before. It seems to be better than merge sort. oops.)
# def mergesort(list):
#     if len(list) > 2000000:
#         mergesort(list[:int(len(list)/2)])
#         mergesort(list[int(len(list)/2):])
#     print('sorting', len(list))
#     return sorted(list, key=custom_sort_key)

def custom_sort_key(item):
# Defines the key used to sort the files. in this case, by chromosome first, then if they are equal, by position.
# Function will not be called manually. meant to be used in python's built in sorted() function. look at docs.
#   item: line to be valued (idk if thats the right word)
#   return: the value (nailed it)
    tabbed = item.split("\t")
    chr_num = tabbed[0].split('chr')[-1]
    pos_str = tabbed[2]

    if chr_num == "X":
        chr_value = 23
    elif chr_num == "Y":
        chr_value = 24
    elif chr_num == "M":
        chr_value = 25
    else:
        try:
            chr_value = int(chr_num)
        except:
            print(tabbed)

    return (chr_value, int(pos_str))

def whoami():
    completed_process = subprocess.run(['whoami'], text=True, capture_output=True)
    return completed_process.stdout.strip()

def connect():
    db_config = {
        'dbname': 'polarDB',
        'user': 'polarPL',
        'password': 'polarpswd',
        'host': 'db',
        'port': '5432',
    }
    return psycopg2.connect(**db_config)

#   _____  _____  _____ _   _  _____ ______  _____ _____   ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  |  __ \|  __ \|_   _| \ | |/ ____|  ____|/ ____/ ____| |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#  | |__) | |__) | | | |  \| | |    | |__  | (___| (___   | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#  |  ___/|  _  /  | | | . ` | |    |  __|  \___ \\___ \  |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#  | |    | | \ \ _| |_| |\  | |____| |____ ____) |___) | | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_|    |_|  \_\_____|_| \_|\_____|______|_____/_____/  |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|
#   (WORKS, NOT BEING USED)
                                                                                                              
def princess(input_dir, run_name, clair_model, reference_file):
# Used to run the princess pipeline. Requires the princess environment be installed and named "princess_env" and that the princess folder is 
# present in /home/<user>/princess_work/. Unfortunately, the one from github does not work as is. There are compatibility
# issues and dependency numbers must be removed from the environment yamls in the envs folder. Kind of obnoxious, but it is what it is.
#   input_dir: directory containing the file to be processed. analysis folder will be generated alongside the file.
#   run_name: the name of the run. (usually name of the file minus extensions)
#   clair_model: the name of the clair model to be used.
#   reference_file: path to the reference fasta. 
#   returns: none. all purchases final.
    print('searching for file...')
    pc_name = whoami()
    for filename in os.listdir(input_dir):
        if os.path.isfile(os.path.join(input_dir, filename)):
            sample = os.path.join(input_dir, filename)
            analysis_dir = os.path.join(input_dir, 'analysis')
            print('starting princess...')
            command = f'mamba run -n princess_env /home/{pc_name}/princess_work/princess/princess all -r ont -d {analysis_dir} -f {reference_file} -s {sample} -sn {run_name} -j 15 -sp -e --latency-wait 10000 --chr chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY chrM --rerun-incomplete --clair-model {clair_model}'
            os.system(command)
            # process = subprocess.run(['mamba', 'run', '-n', 'princess_env', f'/home/{pc_name}/princess_work/princess/princess', 'all', '-r', 'ont', '-d', analysis_dir, '-f', f'/mnt/shared_storage/shared_resources/{reference_file}', '-s', sample, '-sn', run_name ,'-j', '15', '-sp', '-e', '--latency-wait 10000', '--chr', 'chr1', 'chr2', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7', 'chr8', 'chr9', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14', 'chr15', 'chr16', 'chr17', 'chr18', 'chr19', 'chr20', 'chr21', 'chr22', 'chrX', 'chrY', 'chrM', '--rerun-incomplete', '--clair-model', f'/mnt/shared_storage/shared_resources/{clair_model}'])
            # stdout, stderr = process.communicate()
            # while not os.path.isfile(f'/home{pc_name}/polarPipelineWork/{run_name}/analysis/result/{run_name}.minimap.phased.SNVs.vcf.gz'):
            #     print('princess incomplete or failed')
            #     time.sleep(10)
            #     if not os.path.isdir(f'/home{pc_name}/polarPipelineWork/{run_name}/analysis'):
            #         print('run is dead')
            #         quit()
            # command = f'pigz -d /home{pc_name}/polarPipelineWork/{run_name}/analysis/result/{run_name}.minimap.phased.SNVs.vcf.gz'
            # os.system()
            process = subprocess.Popen(['pigz', '-d', f'{run_name}.minimap.phased.SNVs.vcf.gz'], cwd=f'{analysis_dir}/result')
            stdout, stderr = process.communicate()


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
    root = input_path.split('.sam')[0]

    view_command = f'samtools view -@ {threads} -bo {root}.bam {root}.sam'
    os.system(view_command)
    # print(view_command)

    sort_command = f'samtools sort -m 2G -o {root}_sorted.bam -@ {threads} {root}.bam'
    os.system(sort_command)
    # print(sort_command)

    index_command = f'samtools index -b -@ {threads} -o {root}_sorted.bam.bai {root}_sorted.bam'
    os.system(index_command)
    # print(index_command)

    rm_command = f'rm {root}.sam {root}.bam'
    os.system(rm_command)
    # print(rm_command)

    rename_bam = f'mv {root}_sorted.bam {root}.bam'
    os.system(rename_bam)
    rename_bam_bai = f'mv {root}_sorted.bam.bai {root}.bam.bai'
    os.system(rename_bam_bai)

    return f"{root}.bam"

#   _   _ ________   _________ ______ _      ______          __  ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  | \ | |  ____\ \ / /__   __|  ____| |    / __ \ \        / / |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#  |  \| | |__   \ V /   | |  | |__  | |   | |  | \ \  /\  / /  | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#  | . ` |  __|   > <    | |  |  __| | |   | |  | |\ \/  \/ /   |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#  | |\  | |____ / . \   | |  | |    | |___| |__| | \  /\  /    | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_| \_|______/_/ \_\  |_|  |_|    |______\____/   \/  \/     |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|


def nextflow(input_file, output_directory, reference_file, clair3_model_path, threads='30', config='default', workspace_directory='default'):
# Function to run the epi2me nextflow workflow. Assumes nextflow is installed into path.
#   input_file: input file path
#   output_directory: what folder the output and workspace folders will be generated in
#   reference_file: full path to the reference file being used
#   clair3_model_path: full path to the clair3 model folder
    run_name = input_file.strip().split('/')[-1].split('.bam')[0].split('.fastq')[0]
    command = f"echo Epididymis0! | sudo -S nextflow run epi2me-labs/wf-human-variation \
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
        --threads {threads} \
        --ubam_map_threads {math.floor(int(threads)/3)} \
        --ubam_sort_threads {math.floor(int(threads)/3)} \
        --ubam_bam2fq_threads {math.floor(int(threads)/3)} \
        --merge_threads {threads} \
        --annotation_threads {threads} \
        --disable_ping"
    try:
        os.system(command)
        pc_name = whoami()
        working_directory = '/'.join(output_directory.strip().split('/')[:-1])
        command = f'echo Epididymis0! | sudo -S chown {pc_name} {working_directory}/* -R'
        os.system(command)
        return True
    except:
        return False

def y_nextflow(input_file, output_directory, reference_file, clair3_model_path, threads='30', config='default', workspace_directory='default'):
    run_name = input_file.strip().split('/')[-1].split('.bam')[0].split('.fastq')[0]
    command = f"echo [password] | sudo -S nextflow run epi2me-labs/wf-human-variation \
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
        pc_name = whoami()
        working_directory = '/'.join(output_directory.strip().split('/')[:-1])
        command = f'echo Epididymis0! | sudo -S chown {pc_name} {working_directory}/* -R'
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
    chrm, pos, id, ref, alt, qual, fltr, info, frmt, traits = evilstinkynogoodline.strip().split('\t')
    goodlines = []
    if ',' in alt and ',' in traits:
        for i in range(len(alt.strip().split(','))):
            traitlist = []
            for j in range(len(frmt.strip().split(':'))):
                if len(traits.strip().split(':')[j].split(',')) == len(alt.strip().split(',')):
                    traitlist.append(traits.strip().split(':')[j].split(',')[i])
                elif (len(traits.strip().split(':')[j].split(',')) == len(alt.strip().split(','))+1 and frmt.strip().split(':')[j] == "AD"):
                    traitlist.append(','.join([traits.strip().split(':')[j].split(',')[0], traits.strip().split(':')[j].split(',')[i+1]]))
                else:
                    traitlist.append(traits.strip().split(':')[j])
            goodlines.append('\t'.join([chrm, pos, id, ref, alt.strip().split(',')[i], qual, fltr, info, frmt, ':'.join(traitlist)])+'\n')
        return goodlines
    else:
        goodlines.append(evilstinkynogoodline)
        return goodlines

                                                                                                                    
#  __      ________ _____    ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  \ \    / /  ____|  __ \  |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#   \ \  / /| |__  | |__) | | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#    \ \/ / |  __| |  ___/  |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#     \  /  | |____| |      | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#      \/   |______|_|      |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|
                                                                                
                                                                                
def vep(input_snv, input_sv, reference_path, threads='30', output_snv='output', output_sv='output'):
# Runs vep. Params are in list form, so it is easy to add new ones. Same with plugins. The process for installing vep to a new computer
# is unecissarily difficult, but there is (hopefully) a prepackaged vep folder and guide in the setup tab of the webapp.
#   input_snv: path to the input snv file (vcf from either princess or nextflow)
#   input_sv: path to the input sv file (vcf from either princess or nextflow)
#   output_snv: path to the desired snv output file (include full path, filename and extension included)
#   output_sv: path to the desired sv output file (include full path, filename and extension included)
#   return: none. does more damage the more the user likes you.

    pc_name = whoami()
    run_name = input_sv.strip().split('/')[-1].split('.wf_')[0]
    # if input_snv.endswith('.gz'):
    #     subprocess.run(["pigz", "-d", run_name+".sepAlt.wf_snp.vcf.gz"], cwd='/'.join(input_snv.strip().split('/')[:-1]))
    #     input_snv = input_snv.split('.gz')[0]
    if input_sv.endswith('.gz'):
        subprocess.run(["pigz", "-d", run_name+".wf_sv.vcf.gz"], cwd='/'.join(input_snv.strip().split('/')[:-1]))
        input_sv = input_sv.split('.gz')[0]

    start = f'~/ensembl-vep/vep --offline --cache --tab --everything --assembly GRCh38 --fasta {reference_path} --fork {threads} --buffer_size 20000'
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
        f' --plugin dbNSFP,/home/{pc_name}/vep-resources/dbNSFP4.4a_grch38.gz,ALL',
        f' --plugin REVEL,/home/{pc_name}/vep-resources/new_tabbed_revel_grch38.tsv.gz',
        f' --plugin AlphaMissense,file=/home/{pc_name}/vep-resources/AlphaMissense_hg38.tsv.gz',
        f' --plugin EVE,file=/home/{pc_name}/vep-resources/eve_merged.vcf.gz',
        f' --plugin DisGeNET,file=/home/{pc_name}/vep-resources/all_variant_disease_pmid_associations_final.tsv.gz'
    ]
    
    input_dir = '/'.join(input_snv.strip().split('/')[:-1])
    
    commandInputSNV = f' -i {input_snv}'
    commandInputSV = f' -i {input_sv}'
    if output_snv == 'output':
        commandOutputSNV = ' -o ' + os.path.join(input_dir, run_name+"_vep_snv.tsv")
    else:
        commandOutputSNV = f' -o {output_snv}'
    if output_sv == 'output':
        commandOutputSV = ' -o ' + os.path.join(input_dir, run_name+"_vep_sv.tsv")
    else:
        commandOutputSV = f' -o {output_sv}'
    command = start + ''.join(params) + ''.join(plugins) + commandInputSNV + commandOutputSNV
    print('starting vep for snv...')
    os.system(command)
    command = start + ''.join(params) + ''.join(plugins) + commandInputSV + commandOutputSV
    print('starting vep for sv...')
    os.system(command)
    print('vep complete!')

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

# Old code to add gene symbols to variants that did not have them. Was told to do it, then not to. Not currently used. 
""" def addSymbols(inputfile, inputbed):
    outputfile = []
    columns = getColumns(inputfile)
    for line in inputfile:
        tabline = line.split('\t')
        chr = tabline[columns['#CHROM']]
        symbol = tabline[columns['SYMBOL']]
        if line.strip().startswith('#'):
            outputfile.append(line)
            continue

        start = tabline[columns['#START']]
        stop = tabline[columns['#STOP']]

        bedsymbol = lookup(inputbed, chr, start, stop)

        if bedsymbol == '-':
            bedsymbol = '-'

        if symbol == '-':
            tabline[columns['SYMBOL']] = bedsymbol

        newline = '\t'.join(tabline)
        outputfile.append(newline)
    return outputfile """

def addToolsColumn(bed_file):
# This function does two things, probably should have split it up but it avoids an extra loop through the file. It first determines if a tool considers a variant
# dangerous (deliterious? idk) and if it does it adds it to a total and to a list, then adds both of those to the file in separate columns. This allows for both a
# ballpark estimate as to how bad a variant is as well as knowing what tools were to blame for that accusation. (how rude of them!)
#   bed_file: LOADED (using the load_file function) input file. i don't know why i called it bed file, probably because it is in bed format at this point.
#   gene_source_file: LOADED (using the load_file function) gene source file. 
#   returns: whole file with added columns for number of tools claiming deliterious on a variant and the tools themselves(the jury perhaps?)
    output_file = []
    columns = getColumns(bed_file)
    for line in bed_file:
        tabbed_line = line.strip().split('\t')
        if line.strip().startswith('#'):
            output_file.append('\t'.join(tabbed_line[:columns['QUAL']] + ['SV_SNV', 'NUM_TOOLS', 'TOOLS'] + tabbed_line[columns['QUAL']:])+'\n')
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

        if 'Snif' not in id:
            snv_or_sv = 'SNV'
        else:
            num_tools = 6
            snv_or_sv = 'SV'
        built_line = '\t'.join(start + [snv_or_sv] + [str(num_tools)] + [''.join(tools)] + info)+'\n'
        output_file.append(built_line)

    return output_file

def addGeneSource(input, gene_source_file):
    output_file = []
    columns = getColumns(input)
    gene_source = buildGeneSourceDict(gene_source_file)
    for line in input:
        tabbed_line = line.strip().split('\t')
        if line.strip().startswith('#'):
            output_file.append('\t'.join(tabbed_line[:columns['QUAL']] + ['GENE_SOURCE'] + tabbed_line[columns['QUAL']:])+'\n')
            continue
        start = tabbed_line[:columns['QUAL']]
        gene = tabbed_line[columns['SYMBOL']]
        info = tabbed_line[columns['QUAL']:]
        if gene in gene_source:
            gene_source_info = gene_source[gene]
        else:
            gene_source_info = '-'
        built_line = '\t'.join(start + [gene_source_info] + info)+'\n'
        output_file.append(built_line)
    return output_file



#   _____  ______ __  __  ______      ________   _____  _    _ _____  ______ _____    _____   ______          _______ 
#  |  __ \|  ____|  \/  |/ __ \ \    / /  ____| |  __ \| |  | |  __ \|  ____|  __ \  |  __ \ / __ \ \        / / ____|
#  | |__) | |__  | \  / | |  | \ \  / /| |__    | |  | | |  | | |__) | |__  | |  | | | |__) | |  | \ \  /\  / / (___  
#  |  _  /|  __| | |\/| | |  | |\ \/ / |  __|   | |  | | |  | |  ___/|  __| | |  | | |  _  /| |  | |\ \/  \/ / \___ \ 
#  | | \ \| |____| |  | | |__| | \  /  | |____  | |__| | |__| | |    | |____| |__| | | | \ \| |__| | \  /\  /  ____) |
#  |_|  \_\______|_|  |_|\____/   \/   |______| |_____/ \____/|_|    |______|_____/  |_|  \_\\____/   \/  \/  |_____/ 
                                                                                                                    
                                                                                                                    
def collapseDuplicateRows(inputfile):
# This function was made to combat a specific issue we were having where there would be sometimes hundreds of duplicate rows in the output files,
# only difference between them being in like 4 columns in the middle. This function 'squashes' these rows by combining rows that only differ in these
# columns. The differences are kept by listing them all in their corresponding columns, so that if someone wanted to (hasnt happened yet) they could
# delimit these 4 columns and recover all of the original repeated rows.
#   inputfile: self explanatory
#   returns: whole file with dupe rows squashed
    combined_output = []
    combined_rows = {}
    columns = getColumns(inputfile)
    for line in inputfile:
        if line.strip().startswith('#'):
            combined_output.append(line)
            continue
        tabbed_line = line.strip().split('\t')
        key = ('.'.join(tabbed_line[:columns['Gene']] + tabbed_line[columns['cDNA_position']:]))
        if key in combined_rows:
            combined_rows[key][columns['Gene']] = ','.join([combined_rows[key][columns['Gene']], tabbed_line[columns['Gene']]])
            combined_rows[key][columns['Feature']] = ','.join([combined_rows[key][columns['Feature']], tabbed_line[columns['Feature']]])
            combined_rows[key][columns['Feature_type']] = ','.join([combined_rows[key][columns['Feature_type']], tabbed_line[columns['Feature_type']]])
            combined_rows[key][columns['Consequence']] = ','.join([combined_rows[key][columns['Consequence']], tabbed_line[columns['Consequence']]])
        else:
            combined_rows[key] = tabbed_line
    combined_output += ['\t'.join(combined_rows[key]) + '\n' for key in combined_rows]
    return combined_output


#   __  __ ______ _____   _____ ______    ______ _    _ _   _  _____ _______ _____ ____  _   _ 
#  |  \/  |  ____|  __ \ / ____|  ____|  |  ____| |  | | \ | |/ ____|__   __|_   _/ __ \| \ | |
#  | \  / | |__  | |__) | |  __| |__     | |__  | |  | |  \| | |       | |    | || |  | |  \| |
#  | |\/| |  __| |  _  /| | |_ |  __|    |  __| | |  | | . ` | |       | |    | || |  | | . ` |
#  | |  | | |____| | \ \| |__| | |____   | |    | |__| | |\  | |____   | |   _| || |__| | |\  |
#  |_|  |_|______|_|  \_\\_____|______|  |_|     \____/|_| \_|\_____|  |_|  |_____\____/|_| \_|
#  (most complicated function. made me throw up. jk.)

def parse_vep_id(line):
# Parses the given line to create a unique id for it. (basically, if one is provided, uses it, if not, joins together chr, pos, ref and alt to make one)
#   line: yardyno
#   returns: id, either string or tuple depending on if an id existed prior
    if '_' not in line[0]:
        return line[0]
    chr = line[0].split('_')[0]
    pos = line[0].split('_')[1]
    ref = str(line[0].split('_')[2].split('/')[0])
    alt = ','.join(line[0].split('_')[2].split('/')[1:])
    ref = ref.replace('-', '')
    alt = alt.replace('-', '')
    return (chr, pos, ref, alt)

def mergeFiles(snv_vep_input, sv_vep_input, snipeff_input, sniffles_input, output='output'):
# Takes in 4 files, the output for both snvs and svs from vep, as well as the output for both snvs and svs from either nextflow or princess. It combines
# the rows from vep, so that snvs and svs are in one file. however, vep for some reason (probably to cause me agony) drops critical information that was present in
# the nextflow/princess outputs, so that must be retrieved. I rewrote it to use the headers to identify what needs to be added, so even if the output changes in vep
# or nextflow/princess it should still work.
#   snv_vep_input: filepath
#   sv_vep_input: filepath
#   snipeff_input: filepath
#   sniffles_input: filepath
#   output: optional argument. if one is provided, it must be a filepath to a desired output file. if it is not, it just returns the whole file in an array. (elements being lines)
#           distinction exists because if the function is called outside of the pipeline, its nice to be able to output to a file without jumping through hoops
#   returns: conditional. like my love for competitive fps games


    # INITIALIZE VARIABLES

    print(f'loading {snv_vep_input}... ', end='', flush=True)
    snv_vep = load_file(snv_vep_input)
    print(f'done!\nloading {sv_vep_input}... ', end='', flush=True)
    sv_vep = load_file(sv_vep_input)
    print(f'done!\nloading {snipeff_input}... ', end='', flush=True)
    snipList = {}
    sniffList = {}
    snipColumns = {}
    sniffColumns = {}
    vepColumns = {}
    merged_header = ['#CHROM', 'START', 'STOP']
    merge = []

    # LOAD SNIPEFF FILE, GRAB RELEVANT COLUMN HEADERS

    formatindex = 0
    for variant in load_file(snipeff_input):
        line = variant.strip().split('\t')
        if variant.startswith('#'):
            if variant.startswith('#CHROM'):
                for i in range(len(line)):
                    if line[i] == 'FORMAT':
                        formatindex = i
                    elif snipeff_input.strip().split('/')[-1].split('.vcf')[0] != line[i]:
                        snipColumns[line[i]] = i
            continue
        if formatindex:
            for i in range(len(line[formatindex].split(':'))):
                snipColumns[line[formatindex].split(':')[i]] = (formatindex+1, i)
            formatindex = 0

        if line[snipColumns['ID']] == '.':
            chr = line[snipColumns['#CHROM']]
            pos = line[snipColumns['POS']]
            ref = line[snipColumns['REF']]
            alt = line[snipColumns['ALT']]
            alts = []
            poschange = 1
            refchange = 1
            altchange = 1
            for subalt in alt.split(','):
                if len(ref) == 1 and len(subalt) == 1 or subalt[0] != ref[0]:
                    poschange = 0
                    refchange = 0
                    altchange = 0
            for subalt in alt.split(','):
                alts.append(subalt[altchange:])
            snipList[chr, str(int(pos)+poschange), ref[refchange:], ','.join(alts)] = line
        else:
            for id in line[snipColumns['ID']].split(';'):
                snipList[id] = line

    print(f'done!\nloading {sniffles_input}... ', end='', flush=True)

    # LOAD SNIFFLES FILE, GRAB RELEVANT COLUMN HEADERS

    formatindex = 0
    infoindex = 0
    for variant in load_file(sniffles_input):
        line = variant.strip().split('\t')
        if variant.startswith('#'):
            if variant.startswith('#CHROM'):
                for i in range(len(line)):
                    if line[i] == 'FORMAT':
                        formatindex = i
                    elif line[i] == 'INFO':
                        infoindex = i
                    elif sniffles_input.strip().split('/')[-1].split('.vcf')[0] != line[i]:
                        sniffColumns[line[i]] = i
            continue
        if formatindex:
            for i in range(len(line[formatindex].split(':'))):
                if line[formatindex].split(':')[i] == 'PS':
                    sniffColumns['PHASE'] = (formatindex+1, i)
                else:
                    sniffColumns[line[formatindex].split(':')[i]] = (formatindex+1, i)
            formatindex = 0
        for i in range(len(line[infoindex].split(';'))):
            if line[infoindex].split(';')[i].split('=')[0] not in sniffColumns:
                if line[infoindex].split(';')[i].split('=')[0] == 'PRECISE' or line[infoindex].split(';')[i].split('=')[0] == 'IMPRECISE':
                    col = 'PRECISION'
                else: 
                    col = line[infoindex].split(';')[i].split('=')[0]
                sniffColumns[col] = infoindex
        if ';' in line[sniffColumns['ID']]:
            ids = line[sniffColumns['ID']].split('.')[-1]
            for sniffID in line[sniffColumns['ID']].split('.')[-1].split(';'):
                sniffList['.'.join(line[sniffColumns['ID']].split('.')[:-1])+'.'+sniffID] = line
        else:
            sniffList[line[sniffColumns['ID']]] = line

    # print(sniffColumns)

    print('done!\ncreating merged header... ', end='', flush=True)

    # COMPILE FINAL HEADER

    for column in snipColumns:
        if column not in merged_header:
            merged_header.append(column)

    for column in sniffColumns:
        if column == 'PHASE': continue
        if column == 'ANN': continue
        if column not in merged_header:
            merged_header.append(column)

    header_length = len(merged_header)-3

    second_af = False
    for row in snv_vep:
        if row.strip().startswith('#U'):
            for column in row.strip().split('\t'):
                if column == 'AF':
                    merged_header.append('AF_VEP')
                else:
                    merged_header.append(column)

    
    print('done!\n')

    # ENTER SNV VEP VARIANTS INTO MERGED FILE

    merge.append('\t'.join(merged_header)+'\n')

    total_len = len(snv_vep) + len(sv_vep)


    with tqdm(total=total_len, desc='merging', unit=' rows') as pbar:

        for variant in snv_vep:
            line = variant.strip().split('\t')
            if variant.startswith('#'):
                pbar.update(1)
                continue
            id = parse_vep_id(line)
            newline = []
            newline.append(line[1].split(':')[0])
            newline.append(line[1].split(':')[-1].split('-')[0])
            dash = 0
            if '-' in line[1].split(':')[-1]:
                dash = -1
            newline.append(line[1].split(':')[-1].split('-')[dash])
            for column in merged_header[3:header_length+3]:
                if column in snipColumns:
                    if type(snipColumns[column]) == tuple:
                        newline.append(snipList[id][snipColumns[column][0]].split(':')[snipColumns[column][1]])
                    else:
                        newline.append(snipList[id][snipColumns[column]])
                elif column == 'DR':
                    dp = int(snipList[id][snipColumns['DP'][0]].split(':')[snipColumns['DP'][1]])
                    finaldr = ''
                    for subaf in snipList[id][snipColumns['AF'][0]].split(':')[snipColumns['AF'][1]].split(','):
                        af = 1 - float(subaf)
                        finaldr += str(int(dp * af))+','
                    newline.append(finaldr[:-1])
                elif column == 'DV':
                    dp = int(snipList[id][snipColumns['DP'][0]].split(':')[snipColumns['DP'][1]])
                    finaldv = ''
                    for subaf in snipList[id][snipColumns['AF'][0]].split(':')[snipColumns['AF'][1]].split(','):
                        af = float(subaf)
                        finaldv += str(int(dp * af)) + ','
                    newline.append(finaldv[:-1])
                else:
                    newline.append('-')
            newline = newline + line
            merge.append('\t'.join(newline)+'\n')
            pbar.update(1)

        # ENTER SV VEP VARIANTS INTO MERGED FILE

        i = 0
        for variant in sv_vep:
            line = variant.strip().split('\t')
            if variant.startswith('#'):
                pbar.update(1)
                continue
            id = parse_vep_id(line)
            newline = []
            newline.append(line[1].split(':')[0])
            newline.append(line[1].split(':')[-1].split('-')[0])
            newline.append(line[1].split(':')[-1].split('-')[-1])

            infodict = {}
            for item in sniffList[id][infoindex].split(';'):
                title = item.split('=')[0]
                value = item.split('=')[-1]
                if title == "ANN": continue
                if item.split('=')[0] == "PRECISE" or item.split('=')[0] == "IMPRECISE":
                    title = "PRECISION"
                if item.split('=')[0] == "PHASE":
                    title = "PS"
                    value = value.split(',')[1]
                    if value == "NULL":
                        value = '.'
                infodict[title] = value

            for column in merged_header[3:header_length+3]:
                if column in sniffColumns:
                    if type(sniffColumns[column]) == tuple:
                        newline.append(sniffList[id][sniffColumns[column][0]].split(':')[sniffColumns[column][1]])
                    elif column in infodict:
                        newline.append(infodict[column])
                    elif column in ['POS', 'ID', 'REF', 'ALT', 'QUAL', 'FILTER', 'INFO']:
                        newline.append(sniffList[id][sniffColumns[column]])
                    else:
                        newline.append('-')
                elif column == 'DP':
                    dr = int(sniffList[id][sniffColumns['DR'][0]].split(':')[sniffColumns['DR'][1]])
                    dv = int(sniffList[id][sniffColumns['DV'][0]].split(':')[sniffColumns['DV'][1]])
                    dp = str(dr + dv)
                    newline.append(dp)
                else:
                    newline.append('-')
            newline = newline + line
            merge.append('\t'.join(newline)+'\n')
            pbar.update(1)

    print('done!')

    # OUTPUT BY EITHER RETURNING THE LIST OR OUTPUTTING TO FILE

    if output == 'output':
        return merge
    with open(output, 'w') as opened:
        opened.write(''.join(merge))

#   ______ _____ _   _ _____     _____          _   _ _____ _____ _____       _______ ______  _____ 
#  |  ____|_   _| \ | |  __ \   / ____|   /\   | \ | |  __ \_   _|  __ \   /\|__   __|  ____|/ ____|
#  | |__    | | |  \| | |  | | | |       /  \  |  \| | |  | || | | |  | | /  \  | |  | |__  | (___  
#  |  __|   | | | . ` | |  | | | |      / /\ \ | . ` | |  | || | | |  | |/ /\ \ | |  |  __|  \___ \ 
#  | |     _| |_| |\  | |__| | | |____ / ____ \| |\  | |__| || |_| |__| / ____ \| |  | |____ ____) |
#  |_|    |_____|_| \_|_____/   \_____/_/    \_\_| \_|_____/_____|_____/_/    \_\_|  |______|_____/ 
                                                                                                  
                                                                                                
def isCandidate(line, columns):
# Returns whether the given line is a candidate or not. lots of negated statements.
#   line: line to assess for candidacy
#   columns: dictionary of index values for given column names
    try:
        if ',' in line[columns['AF_VEP']]:
            return True
        if line[columns['AF_VEP']] != '-' and float(line[columns['AF_VEP']]) >= 0.05:
            return False
        if line[columns['GENE_SOURCE']] == '-':
            return False
        if line[columns['FILTER']] != 'PASS' and line[columns['FILTER']] != 'GT':
            return False
        if line[columns['SV_SNV']] == 'SV' and line[columns['PRECISION']] != 'PRECISE':
            return False
        if round(float(line[columns['DP']])) < 8:
            return False
        if round(float(line[columns['DV']])) < 3:
            return False
        if round(float(line[columns['NUM_TOOLS']])) < 2:
            return False
        return True
    except:
        print(line)
        return True

def findCandidates(inputfile):
# Function to add a column to the given input file that says whether the row contains a candidate or not
#   inputfile: guess
#   returns: file with brand new sparkly shiny candidate column
    output = []
    temp = []
    columns = getColumns(inputfile)

    for line in inputfile:
        tabbed_line = line.strip().split('\t')
        if line.strip().startswith('#'):
            output.append('\t'.join(tabbed_line[:columns['SV_SNV']] + ['CANDIDATE'] + tabbed_line[columns['SV_SNV']:])+'\n')
            continue
        else:
            candidate = isCandidate(tabbed_line, columns)
        temp.append('\t'.join(tabbed_line[:columns['SV_SNV']] + [str(candidate)] + tabbed_line[columns['SV_SNV']:])+'\n')

    columns = getColumns(output)
    allele_count = {}

    for item in temp:
        line = item.strip().split('\t')
        candidate = line[columns['CANDIDATE']]
        symbol = line[columns['SYMBOL']]
        gt = line[columns['GT']]
        phase = line[columns['PS']]
        chr = line[columns['#CHROM']]
        if chr == 'chrX' or chr == 'chrY':
            gt = '1/1'

        if candidate == 'True':
            if symbol in allele_count:
                if gt == '0|1' or gt == '1|0':
                    allele_count[symbol] = (allele_count[symbol][0] + 1, allele_count[symbol][1] + [(gt, phase)])
                else: 
                    allele_count[symbol] = (allele_count[symbol][0], allele_count[symbol][1] + [(gt, phase)])
            if symbol not in allele_count:
                if gt == '0|1' or gt == '1|0':
                    allele_count[symbol] = (1, [(gt, phase)])
                else: 
                    allele_count[symbol] = (0, [(gt, phase)])

    # print(allele_count)

    for item in temp:
        line = item.strip().split('\t')
        candidate = line[columns['CANDIDATE']]
        symbol = line[columns['SYMBOL']]
        gt = line[columns['GT']]
        phase = line[columns['PS']]
        chr = line[columns['#CHROM']]
        if chr == 'chrX' or chr == 'chrY':
            gt = '1/1'

        if candidate == 'True':
            if symbol in allele_count:
                if gt == '0|1' and (('1|0', phase) in allele_count[symbol][1] or any('1/1' in item for item in allele_count[symbol][1]) or any('0/0' in item for item in allele_count[symbol][1])):
                    candidate = True                
                elif gt == '1|0' and (('0|1', phase) in allele_count[symbol][1] or any('1/1' in item for item in allele_count[symbol][1]) or any('0/0' in item for item in allele_count[symbol][1])):
                    candidate = True
                elif gt == '1/1' or gt == '0/0':
                    candidate = True
                else:
                    candidate = False
        output.append('\t'.join(line[:columns['CANDIDATE']] + [str(candidate)] + line[columns['SV_SNV']:])+'\n')


    return output

#   _____ _   _ _______ ______ _____   _____ ______ _____ _______ _____ ____  _   _ 
#  |_   _| \ | |__   __|  ____|  __ \ / ____|  ____/ ____|__   __|_   _/ __ \| \ | |
#    | | |  \| |  | |  | |__  | |__) | (___ | |__ | |       | |    | || |  | |  \| |
#    | | | . ` |  | |  |  __| |  _  / \___ \|  __|| |       | |    | || |  | | . ` |
#   _| |_| |\  |  | |  | |____| | \ \ ____) | |___| |____   | |   _| || |__| | |\  |
#  |_____|_| \_|  |_|  |______|_|  \_\_____/|______\_____|  |_|  |_____\____/|_| \_|


def overlap(chr, start, stop, chrstartline, bed_ranges):
# Function to answer the burning question: "is this variant overlapping any of the regions in the bed file?"
#   chr: chromosome
#   start: start position
#   stop: stop position
#   chrstartline: a dictionary that contains the index value for the line that each chromosome starts at
#   bed_ranges: basically the bed file to intersect with, just loaded (using the load_file function)
    if chr not in chrstartline:
        return False
    for range in bed_ranges[chr]:
        bedgene = range[2]
        if not (start > range[1]) and not (stop < range[0]):
            return True
    return False

def intersect(file, bed, output='output'):
# Function to basically do what bedtools intersect does but slower. we were experiencing an odd bug where when intersecting, the bed file would expand to minimum
# the same size as the original file, which makes no sense because intersecting is only taking out files, so this was born. From minor testing it produces the same
# output as bedtools intersect but does it way slower. could maybe multithread this but its fine for now.
#   file: input file to be intersected
#   bed: bed file to intersect with
#   output: optional 
    # bed_ranges = {}
    # for line in bed:
    #     tabline = line.strip().split('\t')
    #     if tabline[0] in bed_ranges:
    #         bed_ranges[tabline[0]] = bed_ranges[tabline[0]] + [(int(tabline[1]), int(tabline[2]), tabline[3])]
    #     else:
    #         bed_ranges[tabline[0]] = [(int(tabline[1]), int(tabline[2]), tabline[3])]

    # chrstartline = {}
    # bedline = 0
    # while bedline < len(bed):
    #     tabline = bed[bedline].strip().split('\t')
    #     if tabline[0] not in chrstartline:
    #         chrstartline[tabline[0]] = (bedline, 0)
    #     else:
    #         chrstartline[tabline[0]] = (chrstartline[tabline[0]][0], bedline+1)
    #     bedline += 1


    # header = []
    # output = []
    # body = []

    # for line in file:
    #     if line.startswith('#'):
    #         header.append(line)
    #     else:
    #         body.append(line)

    # print("intersecting...")
    # for line in body:
    #     file_line = line.strip().split('\t')
    #     file_chr, file_start, file_stop = file_line[0], int(file_line[1]), int(file_line[2])

    #     if overlap(file_chr, file_start, file_stop, chrstartline, bed_ranges):
    #         output.append(line)


    # print("sorting...")
    # sorted_output = sorted(output, key=custom_sort_key)

    # final_output = header + sorted_output

    # return final_output

    intersection = []
    completed_process = subprocess.run(['bedtools', 'intersect', '-header', '-u', '-a', file, '-b', bed], text=True, capture_output=True)
    for line in completed_process.stdout.strip().split('\n'):
        intersection.append(line)
    if output != 'output':
        with open(output, 'w') as opened:
            opened.write('\n'.join(intersection))
        
    return intersection


def qcReport(file_path):
    qcData = {}
    with open(file_path) as fp:
        qcreport = BeautifulSoup(fp, 'html.parser')

    table = qcreport.find("table")
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        metric = columns[0].text
        value = columns[1].text
        
        # print(f"{metric}: {value}")
        qcData[metric] = value

    pattern = re.compile(r"EZChart_.+")
    charts = qcreport.find_all(id=pattern)
    for chart in charts:
        chartText = str(chart)
        # print(chartText[:3000])
        if "Read quality" in chartText:
            info = chartText.split("'subtext': '")[1].split("'")[0]
            # print('Read quality:', info)
            for item in info.split('. '):
                qcData['Read quality ' + item.lower().split(': ')[0]] = item.lower().split(': ')[1]
        elif "Read length" in chartText and 'yield' not in chartText:
            info = chartText.split("'subtext': '")[1].split("'")[0]
            # print('Read length:', info)
            for item in info.split('. '):
                qcData['Read length ' + item.lower().split(': ')[0]] = item.lower().split(': ')[1]
        elif "Mapping accuracy" in chartText:
            info = chartText.split("'subtext': '")[1].split("'")[0]
            # print('Mapping accuracy:', info)
            qcData['Mapping accuracy'] = info
        elif "Read coverage" in chartText:
            info = chartText.split("'subtext': '")[1].split("'")[0]
            # print('Read coverage', info)
            qcData['Read coverage'] = info

    pattern = re.compile(r"ParamsTable_.+")
    table = qcreport.find(id=pattern)
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if columns != [] and columns[0].text == 'threads':
            # print('Threads:', columns[1].text)
            qcData['Threads'] = columns[1].text
    
    return qcData

def cnvReport(file_path):
    cnvData = {}

    with open(file_path) as fp:
        cnvreport = BeautifulSoup(fp, 'html.parser')

    pattern = re.compile(r"Grid_.+")
    parent_div = cnvreport.find(id=pattern)

    for child_div in parent_div.find_all('div', class_='container'):
        header = child_div.find('h3', class_='h5').text.strip()
        value = child_div.find('p', class_='fs-2').text.strip()

        if value.endswith('bp'):
            header = header + ' (bp)'
            value = value.replace('bp', '')

        cnvData[header] = value

    table = cnvreport.find("table")
    for i in range(len(table.find_all("td"))):
        metric = table.find_all("th")[i].text
        value = table.find_all("td")[i].text.strip().replace('\n', ',')
        cnvData[metric] = value

    table = cnvreport.find(id="versions")
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if columns != []:
            metric = columns[0].text
            value = columns[1].text
            cnvData[metric] = value

    return cnvData

def snpReport(file_path):
    snpData = {}
    with open(file_path) as fp:
        snpreport = BeautifulSoup(fp, 'html.parser')

    pattern = re.compile(r"Grid_.+")
    parent_div = snpreport.find(id=pattern)

    for child_div in parent_div.find_all('div', class_='container'):
        header = child_div.find('h3', class_='h5').text.strip()
        value = child_div.find('p', class_='fs-2').text.strip()

        snpData[header] = value

    table = snpreport.find(id="versions")
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if columns != []:
            metric = columns[0].text
            value = columns[1].text
            snpData[metric] = value

    return snpData

def svReport(file_path):
    svData = {}
    with open(file_path) as fp:
        svreport = BeautifulSoup(fp, 'html.parser')

    pattern = re.compile(r"Grid_.+")
    parent_div = svreport.find(id=pattern)

    for child_div in parent_div.find_all('div', class_='container'):
        header = child_div.find('h3', class_='h5').text.strip()
        value = child_div.find('p', class_='fs-2').text.strip()

        svData[header] = value

    pattern = re.compile(r"DataTable_.+")
    table = svreport.find(id=pattern)
    
    sv_types = []
    for item in table.find_all("tr"):
        if sv_types == []:
            for header in item.find_all("th"):
                sv_types.append(header.text)
            sv_types = sv_types[1:]

    for i in range(len(sv_types)):
        for j in range(1, len(table.find_all("tr"))):
            # print(sv_types[i] + '_' + table.find_all("tr")[j].find("th").text.replace('. ', '_'), table.find_all("tr")[j].find_all("td")[i].text)
            svData[sv_types[i] + '_' + table.find_all("tr")[j].find("th").text.replace('. ', '_')] = table.find_all("tr")[j].find_all("td")[i].text

    table = svreport.find(id="versions")
    for row in table.find_all("tr"):
        columns = row.find_all("td")
        if columns != []:
            metric = columns[0].text
            value = columns[1].text
            svData[metric] = value

    return svData
    
def reportReport(file_path):
    reportData = {}
    with open(file_path) as fp:
        reportreport = BeautifulSoup(fp, 'html.parser')
    
    command = reportreport.find("pre", class_="nfcommand")
    reportData['Nextflow command'] = command.text

    clairModel = command.text.split('--clair3_model_path ')[1].split(' ')[0].split('/')[-1]
    reportData['clair3 model'] = clairModel

    pc_name = command.text.split('/home/')[1].split('/')[0]
    reportData['PC name'] = pc_name

    cpuHours = reportreport.find("dd", class_="col-sm-9").text
    reportData['CPU hours'] = cpuHours

    return reportData

def coverageReport(file_path):
    coverageArray = []
    for line in open(file_path):
        coverageArray.append(float(line.strip().split('\t')[3]))
    median = statistics.median(coverageArray)
    mean = statistics.mean(coverageArray)
    coverageData = {'Median coverage': str(median), 'Mean coverage': str(mean)}
    return coverageData

def createRunSummary(output, alignment, cnv, snp, sv, report, coverage):
    with open(os.path.join(output, 'run_summary.txt'), 'w') as opened:
        if snp != 'none':
            qcData = qcReport(alignment)
            cnvData = cnvReport(cnv)
            snpData = snpReport(snp)
            svData = svReport(sv)
            reportData = reportReport(report)
            coverageData = coverageReport(coverage)
            opened.write('Name'+'\t'+output.split('/')[-2]+'\n')
            for item in qcData:
                opened.write(item+'\t'+qcData[item]+'\n')
            for item in cnvData:
                opened.write(item+'\t'+cnvData[item]+'\n')
            for item in snpData:
                opened.write(item+'\t'+snpData[item]+'\n')
            for item in svData:
                opened.write(item+'\t'+svData[item]+'\n')
            for item in reportData:
                opened.write(item+'\t'+reportData[item]+'\n')
            for item in coverageData:
                opened.write(item+'\t'+coverageData[item]+'\n')
        else:
            qcData = qcReport(alignment)
            svData = svReport(sv)
            reportData = reportReport(report)
            coverageData = coverageReport(coverage)
            opened.write('Name'+'\t'+output.split('/')[-2]+'\n')
            for item in qcData:
                opened.write(item+'\t'+qcData[item]+'\n')
            for item in svData:
                opened.write(item+'\t'+svData[item]+'\n')
            for item in reportData:
                opened.write(item+'\t'+reportData[item]+'\n')
            for item in coverageData:
                opened.write(item+'\t'+coverageData[item]+'\n')

def vcftobed(inputpath):

    header = []
    output = []
    format = []
    refIndex = 0
    altIndex = 0
    formatIndex = 0
    for line in open(inputpath, 'r'):
        if line.startswith('##'):
            header.append(line)
        elif line.startswith('#'):
            tabbed = line.split('\t')
            for i in range(len(tabbed)):
                if tabbed[i] == "REF":
                    refIndex = i
                if tabbed[i] == "ALT":
                    altIndex = i
                if tabbed[i] == "FORMAT":
                    formatIndex = i
            header.append('\t'.join([tabbed[0]] + ['START', 'STOP'] + tabbed[2:formatIndex])+'\t')
        else:
            tabbed = line.split('\t')
            if format == []:
                for item in tabbed[formatIndex].split(':'):
                    format.append(item)
            if 'END=' in line:
                output.append('\t'.join(tabbed[:2] + [line.split('END=')[1].split(';')[0]] + tabbed[2:formatIndex] + [tabbed[formatIndex+1].replace(':', '\t')]))
            elif refIndex != 0 and altIndex != 0:
                stop = int(tabbed[1]) + max(0, int(len(tabbed[refIndex]))-int(len(tabbed[altIndex])))
                output.append('\t'.join(tabbed[:2] + [str(stop)] + tabbed[2:formatIndex] + [tabbed[formatIndex+1].replace(':', '\t')]))
    with open(inputpath.replace('.vcf', '_bedded.bed'), 'w') as opened:
        opened.write(''.join(header + ['\t'.join(format),'\n']+output))
    return header + output
