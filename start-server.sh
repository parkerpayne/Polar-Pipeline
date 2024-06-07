#!/bin/bash

# Function to check if a directory is nonempty
is_nonempty_dir() {
    [ -d "$1" ] && [ "$(ls -A "$1")" ]
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Installing Docker..."
    
    # Install Docker
    sudo apt-get install -y ca-certificates curl
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

    echo "Docker installation completed. Please restart your machine."
    exit 0
else
    echo "Docker is already installed."
    
    # Check the mnt directory
    MNT_DIR="./mnt"
    if [ -d "$MNT_DIR" ]; then
        all_nonempty=true
        for dir in "$MNT_DIR"/*; do
            if [ -d "$dir" ]; then
                if ! is_nonempty_dir "$dir"; then
                    echo "Directory $dir is empty. There appear to be input/output directories that have failed to mount. If they appear to be mounted, run the fixmounts script."
                fi
            fi
        done
        
        if $all_nonempty; then
            echo "All directories in $MNT_DIR are mounted."
            
        fi
    else
        echo "Directory $MNT_DIR does not exist."
        exit 1
    fi
fi

VEP_DIR="./services/web/vep"
declare -A required_files=(
    ["SNV Report"]="$VEP_DIR/ensembl-vep/ $VEP_DIR/vep-resources/ $VEP_DIR/.vep/ $VEP_DIR/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai $VEP_DIR/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.index $VEP_DIR/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta"
    ["SV Report"]="$VEP_DIR/hg38.refGene $VEP_DIR/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.fai $VEP_DIR/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta.index $VEP_DIR/GCA_000001405.15_GRCh38_no_alt_analysis_set.fasta"
)

for report in "${!required_files[@]}"; do
    missing_files=()
    for file in ${required_files[$report]}; do
        if [ ! -e "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -gt 0 ]; then
        echo "WARNING: The following files/directories needed by $report are missing:"
        for file in "${missing_files[@]}"; do
            echo "  - $file"
        done
        echo "$report will not work properly without these files/directories. It is recommended to install vep on a worker by running the start-worker script, then move the files to the $VEP_DIR directory."
    else
        echo "All required files for $report are present."
    fi
done

IP_ADDR=$(hostname -I | awk '{print $1}')
RSRC_DIR="$PWD/services/web/polarpipeline/resources"
STC_DIR="$PWD/services/web/polarpipeline/static"
FSTAB_FILE="$STC_DIR/fstab.tmp"
FSTAB_LINE="$IP_ADDR:$RSRC_DIR	/mnt/pipeline_resources	nfs	defaults	0	0"
echo "$FSTAB_LINE" > $FSTAB_FILE
docker compose up -d