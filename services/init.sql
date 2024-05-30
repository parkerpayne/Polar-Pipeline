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

CREATE TABLE dbs (
    uid SERIAL PRIMARY KEY,
    date_time timestamp,
    filename text UNIQUE,
    dbname text,
    filepath text
);

CREATE TABLE cols (
    uid SERIAL PRIMARY KEY,
    col_name text UNIQUE,
    col_type text
);

CREATE TABLE db_cols (
    db_uid INT REFERENCES dbs(uid),
    col_uid INT REFERENCES cols(uid),
    PRIMARY KEY (db_uid, col_uid)
);

CREATE INDEX idx_db_uid ON db_cols (db_uid);
CREATE INDEX idx_col_uid ON db_cols (col_uid);