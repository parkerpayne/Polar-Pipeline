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

CREATE TABLE frequency (
    id text,
    _1_0 integer,
    _0_1 integer,
    _1__1 integer,
    _d__d integer,
    _0__0 integer,
    _0__1 integer,
    _1__2 integer,
    samples jsonb
);

