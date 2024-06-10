#!/bin/bash

# Function to check if a directory is nonempty
is_nonempty_dir() {
    [ -d "$1" ] && [ "$(ls -A "$1")" ]
}

PROGRAMS="minimap2 samtools nextflow docker vep"
missing_files=()
for file in ${PROGRAMS}; do
    if ! command -v $file &> /dev/null; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    failed=()
    echo "The following programs are missing and will attempt to be installed:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done

    # Step 1: Install dependencies
    echo "Installing dependencies..."
    sudo apt update
    sudo apt install -y pigz ca-certificates curl bedtools tabix celery nfs-common python3-pip zlib1g-dev libbz2-dev liblzma-dev default-jre libncurses5-dev libncursesw5-dev libcurl4-openssl-dev screen
    pip install psycopg2-binary bs4
    sudo cpan DBI Math::CDF List::MoreUtils Module::Build

    if ! command -v "minimap2" &> /dev/null; then
        # Step 2: Download and setup Minimap2
        echo "Downloading and setting up Minimap2..."
        cd ~
        wget https://github.com/lh3/minimap2/releases/download/v2.28/minimap2-2.28_x64-linux.tar.bz2
        tar -xjf ~/minimap2-2.28_x64-linux.tar.bz2
        rm -r ~/minimap2-2.28_x64-linux.tar.bz2
        MINIMAP_DIR=~/minimap2-2.28_x64-linux
        echo "PATH=\"$MINIMAP_DIR:\$PATH\"" >> ~/.bashrc
        eval "$(cat ~/.bashrc | tail -n +10)"
    fi
    if ! command -v "minimap2" &> /dev/null; then
        failed+=("minimap2")
    fi

    if ! command -v "samtools" &> /dev/null; then
        # Step 3: Download and setup Samtools
        echo "Downloading and setting up Samtools..."
        cd ~
        wget https://github.com/samtools/samtools/releases/download/1.20/samtools-1.20.tar.bz2
        tar -xjf samtools-1.20.tar.bz2
        rm -r ~/samtools-1.20.tar.bz2
        cd samtools-1.20
        make
        sudo make install
        SAMTOOLS_DIR=~/samtools-1.20
        echo "PATH=\"$SAMTOOLS_DIR:\$PATH\"" >> ~/.bashrc
        eval "$(cat ~/.bashrc | tail -n +10)"
    fi
    if ! command -v "samtools" &> /dev/null; then
        failed+=("samtools")
    fi

    if ! command -v "nextflow" &> /dev/null; then
        # Step 4: Install Nextflow
        echo "Installing Nextflow..."
        cd ~
        curl -s https://get.nextflow.io | bash
        sudo mv nextflow /usr/local/bin
    fi
    if ! command -v "nextflow" &> /dev/null; then
        failed+=("nextflow")
    fi
    
    if ! command -v "docker" &> /dev/null; then
        # Step 5: Install Docker
        echo "Installing Docker..."
        sudo install -m 0755 -d /etc/apt/keyrings
        sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        sudo chmod a+r /etc/apt/keyrings/docker.asc
        echo \
          "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
          $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
          sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
        sudo apt-get update
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        # Docker post-installation steps
        sudo groupadd docker
        sudo usermod -aG docker $USER
    fi
    if ! command -v "docker" &> /dev/null; then
        failed+=("docker")
    fi

    if ! command -v "vep" &> /dev/null; then
        # Step 6: Install Vep
        # echo "Installing Vep..."
        # cd ~
        # curl -L -O https://github.com/Ensembl/ensembl-vep/archive/release/112.zip
        # unzip 112.zip
        # rm 112.zip
        # cd ensembl-vep-release-112/
        # perl INSTALL.pl --NO_UPDATE --AUTO apc --PLUGINS AlphaMissense,CADD,Carol,Condel,dbNSFP,DisGeNET,EVE,LoFtool,Mastermind,pLI,PrimateAI,REVEL --SPECIES homo_sapiens,homo_sapiens_merged,homo_sapiens_refseq --ASSEMBLY GRCh38

        # # # initialize vep-resources directory
        # cd ~
        # mkdir vep-resources

        # # Alphamissense
        # cd ~/vep-resources
        # curl https://storage.googleapis.com/storage/v1/b/dm_alphamissense/o/AlphaMissense_hg38.tsv.gz?alt=media --output AlphaMissense_hg38.tsv.gz
        # tabix -s 1 -b 2 -e 2 -f -S 1 AlphaMissense_hg38.tsv.gz

        # # CADD
        # cd ~/vep-resources
        # wget https://krishna.gs.washington.edu/download/CADD/v1.7/GRCh38/whole_genome_SNVs.tsv.gz
        # wget https://krishna.gs.washington.edu/download/CADD/v1.7/GRCh38/whole_genome_SNVs.tsv.gz.tbi

        # # dbNSFP
        # cd ~/vep-resources
        # version=4.8a
        # wget https://dbnsfp.s3.amazonaws.com/dbNSFP4.8a.zip
        # unzip dbNSFP${version}.zip
        # zcat dbNSFP${version}_variant.chr1.gz | head -n1 > h
        # zgrep -h -v ^#chr dbNSFP${version}_variant.chr* | sort -k1,1 -k2,2n - | cat h - | bgzip -c > dbNSFP${version}_grch38.gz
        # tabix -s 1 -b 2 -e 2 dbNSFP${version}_grch38.gz

        # EVE
        cd ~/vep-resources
        wget -O EVE_all_data.zip https://evemodel.org/api/proteins/bulk/download/
        unzip EVE_all_data.zip
        rm EVE_all_data.zip
        DATA_FOLDER=./vcf_files_missense_mutations
        OUTPUT_FOLDER=./
        OUTPUT_NAME=eve_merged.vcf 
        cat `ls ${DATA_FOLDER}/*vcf | head -n1` > header
        # Get variants from all VCFs and add to a single-file
        ls ${DATA_FOLDER}/*vcf | while read VCF; do grep -v '^#' ${VCF} >> variants; done
        # Merge Header + Variants in a single file
        cat header variants | \
        awk '$1 ~ /^#/ {print $0;next} {print $0 | "sort -k1,1V -k2,2n"}' > ${OUTPUT_FOLDER}/${OUTPUT_NAME};
        # Remove temporary files
        rm header variants
        # Compress and index
        bgzip ${OUTPUT_FOLDER}/${OUTPUT_NAME};
        # If not installed, use: sudo apt install tabix
        tabix ${OUTPUT_FOLDER}/${OUTPUT_NAME}.gz;
        rm -r $DATA_FOLDER

        # # LoFtool
        # cd ~/vep-resources
        # wget https://raw.githubusercontent.com/Ensembl/VEP_plugins/release/112/LoFtool_scores.txt

        # # pLI
        # cd ~/vep-resources
        # wget https://raw.githubusercontent.com/Ensembl/VEP_plugins/release/112/pLI_values.txt

        # PrimateAI
        # mail: u250951@bcm.edu
        # password: P0l4rpswd!
        # cd ~/vep-resources
        # This is technically possible. you need to go set up an API key on their website and then use that to authenticate the download. best of luck.
        # https://developer.basespace.illumina.com/docs/content/documentation/authentication/obtaining-access-tokens

        # REVEL
        # cd ~/vep-resources
        # wget https://rothsj06.dmz.hpc.mssm.edu/revel-v1.3_all_chromosomes.zip
        # unzip revel-v1.3_all_chromosomes.zip
        # cat revel_with_transcript_ids | tr "," "\t" > tabbed_revel.tsv
        # sed '1s/.*/#&/' tabbed_revel.tsv > new_tabbed_revel.tsv
        # bgzip new_tabbed_revel.tsv
        # rm revel-v1.3_all_chromosomes.zip

        # cd ~
        # VEP_DIR=~/ensembl-vep-release-112/
        # echo "PATH=\"$VEP_DIR:\$PATH\"" >> ~/.bashrc
        # eval "$(cat ~/.bashrc | tail -n +10)"

    fi
    if ! command -v "vep" &> /dev/null; then
        failed+=("vep")
    fi


    if [ ${#failed[@]} -gt 0 ]; then
        echo "The following programs failed to install:"
        for program in "${failed[@]}"; do
            echo "  - $program"
        done
        exit 1
    else
      echo "Setup completed successfully. Please restart your machine."
    fi
else

    # Function to check if a line is in the fstab
    check_fstab() {
        grep -qF "$FSTAB_LINE" /etc/fstab
    }

    # Function to add line to fstab
    add_fstab() {
        echo "$FSTAB_LINE" | sudo tee -a /etc/fstab
    }

    # Function to check if directory exists
    check_directory_exists() {
        [ -d "$1" ]
    }

    # Function to create directory
    create_directory() {
        sudo mkdir -p "$1"
    }

    # Function to check if directory is empty
    check_directory_empty() {
        [ -z "$(ls -A "$1")" ]
    }

    # Function to mount directory
    mount_directory() {
        sudo mount "$1"
    }

    # Function to check if tasks.py exists
    check_tasks_py() {
        [ -f "$1/tasks.py" ]
    }

    # Check if the provided line is in the fstab
    if ! check_fstab; then
        echo "Line not found in /etc/fstab. Adding it..."
        add_fstab
    else
        echo "Line already exists in /etc/fstab."
    fi

    # Check if the directory /mnt/pipeline_resources exists
    MNT_DIR="/mnt/pipeline_resources"
    if ! check_directory_exists "$MNT_DIR"; then
        echo "Directory $MNT_DIR does not exist. Creating it..."
        create_directory "$MNT_DIR"
    else
        echo "Directory $MNT_DIR already exists."
    fi

    # Check if the directory is empty
    if check_directory_empty "$MNT_DIR"; then
        echo "Directory $MNT_DIR is empty. Attempting to mount..."
        if mount_directory "$MNT_DIR"; then
            echo "Mount succeeded."
        else
            echo "Mount failed. Exiting."
            exit 1
        fi
    else
        echo "Directory $MNT_DIR is not empty."
    fi

    # Check if tasks.py exists in the mounted directory
    if check_tasks_py "$MNT_DIR"; then
        echo "tasks.py found in $MNT_DIR."
    else
        echo "tasks.py not found in $MNT_DIR. Exiting."
        exit 1
    fi

    echo "Starting worker!"
    cd $MNT_DIR
    LOG_FILE="$MNT_DIR/worker_logs/$USER.log"
    SCREEN_SESSION="polarpipelineworker"
    COMMAND="celery -A tasks worker --concurrency=1 --prefetch-multiplier=1 --loglevel=INFO > $LOG_FILE 2>&1"
    screen -dmS $SCREEN_SESSION bash -c "$COMMAND"
    # screen -S $USER.polarpipelineworker
    # screen -r $USER.polarpipelineworker
    # cd $MNT_DIR
    # cd ~/newPipeline
    # celery -A tasks worker --concurrency=1 --prefetch-multiplier=1 --loglevel=INFO > $MNT_DIR/$USER.log 2>&1

fi