# Épicerie Le Détour Vouchers System

## Develop

```sh
# Serve
uvicorn app.main:app --reload --host 0.0.0.0 --ssl-keyfile ssl/ca.key --ssl-certfile ssl/ca.pem --ssl-keyfile-password nopasswd
```

## Genereate SSL certificate

```sh
cd ssl
openssl genrsa -des3 -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 1825 -out ca.pem
```
