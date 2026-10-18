#!/bin/bash
set -e

# Creates dedicated test database on fresh volume initialization.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE hetu_test OWNER hetu;
EOSQL
