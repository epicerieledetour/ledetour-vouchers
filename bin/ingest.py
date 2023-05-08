#!python

import csv
import sys

_LINE = """curl -k -d '{{"state":1}}' -H "Authorization:Bearer {userid}" -H "Content-Type: application/json" -X PATCH https://localhost:8000/api/vouchers/{id}"""

reader = csv.DictReader(sys.stdin)
for row in reader:
  print(_LINE.format(**row))

