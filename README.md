# Polar Pipeline
is a pipeline for the purpose of analyzing human genomic data.

## Table of Contents

- [Introduction](#introduction)
- [Key Components](#key-components)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Introduction

The Polar Pipeline is a powerful Flask-based web application and pipeline tailored for the seamless execution of genomic data analysis pipelines. It is meticulously designed to provide efficient and user-friendly access to advanced genomic research tools. Some features like changing what VEP plugins are included are not part of this program, so changing these will require coding knowledge. It is designed for Ubuntu.

## Key Components

- **Webapp:** A user friendly frontend for file organization, data processing, task handling, and minor analysis.

- **Backend:** The application hosted through Flask, and is backed by a PostgreSQL server, the RabbitMQ message broker, and the Celery job queue.

- **Job Handling:** Utilizing the power of Celery, the application efficiently manages and schedules data analysis jobs, allowing for parallel processing and optimal resource utilization.

## Features

- **Streamlined Analysis:** The included web application simplifies the complex process of analyzing human genomic data, making it accessible to researchers and scientists with varying levels of expertise.

- **Scalability:** With Celery's job queuing system, the application scales effortlessly to handle more simultaneous computations across multiple computers, automatically distributing the workload without the use of clusters.

- **User-friendly Interface:** A user-friendly and intuitive interface allows users to submit and monitor genomic data analysis tasks with ease.

- **Variant Figure Generator:** Included in the web application is a generator for displaying locations of variants on genes. Supports Heterozygous and Homozygous variants, as well as Heterozygous genes with varying structures.

- **Personalization:** In the event that computers connected to the pipeline have differing levels of processing power, the threads for each computer can be set manually.

- **Convenience:** The output of this pipeline will have both structural variants and single nucleotide variants combined into one file, in the same format. Information that was not retained when utilizing VEP is recovered and inserted into the output files.

## Installation
This pipeline was developed and tested on Ubuntu. Other debian-based distros should work, such as Mint, but they are similarly untested. As it is in a Docker container, it may be possible to host the application on a Windows host, but in depth knowledge will be required to set up.
1. Install Docker on the to-be host machine.
2. Download the polarpipelineserver folder to the host machine.
3. Install vep 
3. Run ```sudo docker compose up -d --build``` in the polarpipelineserver directory.
4. The Polar Pipeline webapp will build and begin hosting. The default IP on the host machine is ```10.20.0.88:5000```, but ```localhost:5000``` will work.
5. ~~Create worker machines following the instructions in the setup page on the Polar Pipeline website.~~

## Usage
1. Place fastq, fastq.gz, or .bam files to be processed in the polarpipelineserver folder's 'mnt' directory.
2. Go to the configuration tab on the Polar Pipeline website, and upload needed reference files, clair models, bed files, and gene source files.
3. Go to the home page of the Polar Pipeline website and select the file to be processed.
4. Make selections, including what type of sample, a bed file to intersect with, etc.
5. Hit start, and head to the dashboard tab to view progress.
6. Output will be as defined in the configuration tab, under the "General" dropdown. This is in reference to the worker computers, not the host.

## Contribution
Even though the programs are not included in this repository, the following tools are necessary for the usage of the Polar Pipeline.
- [Minimap2](https://github.com/lh3/minimap2)
- [Nextflow](https://www.nextflow.io/)
- [epi2me-labs/wf-human-variation](https://github.com/epi2me-labs/wf-human-variation)
- [samtools](http://www.htslib.org/)
- [bedtools](https://bedtools.readthedocs.io/en/latest/)
- [Varient Effect Predictor]()

## License
This project is licensed under the terms of the MIT License. See the [LICENSE](LICENSE.md) file for the full license text.
