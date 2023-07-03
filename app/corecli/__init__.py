import argparse

parser = argparse.ArgumentParser(
    prog="ldtvouchers", description="Command line interface for ldtvouchers"
)

parser.add_argument("--db", help="Path to the database file")
