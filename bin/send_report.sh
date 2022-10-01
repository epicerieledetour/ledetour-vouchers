#!/bin/bash

_db=$1


if [ -z "$_db" ]
then
    echo "usage: dump_report PATH_TO_DB]"
    exit 1
fi

if [ -z "$LDTVOUCHERS_MAIL_PASSWORD" ]
then
    echo "The environment variable LDTVOUCHERS_MAIL_PASSWORD must be set. Aborting."
    exit 1
fi

_stamp=`TZ='America/Montreal' date "+%F-%H%M%S"`
_dir=/tmp/ldt-vouchers/report_$_stamp

_report=$_dir/vouchers-$_stamp-report.csv
_history=$_dir/vouchers-$_stamp-history.csv

mkdir -pv $_dir

sqlite3 -header -csv $_db "select * from v_report;" > $_report
sqlite3 -header -csv $_db "select * from v_history;" > $_history

curl \
    --url 'smtps://smtp.gmail.com:465' \
    --ssl-reqd \
    --mail-from 'charles@epicerieledetour.org' \
    --mail-rcpt 'charles.fleche@gmail.com' \
    --user "charles@epicerieledetour.org:$LDTVOUCHERS_MAIL_PASSWORD" \
    -H "From: Charles Flèche <charles@epicerieledetour.org>" \
    -H "To: Charles Flèche <charles@epicerieledetour.org>" \
    -H "Subject: [vouchers] Rapport au $_stamp" \
    -F text="Bonjour Pointe-Saint-Charles, ci-joint le rapport automatique des bons d'achats au $_stamp." \
    -F attachment=@$_report \
    -F attachment=@$_history
