# type: ignore

from . import cli  # pragma: no cover

# Function here is just for pyproject.toml
# projects.scripts
def main():
    cli.parse_args()  # pragma: no cover

if __name__ == "__main__":
    main()

