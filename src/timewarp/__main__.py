"""CLI for Time Warp."""

import argparse
import sys
from pathlib import Path

from .app import TimeWarpApp


def dir_path_arg(path: str) -> Path:
    path = Path(path)
    if path.is_dir():
        return path
    else:
        raise argparse.ArgumentTypeError(f"{path} is not a valid path")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir', type=dir_path_arg, help='path to journal directory')
    args = parser.parse_args()
    app = TimeWarpApp(args.dir)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
