rm db.sqlite3
python -m app db init
python -m app users create --label=Dist1
python -m app users create --label=Dist2
python -m app emissions create
