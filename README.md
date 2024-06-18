# Épicerie Le Détour Vouchers System

## Develop

### Dependencies

- python>=3.7
- jq
- sqlite3
- pdfunite
- qrencode


### Run the server

```sh
# Install
python -m venv venv
source venv/bin/activate
python -m pip install -e . -r requirements.txt

# Test
pytest

# Serve
python -m uvicorn app.main:app --reload --host 0.0.0.0 --ssl-keyfile ssl/ca.key --ssl-certfile ssl/ca.pem --ssl-keyfile-password nopasswd --env-file dev.env
```

### Genereate SSL certificate

```sh
cd ssl
# Enter nopasswd on the password prompt
openssl genrsa -des3 -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 1825 -out ca.pem
```

## WIP operations

### File a table

1. Create a stub CSV file with `python bin/generate_stub_table.py`
2. Edit the CSV by hand
3. Import it to the db with

```
sqlite3 db.sqlite3
> .import --csv --skip 1 data.csv table_name
```

For vouchers:
```
sqlite3 db.sqlite3
> .import --csv --skip 1 vouchers.csv vouchers
```

4. Make an ingest.csv with at least two columns:
  - `id`: this is the voucher ID
  - `userid`: the ID of the user that will distribute the voucher

5. Create an ingestion script ingest.sh

```
python bin/ingest.py < ingest.csv > ingest.sh
```

6. Run a server

```
export LDTVOUCHERS_DB_PATH=`pwd`/emissions/2024-07-01/ledetour-vouchers.sqlite3
export LDTVOUCHERS_SERVE_STATIC_FILES=1

python -m uvicorn app.main:app --reload --host 0.0.0.0 --ssl-keyfile ssl/ca.key --ssl-certfile ssl/ca.pem --ssl-keyfile-password nopasswd
```

7. Run the ingestion script

```
sh ingest.sh
```

## Make a new emissions

1. Copy a previous emission
2. Empty the vouchers and history tables
3. Generate vouchers following the `File a table` procedure above
