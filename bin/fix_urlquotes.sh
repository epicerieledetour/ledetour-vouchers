#!/usr/bin/sh

_in=$1

sed -i 's/%7B/{/g' $_in
sed -i 's/%7D/}/g' $_in

