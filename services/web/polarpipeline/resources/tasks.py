import sys
sys.path.append('/usr/src/app/polarpipeline')
from celery import Celery
from lib import *
import time
import sys
import os
import configparser
import subprocess
from datetime import datetime

app = Celery('tasks', broker='pyamqp://guest:guest@10.21.5.24:5672/')


@app.task
def process(input_file_path, clair_model_name, gene_source_name, bed_file_name, reference_file_name, id):
    
    clair_model_path = os.path.join('/mnt/pipeline_resources/clair_models', clair_model_name)
    gene_source_path = []
    for name in gene_source_name:
        gene_source_path.append(os.path.join('/mnt/pipeline_resources/gene_source',name))
    # gene_source_path = os.path.join('/mnt/pipeline_resources/gene_source', gene_source_name)
    reference_path = os.path.join('/mnt/pipeline_resources/reference_files', reference_file_name)
    bed_file_path = []
    for name in bed_file_name:
        bed_file_path.append(os.path.join('/mnt/pipeline_resources/bed_files',name))
    # bed_file_path = os.path.join('/mnt/pipeline_resources/bed_files', bed_file_name)

    pc_name = whoami()
    
    CONFIG_FILE_PATH = '/mnt/pipeline_resources/config.ini'

    config = configparser.ConfigParser()

    config.read(CONFIG_FILE_PATH)
    
    if not os.path.isdir(config['General']['output_directory']):
        update_db(id, 'status', 'output path not found')
        quit()
    else: print('output path:', config['General']['output_directory'])

    if config.has_section(pc_name):
        threads = config[pc_name]['threads']
    else:
        threads = config['Default']['threads']

    print(f'threads detected: {threads}')

    if '/' + pc_name + '/' in input_file_path:
        print('file is local!')
        input_file_path = input_file_path.replace('/mnt', '/home')

    run_name = input_file_path.strip().split('/')[-1].split('.bam')[0].split('.fastq')[0]
    input_directory = input_file_path.strip().split(run_name)[0]

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
        if i == 3:
            print('could not be found. quitting.')
            update_db(id, 'status', 'file not found')
            quit()
    # bam = False
    # fast5 = False
    # for file in os.listdir(input_directory):
    #     if file.endswith('.bam'):
    #         bam = True
    #         input_dir = os.path.join()
    #     file.endswith('.fast5') or file.endswith('.pod5'):
    working_path = f'/home/{pc_name}/polarPipelineNFWork/{id}'

    if checksignal(id) == 'stop':
        abort(working_path, id)

    os.makedirs(working_path, exist_ok=True)
    command = ['cp', input_file_path, working_path]
    update_db(id, 'status', 'transferring in')
    update_db(id, 'computer', pc_name)
    if subprocess.run(command) == '0':
        print('cool ig')
    
    currentTime = datetime.now()
    formattedTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = os.path.join(config['General']['output_directory'],f'{formattedTime}_{run_name}')
    
    update_db(id, 'start_time', currentTime)
    
    # CHANGE FILENAMES TO INCLUDE TIME
    run_name = formattedTime + '_' + run_name

    subprocess.run(["mv", os.path.join(working_path, input_file_path.split('/')[-1]), os.path.join(working_path, run_name+'.'+input_file_path.split('/')[-1].split('.')[-1])])
    input_file_path = os.path.join(working_path, run_name+'.'+input_file_path.split('/')[-1].split('.')[-1])

    if not input_file_path.endswith('.bam'):

        if input_file_path.endswith('.fastq.gz'):
            subprocess.run(['pigz', '-d', input_file_path], cwd=working_path)
            input_file_path = input_file_path.replace('.fastq.gz', '.fastq')

        update_db(id, 'status', 'minimap')

        print('input: ' + working_path)
        print('output file destination: ' + output_dir)


        try:
            input_file_path = minimap2(input_file_path, reference_path, threads)
        except:
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            quit()
        
        update_db(id, 'status', 'view sort index')

        try:
            input_file_path = viewSortIndex(input_file_path, threads)
        except:
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            quit()
        
    if checksignal(id) == 'stop':
        abort(working_path, id)

    update_db(id, 'status', 'nextflow')
    # princess(working_path, run_name, clair_model_path, pc_name, reference_path)
    try:
        nextflow(input_file_path, working_path, reference_path, clair_model_path, threads)
    except:
        update_db(id, 'status', 'failed: nextflow')
        update_db(id, 'end_time', datetime.now())
        quit()

    if checksignal(id) == 'stop':
        abort(working_path, id)

    # if not os.path.isdir(os.path.join('/home', pc_name, 'polarPipelineWork', run_name, 'analysis/result')):
    #     update_db(id, 'status', 'failed: princess', conn)
    #     update_db(id, 'end_time', datetime.now(), conn)
    #     quit()        

    subprocess.run(["pigz", "-d", run_name+".wf_snp.vcf.gz"], cwd=f"{working_path}/output")

    try:
        outputfile = load_file(os.path.join(working_path, "output", run_name+".wf_snp.vcf"))
    except:
        update_db(id, 'status', 'failed: nextflow')
        update_db(id, 'end_time', datetime.now())
        quit()

    output = []
    for variant in outputfile:
        if variant.startswith('#'):
            output.append(variant)
            continue
        for goodline in parseAlts(variant):
            output.append(goodline)
    with open(os.path.join(working_path, "output", run_name+".sepAlt.wf_snp.vcf"), 'w') as opened:
        opened.write(''.join(output))
    

    update_db(id, 'status', 'vep')
    vep(os.path.join(working_path, 'output', run_name+'.sepAlt.wf_snp.vcf'), os.path.join(working_path, 'output', run_name+'.wf_sv.vcf.gz'), reference_path, threads)
    if checksignal(id) == 'stop':
        abort(working_path, id)

    if not os.path.isfile(os.path.join(working_path, 'output', run_name+'_vep_snv.tsv')) or not os.path.isfile(os.path.join(working_path, 'output', run_name+'_vep_sv.tsv')):
        update_db(id, 'status', 'failed: vep')
        update_db(id, 'end_time', datetime.now())

    output = []
    vep_snv_file = f'{working_path}/output/{run_name}_vep_snv.tsv'
    vep_sv_file = f'{working_path}/output/{run_name}_vep_sv.tsv'
    snipeff_file = f'{working_path}/output/{run_name}.sepAlt.wf_snp.vcf'
    sniffles_file = f'{working_path}/output/{run_name}.wf_sv.vcf'
    # for root, dirs, files in os.walk(input_dir):
    #     for filename in files:
    #         if run_name+'.' in filename or run_name+"_vep" in filename:
    #             full_path = os.path.join(root, filename)
    #             if 'vep' in filename.lower() and 'snv' in filename.lower() and filename.endswith('.tsv'):
    #                 vep_snv_file = os.path.join(root, filename)
    #             if 'vep' in filename.lower() and 'sv' in filename.lower() and filename.endswith('.tsv'):
    #                 vep_sv_file = os.path.join(root, filename)
    #             if filename.endswith('.vcf') and ('snv' in filename.lower() or 'snp' in filename.lower()):
    #                 snipeff_file = os.path.join(root, filename)
    #             if filename.endswith('.vcf') and ('sv' in filename.lower()):
    #                 sniffles_file = os.path.join(root, filename)

    if not os.path.isfile(vep_snv_file) or not os.path.isfile(vep_sv_file) or not os.path.isfile(snipeff_file) or not os.path.isfile(sniffles_file):
        print("failed to locate all necessary files in input directory.\nmissing:")
        if not os.path.isfile(vep_snv_file):
            print('\tvep snv')
        if not os.path.isfile(vep_sv_file):
            print('\tvep sv')
        if not os.path.isfile(snipeff_file):
            print('\tsnipeff')
        if not os.path.isfile(sniffles_file):
            print('\tsniffles')
        print('found:')
        if vep_snv_file:
            print('\tvep snv: '+vep_snv_file)
        if vep_sv_file:
            print('\tvep sv: '+vep_sv_file)
        if snipeff_file:
            print('\tsnipeff: '+snipeff_file)
        if sniffles_file:
            print('\tsniffles: '+sniffles_file)
        update_db(id, 'status', 'failed: merge')
        update_db(id, 'end_time', datetime.now())
        quit()
    else:
        print("found all files for run " + run_name + "!")
        print("vep snv: "+vep_snv_file, "vep sv: "+vep_sv_file, "snipeff: "+snipeff_file, "sniffles: "+sniffles_file, sep="\n")


    update_db(id, 'status', 'merging')

    try:
        output = mergeFiles(vep_snv_file, vep_sv_file, snipeff_file, sniffles_file)
    except:
        update_db(id, 'status', 'failed: merge')
        update_db(id, 'end_time', datetime.now())
        quit()

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

    if checksignal(id) == 'stop':
        abort(working_path, id)

    update_db(id, 'status', 'tabulating tools')
    print('adding tools...')
    try:
        output = addToolsColumn(output)
    except:
        update_db(id, 'status', 'failed: adding tools')
        update_db(id, 'end_time', datetime.now())
        quit()

    if checksignal(id) == 'stop':
        abort(working_path, id)

    update_db(id, 'status', 'collapsing duplicate rows')
    print('collapsing duplicate rows...')
    try:
        output = collapseDuplicateRows(output)
    except:
        update_db(id, 'status', 'failed: collapsing duplicate rows')
        update_db(id, 'end_time', datetime.now())
        quit()

    if checksignal(id) == 'stop':
        abort(working_path, id)

    resultdir = os.path.join(working_path, 'output')

    with open(os.path.join(variantdir, run_name+'_merged.bed'), 'w') as opened:
        opened.write(''.join(output))
    with open(os.path.join(variantdir, run_name+'_merged_N0.bed'), 'w') as nozeros:
        for line in output:
            if line.strip().split('\t')[8] != '0':
                nozeros.write(line)
    with open('/'.join(working_path.split('/')[:-1])+'temp.bed', 'w') as opened:
        opened.write(''.join(output))
    
    for i in range(len(bed_file_path)):

        update_db(id, 'status', 'intersecting')

        output = intersect('/'.join(working_path.split('/')[:-1])+'temp.bed', bed_file_path[i])

        if gene_source_name[i] != "No gene source":
            gene_source_file = load_file(gene_source_path[i])
            output = addGeneSource(output, gene_source_file)
            finalfile = os.path.join(finaldir, run_name + '_' + bed_file_name[i].replace('.bed', f'_{gene_source_name[i].split(".txt")[0]}.vcf'))
            with open(finalfile, 'w') as openFile:
                openFile.write(''.join(output))
        else:
            finalfile = os.path.join(intersectdir, run_name + '_' + bed_file_name[i].replace('.bed', '.vcf'))
            with open(finalfile, 'w') as openFile:
                openFile.write('\n'.join(output))

        # if not gene_source_name[i] == "No gene source":
        #     gene_source_file = load_file(gene_source_path[i])
        #     print('\tloaded gene source!')
        # try:
        #     bedoutput = intersect('/'.join(working_path.split('/')[:-1])+'temp.bed', bed_file_path[i], os.path.join(intersectdir, run_name + '_' + bed_file_name[i].replace('.bed', '.vcf')))
        # except:
        #     update_db(id, 'status', 'failed: intersection')
        #     update_db(id, 'end_time', datetime.now())
        #     quit()

        # # with open(os.path.join(intersectdir, run_name + '_' + bed_file_name[i].replace('.bed', '.vcf')), 'w') as opened:
        # #     opened.write(''.join(bedoutput))

        # if not gene_source_name[i] == 'No gene source':
        #     update_db(id, 'status', 'adding gene source')
        #     try:
        #         bedoutput = addGeneSource(bedoutput, gene_source_file)
        #     except:
        #         update_db(id, 'status', 'failed: add gene source')
        #         update_db(id, 'end_time', datetime.now())
        #         quit()
            # update_db(id, 'status', 'compiling candidates')
            # print('finding candidates...')
            # try:
            #     output = findCandidates(output)
            # except:
            #     update_db(id, 'status', 'failed: find candidates')
            #     update_db(id, 'end_time', datetime.now())
            #     quit()

            # columns = getColumns(output)
            # final_output = []
            # for line in output:
            #     tabbed_line = line.strip().split('\t')
            #     newline = tabbed_line[:columns['PRECISION']] + [tabbed_line[columns['SYMBOL']]] + tabbed_line[columns['PRECISION']:]
            #     final_output.append('\t'.join(newline)+'\n')

            # finalfile = os.path.join(finaldir, run_name + '_' + bed_file_name[i].replace('.bed', f'_{gene_source_name[i].split(".txt")[0]}.vcf'))
            # with open(finalfile, 'w') as openFile:
            #     openFile.write(''.join(output))

        print('done!')


    update_db(id, 'status', 'transferring completed files')
    currentTime = datetime.now()
    update_db(id, 'end_time', currentTime)
    subprocess.run(["mv", run_name+".sepAlt.wf_snp.vcf", run_name+".wf_sv.vcf", run_name+"_vep_snv.tsv", run_name+"_vep_sv.tsv", variantdir], cwd=f"{resultdir}")

    subprocess.run(["mv", run_name+".haplotagged.bam", run_name+".haplotagged.bam.bai", bamdir], cwd=f"{resultdir}")

    subprocess.run(["rm", reference_file_name, reference_file_name+'.fai', reference_file_name+".fa"], cwd=f"{resultdir}")
    subprocess.run(["rm", "-r", "ref_cache"], cwd=f"{resultdir}")
    subprocess.run(["rm", "-r", "workspace"], cwd=f"{working_path}")
    subprocess.run(["mv", 'output', nextflowdir], cwd=working_path)

    subprocess.run(['pigz', '-d', run_name+'.regions.bed.gz'], cwd=os.path.join(nextflowdir, 'output'))

    createRunSummary(
        nextflowdir, 
        os.path.join(nextflowdir, 'output', 'wf-human-variation-alignment-report.html'), 
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-cnv-report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-snp-report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-sv-report.html'),
        os.path.join(nextflowdir, 'output', 'execution', 'report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.regions.bed'))

    subprocess.run(["rm", "-r", id], cwd='/'.join(working_path.strip().split('/')[:-1]))

    update_db(id, 'status', 'complete')














@app.task
def processT2T(input_file_path, clair_model_name, bed_file_name, reference_file_name, id):
    clair_model_path = os.path.join('/mnt/pipeline_resources/clair_models', clair_model_name)
    reference_path = os.path.join('/mnt/pipeline_resources/reference_files', reference_file_name)
    bed_file_path = []
    for name in bed_file_name:
        bed_file_path.append(os.path.join('/mnt/pipeline_resources/bed_files', name))
    # bed_file_path = os.path.join('/mnt/pipeline_resources/bed_files', bed_file_name)

    pc_name = whoami()

    CONFIG_FILE_PATH = '/mnt/pipeline_resources/config.ini'

    config = configparser.ConfigParser()

    config.read(CONFIG_FILE_PATH)

    if not os.path.isdir(config['General']['output_directory']):
        update_db(id, 'status', 'output path not found')
        quit()
    else: print('output path:', config['General']['output_directory'])

    if config.has_section(pc_name):
        threads = config[pc_name]['threads']
    else:
        threads = config['Default']['threads']

    print(f'threads detected: {threads}')


    if '/' + pc_name + '/' in input_file_path:
        input_file_path = input_file_path.replace('/mnt', '/home')

    run_name = input_file_path.strip().split('/')[-1].split('.bam')[0].split('.fastq')[0]
    input_directory = input_file_path.strip().split(run_name)[0]

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
        if i == 3:
            print('could not be found. quitting.')
            update_db(id, 'status', 'file not found')
            quit()
    # bam = False
    # fast5 = False
    # for file in os.listdir(input_directory):
    #     if file.endswith('.bam'):
    #         bam = True
    #         input_dir = os.path.join()
    #     file.endswith('.fast5') or file.endswith('.pod5'):
    working_path = f'/home/{pc_name}/polarPipelineNFWork/{id}'

    if checksignal(id) == 'stop':
        abort(working_path, id)

    os.makedirs(working_path, exist_ok=True)
    command = ['cp', input_file_path, working_path]
    update_db(id, 'status', 'transferring in')
    update_db(id, 'computer', pc_name)
    if subprocess.run(command) == '0':
        print('cool ig')
    
    currentTime = datetime.now()
    formattedTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    
    update_db(id, 'start_time', currentTime)
    # CHANGE FILENAMES TO INCLUDE TIME
    run_name = formattedTime + '_' + run_name + '_T2T'

    output_dir = os.path.join(config['General']['output_directory'],f'{run_name}')

    subprocess.run(["mv", os.path.join(working_path, input_file_path.split('/')[-1]), os.path.join(working_path, run_name+'.'+input_file_path.split('/')[-1].split('.')[-1])])
    input_file_path = os.path.join(working_path, run_name+'.'+input_file_path.split('/')[-1].split('.')[-1])

    if not input_file_path.endswith('.bam'):
        update_db(id, 'status', 'minimap')

        print('input: ' + working_path)
        print('output file destination: ' + output_dir)

        try:
            input_file_path = minimap2(input_file_path, reference_path, threads)
        except:
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            quit()
        
        update_db(id, 'status', 'view sort index')

        try:
            input_file_path = viewSortIndex(input_file_path, threads)
        except:
            update_db(id, 'status', 'failed: minimap')
            update_db(id, 'end_time', datetime.now())
            quit()
        
    if checksignal(id) == 'stop':
        abort(working_path, id)

    update_db(id, 'status', 'nextflow')
    # princess(working_path, run_name, clair_model_path, pc_name, reference_path)
    try:
        y_nextflow(input_file_path, working_path, reference_path, clair_model_path, threads)
    except:
        update_db(id, 'status', 'failed: nextflow')
        update_db(id, 'end_time', datetime.now())
        quit()

    if checksignal(id) == 'stop':
        abort(working_path, id)

    # if not os.path.isdir(os.path.join('/home', pc_name, 'polarPipelineWork', run_name, 'analysis/result')):
    #     update_db(id, 'status', 'failed: princess', conn)
    #     update_db(id, 'end_time', datetime.now(), conn)
    #     quit()        

    subprocess.run(["pigz", "-d", run_name+".wf_sv.vcf.gz"], cwd=f"{working_path}/output")

    if not os.path.isfile(os.path.join(working_path, "output", run_name+".wf_sv.vcf")):
        update_db(id, 'status', 'failed: nextflow')
        update_db(id, 'end_time', datetime.now())
        quit()

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

    try:
        vcftobed(os.path.join(working_path, 'output', run_name+'.wf_sv.vcf'))
    except:
        update_db(id, 'status', 'failed: vcftobed')
        update_db(id, 'end_time', datetime.now())
        quit()

    

    # update_db(id, 'status', 'collapsing duplicate rows')
    # print('collapsing duplicate rows...')
    # try:
    #     output = collapseDuplicateRows(output)
    # except:
    #     update_db(id, 'status', 'failed: collapsing duplicate rows')
    #     update_db(id, 'end_time', datetime.now())
    #     quit()

    # if checksignal(id) == 'stop':
    #     abort(working_path, id)

    resultdir = os.path.join(working_path, 'output')
    
    
    for i in range(len(bed_file_path)):
        update_db(id, 'status', 'intersecting')
        try:
            intersect(os.path.join(working_path, 'output', run_name+'.wf_sv_bedded.bed'), bed_file_path[i], os.path.join(intersectdir, run_name+'_'+bed_file_name[i].replace('.bed', '.vcf')))
        except:
            update_db(id, 'status', 'failed: intersection')
            update_db(id, 'end_time', datetime.now())
            quit()

        print('done!')


    update_db(id, 'status', 'transferring completed files')
    currentTime = datetime.now()
    update_db(id, 'end_time', currentTime)

    subprocess.run(["mv", run_name+".bam", run_name+".bam.bai", bamdir], cwd=f"{working_path}")

    subprocess.run(["rm", reference_file_name, reference_file_name+'.fai', reference_file_name+".fa"], cwd=f"{resultdir}")
    subprocess.run(["rm", "-r", "ref_cache"], cwd=f"{resultdir}")
    subprocess.run(["rm", "-r", "workspace"], cwd=f"{working_path}")
    subprocess.run(["mv", 'output', nextflowdir], cwd=working_path)

    subprocess.run(["rm", "-r", id], cwd='/'.join(working_path.strip().split('/')[:-1]))

    subprocess.run(['pigz', '-d', run_name+'.regions.bed.gz'], cwd=os.path.join(nextflowdir, 'output'))

    createRunSummary(
        nextflowdir, 
        os.path.join(nextflowdir, 'output', 'wf-human-variation-alignment-report.html'), 
        'none',
        'none',
        os.path.join(nextflowdir, 'output', f'{run_name}.wf-human-sv-report.html'),
        os.path.join(nextflowdir, 'output', 'execution', 'report.html'),
        os.path.join(nextflowdir, 'output', f'{run_name}.regions.bed')
        )

    update_db(id, 'status', 'complete')
