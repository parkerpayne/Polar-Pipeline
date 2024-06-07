CREATE TABLE progress (
    file_name   text,
    start_time  timestamp without time zone,
    status      text,
    end_time    timestamp without time zone,
    computer    text,
    id          text,
    signal      text,
    clair_model text,
    bed_file    text,
    reference   text,
    gene_source text,
    file_path text
);

CREATE TABLE status (
    name   text UNIQUE,
    status text
);