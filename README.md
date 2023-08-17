# Épicerie Le Détour Vouchers System

## Request / Response chart

```mermaid
flowchart TD
    S(Start)
    S --> Q1

    Q1{Q1: Has voucherid ?}
    Q1 -- No --> Q2
    Q1 -- Yes --> Q3

    Q2{Q2: Is authentificating user valid ?}
    Q2Y[ok_user_authentified]:::ok
    Q2N[error_user_invalid_token]:::error
    Q2 -- Yes --> Q2Y
    Q2 -- No --> Q2N

    Q3{Q3: Is user valid ?}
    Q3N[error_voucher_unauthentified]:::error
    Q3 -- No --> Q3N
    Q3 -- Yes --> Q4

    Q4{Q4: Is voucher valid ?}
    Q4N[error_voucher_invalid_token]:::error
    Q4 -- No --> Q4N
    Q4 -- Yes --> Q5

    Q5{Q5: Is voucher expired ?}
    Q5Y[error_voucher_expired]:::error
    Q5 -- Yes --> Q5Y
    Q5 -- No --> Q6

    Q6{Q6: Has voucher already been cashedin ?}
    Q6N[ok_voucher_cashedin]:::ok
    Q6 -- No --> Q6N
    Q6 -- Yes --> Q7

    Q7{Q7: Has voucher been cashed by another user ?}
    Q7Y[error_voucher_cashedin_by_another_user]:::error
    Q7 -- Yes --> Q7Y
    Q7 -- No --> Q8

    Q8{Q8: Is it still possible to undo cashing the voucher in ?}
    Q8N[warning_voucher_cannot_undo_cashedin]:::warning
    Q8Y[warning_voucher_can_undo_cashedin]:::warning
    Q8 -- No --> Q8N
    Q8 -- Yes --> Q8Y

    classDef ok stroke:#0f0
    classDef warning stroke:#ffa500
    classDef error stroke:#f00
```

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
python -m python3 venv
venv/bin/activate
python -m pip install -e . -r requirements.txt

# Test
pytest

# Serve
python -m uvicorn app.main:app --reload --host 0.0.0.0 --ssl-keyfile ssl/ca.key --ssl-certfile ssl/ca.pem --ssl-keyfile-password nopasswd --env-file dev.env
```

### Genereate SSL certificate

```sh
cd ssl
openssl genrsa -des3 -out ssl/ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 1825 -out ssl/ca.pem
```

## WIP operations

### File a table

1. Create a stub CSV file with `python bin/generate_stub_table.py`
2. Edit the CSV by hand
3. Import it to the db with

```
sqlite3 db.sqlite3
> .import --csv --skip 1 --schema temp data.csv table_name
```
