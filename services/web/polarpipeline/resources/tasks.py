# import sys
# sys.path.append('/usr/src/app/polarpipeline')
from celery import Celery
from lib import *
import time
import sys
import os
import shutil
import configparser
import subprocess
from datetime import datetime

# define config filepath
CONFIG_FILE_PATH = '/mnt/pipeline_resources/config.ini'

# Read the IP of the server from config file
setup_parser = configparser.ConfigParser()
setup_parser.read(CONFIG_FILE_PATH)
ip = setup_parser['Network']['host_ip']

# define the celery app
app = Celery('tasks', broker=f'pyamqp://guest:guest@{ip}:5672/')


# function for the regular (hg38) operations
@app.task
def process(input_file_path, output_path, clair_model_name, gene_source_name, bed_file_name, reference_file_name, id):
    # build paths for all necessary files
    clair_model_path = os.path.join('/mnt/pipeline_resources/clair_models', clair_model_name)
    gene_source_path = []
    for name in gene_source_name:
        gene_source_path.append(os.path.join('/mnt/pipeline_resources/gene_source',name))
    # gene_source_path = os.path.join('/mnt/pipeline_resources/gene_source', gene_source_name)
    reference_path = os.path.join('/mnt/pipeline_resources/reference_files', reference_file_name)
    bed_file_path = []
    for name in bed_file_name:
        bed_file_path.append(os.path.join('/mnt/pipeline_resources/bed_files',name))

    # get the name of the current computer (for database logging and such)
    pc_name = whoami()
    
    # check for presence of output path
    if not os.path.isdir(output_path):
        update_db(id, 'status', 'output path not found')
        return
    else: print('output path:', output_path)

    # check for thread count
    if setup_parser.has_section(pc_name):
        threads = setup_parser[pc_name]['threads']
    else:
        threads = setup_parser['Default']['threads']

    print(f'threads detected: {threads}')

    # check if file is local, if so, copy from local directory
    if '/' + pc_name + '/' in input_file_path:
        print('file is local!')
        input_file_path = input_file_path.replace('/mnt', '/home')

    # define the run name and the input directory
    run_name = os.path.basename(input_file_path).replace('.bam', '').replace('.fastq', '')
    input_directory = os.path.dirname(input_file_path)

    # try 3 times to identify the input file (not like anything would change between those seconds so idk)
    i = 0
    while i < 4:
        if os.path.isfile(input_file_path):
            print('found file ' + run_name+'!')
            if os.path.isdir(input_directory):
                print('directory identified!')
                break
        print("input could not be found: " + input_file_path + ". retrying.")
        time.sleep(10)
        i+=1
        if i >= 3:
            print('could not be found. quitting.')
            update_db(id, 'status', 'file not found')
            return

    # define the working path in polarPipelineNFWork using the run ID
    working_path = os.path.join('/home', pc_name, 'polarPipelineWork', id)

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # make the working directory
    os.makedirs(working_path, exist_ok=True)

    # copy the input file to the working directory
    update_db(id, 'status', 'transferring in')
    update_db(id, 'computer', pc_name)
    shutil.copy(input_file_path, working_path)
    
    currentTime = datetime.now()
    formattedTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(output_path,f'{formattedTime}_{run_name}')
    
    update_db(id, 'start_time', currentTime)
    
    # CHANGE FILENAMES TO INCLUDE TIME
    run_name = formattedTime + '_' + run_name

    # rename the input file (inside the working directory) to the timestamped name
    shutil.move(os.path.join(working_path, os.path.basename(input_file_path)), os.path.join(working_path, f'{run_name}.{os.path.basename(input_file_path).split(".")[-1]}'))
    # subprocess.run(["mv", os.path.join(working_path, input_file_path.split('/')[-1]), os.path.join(working_path, run_name+'.'+input_file_path.split('/')[-1].split('.')[-1])])
    input_file_path = os.path.join(working_path, f'{run_name}.{os.path.basename(input_file_path).split(".")[-1]}')

    # skips the minimap step if already a bam file
    if not input_file_path.endswith('.bam'):

        # unzips the input file if it is zipped
        if input_file_path.endswith('.fastq.gz'):
            subprocess.run(['pigz', '-d', input_file_path], cwd=working_path)
            input_file_path = input_file_path.replace('.fastq.gz', '.fastq')

        update_db(id, 'status', 'minimap')

        print('input: ' + working_path)
        print('output file destination: ' + output_dir)

        # runs minimap on fastq file
        try:
            input_file_path = minimap2(input_file_path, reference_path, threads)
        except:
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            return
        
        # if the minimap output is not found, report error and exit
        if not os.path.isfile(os.path.join(working_path, f"{run_name}.sam")):
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            return
        
        if checksignal(id) == 'stop':
            abort(working_path, id)
            return
        
    # runs samtools view, sort, and index on sam file
    update_db(id, 'status', 'view sort index')
    try:
        print('Running View Sort Index!')
        input_file_path = viewSortIndex(input_file_path, threads)
    except:
        update_db(id, 'status', 'failed: samtools')
        update_db(id, 'end_time', datetime.now())
        return
    
    # if output bam file is not found, report error and exit
    if not os.path.isfile(os.path.join(working_path, f"{run_name}.bam")):
        update_db(id, 'status', 'failed: samtools')
        update_db(id, 'end_time', datetime.now())
        return
        
        
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return
    

    # start the wf-human-variation pipeline using the bam file, we did these steps separately because the pipeline did not work with fastqs.
    # this makes sense as the pipeline is specifically made to work from bams and actually says this is the optimal starting point.
    update_db(id, 'status', 'nextflow')
    try:
        print('Running wf-human-variation!')
        nextflow(input_file_path, working_path, reference_path, clair_model_path, threads)
    except:
        update_db(id, 'status', 'failed: wf-human-variation')
        update_db(id, 'end_time', datetime.now())
        return
    
    outputsnv = os.path.join(working_path, "output", run_name+".wf_snp.vcf")
    outputsv = os.path.join(working_path, 'output', run_name+".wf_sv.vcf")
    
    # if wf-human-variation vcf output is not found, report error and exit
    if not (os.path.isfile(outputsnv+'.gz') and os.path.isfile(outputsv+'.gz')):
        print('wf-human-variation output not found. Exiting.')
        update_db(id, 'status', 'failed: wf-human-variation')
        update_db(id, 'end_time', datetime.now())
        return
    
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return    

    # unzip the wf-human-variation outputs
    subprocess.run(["pigz", "-d", run_name+".wf_snp.vcf.gz"], cwd=os.path.join(working_path, 'output'))
    subprocess.run(["pigz", "-d", run_name+".wf_sv.vcf.gz"], cwd=os.path.join(working_path, 'output'))
    
    # create sepAlt file to separate the alternate alleles from each other splitting them into two different rows
    sepalt = outputsnv.replace('.wf_snp.vcf', '.wf_snp.sepAlt.vcf')
    with open(sepalt, 'w') as opened:
        for variant in open(outputsnv):
            if variant.startswith('#'):
                opened.write(variant)
                continue
            for goodline in parseAlts(variant):
                opened.write(goodline)
    
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return
    
    # run vep on the wf-human-variation vcf
    update_db(id, 'status', 'vep')
    vep_snv = vep(sepalt, reference_path, threads)
    vep_sv = vep(outputsv, reference_path, threads)
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return
    
    # if the vep output is not found, report error and exit
    if not (os.path.isfile(vep_snv) and os.path.isfile(vep_sv)):
        print('Vep output not found. Exiting.')
        update_db(id, 'status', 'failed: vep')
        update_db(id, 'end_time', datetime.now())
        return
    
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # check one more time for files to merge
    missing = []
    for file in [sepalt, outputsv, vep_snv, vep_sv]:
        if not os.path.isfile(file):
            missing.append(file)
    if missing:
        missing_str = "\n".join([f"- {x}" for x in missing])
        print(f'Could not find all files for merge! Missing: \n{missing_str}')
        update_db(id, 'status', 'failed: vep')
        update_db(id, 'end_time', datetime.now())
        return
    else:
        print("found all files for run " + run_name + "!")

    # generate merged file, basically just adding columns from the wf-human-variation vcf that were lost in the vep output
    # outputs to a temporary file
    update_db(id, 'status', 'merging')
    try:
        mergeoutput = os.path.join(working_path, 'rawmerge.tsv')
        mergeFiles(sepalt, outputsv, vep_snv, vep_sv, mergeoutput)
    except Exception as e:
        print('Merge failed:', e, 'Exiting.')
        update_db(id, 'status', 'failed: merge')
        update_db(id, 'end_time', datetime.now())
        return

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # add tools column to merged file
    # outputs to a temporary file
    update_db(id, 'status', 'tabulating tools')
    print('adding tools...')
    try:
        toolsoutput = os.path.join(working_path, 'tools.tsv')
        addToolsColumn(mergeoutput, toolsoutput)
        os.remove(mergeoutput)
    except Exception as e:
        print('Tools failed:', e, 'Exiting.')
        update_db(id, 'status', 'failed: adding tools')
        update_db(id, 'end_time', datetime.now())
        return

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # collapse the duplicate rows to shrink the file size a bit and assist in simplifying analysis
    # outputs to a temporary file
    update_db(id, 'status', 'collapsing duplicate rows')
    print('collapsing duplicate rows...')
    try:
        collapseoutput = os.path.join(working_path, 'collapseoutput.tsv')
        collapseDuplicateRows(toolsoutput, collapseoutput)
        os.remove(toolsoutput)
    except:
        update_db(id, 'status', 'failed: collapsing duplicate rows')
        update_db(id, 'end_time', datetime.now())
        return

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # defines the wf-human-variation output path
    resultdir = os.path.join(working_path, 'output')

    print('moving to output!')
    # create all output directories
    '''
            FIRST OUTPUT GENERATED
    '''
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    nextflowdir = os.path.join(output_dir, '0_nextflow')
    if not os.path.exists(nextflowdir):
        os.mkdir(nextflowdir)
    bamdir = os.path.join(output_dir, '1_bam')
    if not os.path.exists(bamdir):
        os.mkdir(bamdir)
    variantdir = os.path.join(output_dir, '2_variant_files')
    if not os.path.exists(variantdir):
        os.mkdir(variantdir)
    intersectdir = os.path.join(output_dir, '3_intersect')
    if not os.path.exists(intersectdir):
        os.mkdir(intersectdir)
    finaldir = os.path.join(output_dir, '4_gene_source')
    if not os.path.exists(finaldir):
        os.mkdir(finaldir) 

    print('Writing merged files...')
    # gets columns for final merged file so that the tools column is known and the no zeros file can be produced
    mergeCols = getColumns(collapseoutput)
    # simultaneously writes the merged and nozero merged files
    with open(os.path.join(variantdir, run_name+'_merged.bed'), 'w') as finalmerged:
        with open(os.path.join(variantdir, run_name+'_merged_N0.bed'), 'w') as nozeros:
            for line in open(collapseoutput):
                variant = line.strip().split('\t')
                if variant[mergeCols['NUM_TOOLS']] != '0':
                    nozeros.write(line)
                finalmerged.write(line)
    
    print('Checking intersections...')
    # iterate through bed files, intersecting when necessary
    for i in range(len(bed_file_path)):

        update_db(id, 'status', 'intersecting')

        output = intersect(collapseoutput, bed_file_path[i])
        # if gene file is selected for the bed file, adds and populates the gene source column
        if gene_source_name[i] != "No gene source":
            gene_source_file = load_file(gene_source_path[i])
            output = addGeneSource(output, gene_source_file)
            finalfile = os.path.join(finaldir, run_name + '_' + bed_file_name[i].replace('.bed', f'_{gene_source_name[i].split(".txt")[0]}.vcf'))
            # writes to final output file
            with open(finalfile, 'w') as openFile:
                openFile.write(''.join(output))
        else:
            # if no gene source selected, writes intersected file without gene source
            finalfile = os.path.join(intersectdir, run_name + '_' + bed_file_name[i].replace('.bed', '.vcf'))
            with open(finalfile, 'w') as openFile:
                openFile.write('\n'.join(output))

        print('done!')

    print('Transferring files!')
    update_db(id, 'status', 'transferring completed files')
    currentTime = datetime.now()
    update_db(id, 'end_time', currentTime)

    # moves all relevant output files to the variant files output directory
    variantfiles = [sepalt, outputsv, vep_snv, vep_sv]
    for vf in variantfiles:
        shutil.move(os.path.join(resultdir, vf), variantdir)

    # moves all bam and bam.bai files to the bam output directory
    bamfiles = [run_name+".bam", run_name+".bam.bai"]
    for bm in bamfiles:
        shutil.move(os.path.join(working_path, bm), bamdir)

    # removes all reference files as to not waste space
    referencefiles = [reference_file_name, reference_file_name+'.fai', reference_file_name+".fa"]
    for rf in referencefiles:
        if os.path.isfile(os.path.join(resultdir, rf)):
            os.remove(os.path.join(resultdir, rf))

    # remove the wf-human-variation workspace directory
    if os.path.isdir(os.path.join(working_path, 'workspace')):
        shutil.rmtree(os.path.join(working_path, 'workspace'))

    # remove the wf-human-variation reference cache
    if os.path.isdir(os.path.join(working_path, 'output', 'ref_cache')):
        shutil.rmtree(os.path.join(working_path, 'output', 'ref_cache'))

    # move the wf-human-variation output directory to the nextflow output directory
    shutil.move(os.path.join(working_path, 'output'), nextflowdir)

    # unzip the regions file for summary creation
    subprocess.run(['pigz', '-d', run_name+'.regions.bed.gz'], cwd=os.path.join(nextflowdir, 'output'))

    # create summary file using wf-human-variation report htmls
    createRunSummary(
        nextflowdir, 
        os.path.join(nextflowdir, 'output', 'wf-human-variation-alignment-report.html'), 
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-cnv-report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-snp-report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-sv-report.html'),
        os.path.join(nextflowdir, 'output', 'execution', 'report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.regions.bed'))

    # remove the workspace directory on the worker
    shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(working_path)), id))


    update_db(id, 'status', 'complete')






@app.task
def processT2T(input_file_path, output_path, clair_model_name, bed_file_name, reference_file_name, id):
    # build paths for all necessary files
    clair_model_path = os.path.join('/mnt/pipeline_resources/clair_models', clair_model_name)
    reference_path = os.path.join('/mnt/pipeline_resources/reference_files', reference_file_name)
    bed_file_path = []
    for name in bed_file_name:
        bed_file_path.append(os.path.join('/mnt/pipeline_resources/bed_files',name))

    # get the name of the current computer (for database logging and such)
    pc_name = whoami()

    # check for presence of output path
    if not os.path.isdir(output_path):
        update_db(id, 'status', 'output path not found')
        return
    else: print('output path:', output_path)

    # check for thread count
    if setup_parser.has_section(pc_name):
        threads = setup_parser[pc_name]['threads']
    else:
        threads = setup_parser['Default']['threads']

    print(f'threads detected: {threads}')


    if '/' + pc_name + '/' in input_file_path:
        input_file_path = input_file_path.replace('/mnt', '/home')

    # define the run name and the input directory
    run_name = os.path.basename(input_file_path).replace('.bam', '').replace('.fastq', '')
    input_directory = os.path.dirname(input_file_path)

    # try 3 times to identify the input file (not like anything would change between those seconds so idk)
    i = 0
    while i < 4:
        if os.path.isfile(input_file_path):
            print('found file ' + run_name+'!')
            if os.path.isdir(input_directory):
                print('directory identified!')
                break
        print("input could not be found: " + input_file_path + ". retrying.")
        time.sleep(10)
        i+=1
        if i >= 3:
            print('could not be found. quitting.')
            update_db(id, 'status', 'file not found')
            return
    
    # define the working path in polarPipelineNFWork using the run ID
    working_path = os.path.join('/home', pc_name, 'polarPipelineWork', id)

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # make the working directory
    os.makedirs(working_path, exist_ok=True)

    # copy the input file to the working directory
    update_db(id, 'status', 'transferring in')
    update_db(id, 'computer', pc_name)
    shutil.copy(input_file_path, working_path)
    
    currentTime = datetime.now()
    formattedTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(output_path,f'{formattedTime}_{run_name}')
    
    update_db(id, 'start_time', currentTime)
    
    # CHANGE FILENAMES TO INCLUDE TIME
    run_name = formattedTime + '_' + run_name + '_T2T'

    output_dir = os.path.join(output_path,f'{run_name}')

    # rename the input file (inside the working directory) to the timestamped name
    shutil.move(os.path.join(working_path, os.path.basename(input_file_path)), os.path.join(working_path, f'{run_name}.{os.path.basename(input_file_path).split(".")[-1]}'))
    # subprocess.run(["mv", os.path.join(working_path, input_file_path.split('/')[-1]), os.path.join(working_path, run_name+'.'+input_file_path.split('/')[-1].split('.')[-1])])
    input_file_path = os.path.join(working_path, f'{run_name}.{os.path.basename(input_file_path).split(".")[-1]}')

    # skips the minimap step if already a bam file
    if not input_file_path.endswith('.bam'):

        # unzips the input file if it is zipped
        if input_file_path.endswith('.fastq.gz'):
            subprocess.run(['pigz', '-d', input_file_path], cwd=working_path)
            input_file_path = input_file_path.replace('.fastq.gz', '.fastq')

        update_db(id, 'status', 'minimap')

        print('input: ' + working_path)
        print('output file destination: ' + output_dir)

        # runs minimap on fastq file
        try:
            input_file_path = minimap2(input_file_path, reference_path, threads)
        except:
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            return
        
        # if the minimap output is not found, report error and exit
        if not os.path.isfile(os.path.join(working_path, f"{run_name}.sam")):
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            return
        
        if checksignal(id) == 'stop':
            abort(working_path, id)
            return
        
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return
    
    # runs samtools view, sort, and index on sam file
    update_db(id, 'status', 'view sort index')
    try:
        print('Running View Sort Index!')
        input_file_path = viewSortIndex(input_file_path, threads)
    except:
        update_db(id, 'status', 'failed: samtools')
        update_db(id, 'end_time', datetime.now())
        return
    
    # if output bam file is not found, report error and exit
    if not os.path.isfile(os.path.join(working_path, f"{run_name}.bam")):
        update_db(id, 'status', 'failed: samtools')
        update_db(id, 'end_time', datetime.now())
        return
        
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    update_db(id, 'status', 'nextflow')
    try:
        y_nextflow(input_file_path, working_path, reference_path, clair_model_path, threads)
    except:
        update_db(id, 'status', 'failed: nextflow')
        update_db(id, 'end_time', datetime.now())
        return

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    outputsv = os.path.join(working_path, 'output', run_name+".wf_sv.vcf")
    
    # if wf-human-variation vcf output is not found, report error and exit
    if not os.path.isfile(outputsv+'.gz'):
        print('wf-human-variation output not found. Exiting.')
        update_db(id, 'status', 'failed: wf-human-variation')
        update_db(id, 'end_time', datetime.now())
        return
    
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return    

    # unzip the wf-human-variation outputs
    subprocess.run(["pigz", "-d", run_name+".wf_sv.vcf.gz"], cwd=os.path.join(working_path, 'output'))

    # make output directories
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    nextflowdir = os.path.join(output_dir, '0_nextflow')
    if not os.path.exists(nextflowdir):
        os.mkdir(nextflowdir)
    bamdir = os.path.join(output_dir, '1_bam')
    if not os.path.exists(bamdir):
        os.mkdir(bamdir)
    intersectdir = os.path.join(output_dir, '2_intersect')
    if not os.path.exists(intersectdir):
        os.mkdir(intersectdir)

    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # attempt to create a bed version of the wf-human-variation output for intersection
    try:
        vcftobed(os.path.join(working_path, 'output', run_name+'.wf_sv.vcf'))
    except:
        update_db(id, 'status', 'failed: vcftobed')
        update_db(id, 'end_time', datetime.now())
        return
    
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # define the result directory
    resultdir = os.path.join(working_path, 'output')
    
    # intersect the original file for each selected bed file
    for i in range(len(bed_file_path)):
        update_db(id, 'status', 'intersecting')
        try:
            intersect(os.path.join(working_path, 'output', run_name+'.wf_sv_bedded.bed'), bed_file_path[i], os.path.join(intersectdir, run_name+'_'+bed_file_name[i].replace('.bed', '.vcf')))
        except:
            update_db(id, 'status', 'failed: intersection')
            update_db(id, 'end_time', datetime.now())
            return
        print('done!')
    
    if checksignal(id) == 'stop':
        abort(working_path, id)
        return

    # transfer completed files
    update_db(id, 'status', 'transferring completed files')
    currentTime = datetime.now()
    update_db(id, 'end_time', currentTime)

    # iterate through bam files, moving them to output
    for b in [run_name+".bam", run_name+".bam.bai"]:
        shutil.move(os.path.join(working_path, b), bamdir)
    # subprocess.run(["mv", run_name+".bam", run_name+".bam.bai", bamdir], cwd=f"{working_path}")

    # iterate through possible reference files, removing them all
    for r in [reference_file_name, reference_file_name+'.fai', reference_file_name+".fa"]:
        if os.path.isfile(os.path.join(resultdir, r)):
            os.remove(os.path.join(resultdir, r))
    # subprocess.run(["rm", reference_file_name, reference_file_name+'.fai', reference_file_name+".fa"], cwd=f"{resultdir}")

    # remove the workspace folder from wf-human-variation
    if os.path.isdir(os.path.join(working_path, 'workspace')):
        shutil.rmtree(os.path.join(working_path, 'workspace'))
    # subprocess.run(["rm", "-r", "workspace"], cwd=f"{working_path}")

    # remove the wf-human-variation reference cache
    if os.path.isdir(os.path.join(working_path, 'output', 'ref_cache')):
        shutil.rmtree(os.path.join(working_path, 'output', 'ref_cache'))

    # move the wf-human-variation output to the output directory
    if os.path.isdir(os.path.join(working_path, 'output')):
        shutil.move(os.path.join(working_path, 'output'), nextflowdir)
    # subprocess.run(["mv", 'output', nextflowdir], cwd=working_path)

    # remove the workspace directory
    if os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(working_path)), id)):
        shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(working_path)), id))
    # subprocess.run(["rm", "-r", id], cwd='/'.join(working_path.strip().split('/')[:-1]))

    # unzip report file
    subprocess.run(['pigz', '-d', run_name+'.regions.bed.gz'], cwd=os.path.join(nextflowdir, 'output'))

    # create a run summary for T2T
    createRunSummary(
        nextflowdir, 
        os.path.join(nextflowdir, 'output', '{run_name}.wf-human-alignment-report.html'), 
        'none',
        'none',
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-sv-report.html'),
        os.path.join(nextflowdir, 'output', 'execution', 'report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.regions.bed')
        )

    update_db(id, 'status', 'complete')
