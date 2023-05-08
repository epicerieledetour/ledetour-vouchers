#!/bin/bash

_db=$1

if [ -z "$_db" ]
then
    echo "usage: send_report [PATH_TO_DB]"
    exit 1
fi

if [ -z "$LDTVOUCHERS_MAIL_PASSWORD" ]
then
    echo "The environment variable LDTVOUCHERS_MAIL_PASSWORD must be set. Aborting."
    exit 1
fi

_stamp=`TZ='America/Montreal' date "+%F-%H%M%S"`
_dir=/var/www/ledetour-vouchers/reports

_report_name=vouchers-$_stamp-report.csv
_history_name=vouchers-$_stamp-history.csv

_report=$_dir/$_report_name
_history=$_dir/$_history_name

_url_root=https://vouchers.epicerieledetour.org/reports
_report_url=$_url_root/$_report_name
_history_url=$_url_root/$_history_name

mkdir -pv $_dir

sqlite3 -header -csv $_db "select * from v_report;" > $_report
sqlite3 -header -csv $_db "select * from v_history;" > $_history

_mail=/tmp/ledetour-vouchers-report-email.txt

echo "From: Charles Flèche <charles@epicerieledetour.org>" > $_mail
echo "To: Bon Solidaire <bonsolidaire@actiongardien.ca>" >> $_mail
echo "Subject: Bons d'achats" >> $_mail
echo >> $_mail
echo "Bonjour l'équipe des Bons Solidaires," >> $_mail
echo "ci-joint à ce message automatique le rapport des Bons Solidaires au $_stamp:" >> $_mail
echo "- Rapport: $_report_url" >> $_mail
echo "- Historique: $_history_url" >> $_mail

curl \
    --url 'smtps://smtp.gmail.com:465' \
    --ssl-reqd \
    --mail-from 'charles@epicerieledetour.org' \
    --mail-rcpt 'charles.fleche@free.fr' \
    --user "charles@epicerieledetour.org:$LDTVOUCHERS_MAIL_PASSWORD" \
    --upload-file $_mail
