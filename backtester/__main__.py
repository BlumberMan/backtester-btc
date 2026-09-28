import sys

from backtester import __version__


def check_python_version(version_info):
    major, minor = version_info[0], version_info[1]
    return (major, minor) == (3, 14)


def main():
    found = f"{sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]}"
    if not check_python_version(sys.version_info):
        print(f"Error: Python 3.14 is required, found Python {found}.", file=sys.stderr)
        return 1
    print(f"backtester-btc v{__version__} - Python {found}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
