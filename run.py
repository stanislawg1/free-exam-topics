import argparse
from app import create_app

parser = argparse.ArgumentParser()
parser.add_argument("--cache", choices=["true", "false"], default="false")
args = parser.parse_args()

cache_enabled = args.cache == "true"

app = create_app(cache_enabled)


if __name__ == "__main__":
    app.run(debug=True)
