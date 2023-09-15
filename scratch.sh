rm db.sqlite3
python -m ldtvouchers db init
python -m ldtvouchers users create --label=user1 --can_cashin=true --can_cashin_by_voucherid=true
python -m ldtvouchers users create --label=user2
python -m ldtvouchers emissions create
python -m ldtvouchers emissions import 1 tests/test_import.csv
# python -m ldtvouchers actions scan --userid 1 --voucherid 1