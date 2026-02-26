"""
Command-line interface for text2geo.

Usage:
    python -m text2geo download [dataset]    Download GeoNames data
    python -m text2geo geocode <query>       Geocode a place name
    python -m text2geo info                  Show dataset info
"""

import sys
from text2geo.data import download, available_datasets, is_downloaded, get_data_path


def main():
    if len(sys.argv) < 2:
        _print_help()
        return

    command = sys.argv[1]

    if command == "download":
        dataset = sys.argv[2] if len(sys.argv) > 2 else "cis"
        print(f"Downloading '{dataset}' dataset...")
        path = download(dataset)
        print(f"Done: {path}")

    elif command == "geocode":
        if len(sys.argv) < 3:
            print("Usage: python -m text2geo geocode <place_name> [--dataset cis]")
            return
        query = sys.argv[2]
        dataset = "cis"
        if "--dataset" in sys.argv:
            idx = sys.argv.index("--dataset")
            dataset = sys.argv[idx + 1]

        from text2geo import Geocoder
        geo = Geocoder(dataset=dataset)
        result = geo.geocode(query)
        if result:
            print(f"  Name:       {result['name']}")
            print(f"  Lat:        {result['lat']}")
            print(f"  Lon:        {result['lon']}")
            print(f"  Country:    {result['country']}")
            print(f"  Population: {result['population']:,}")
            print(f"  Score:      {result['score']}")
        else:
            print(f"  No match found for '{query}'")

    elif command == "info":
        print("Available datasets:\n")
        for name, desc in available_datasets().items():
            status = "downloaded" if is_downloaded(name) else "not downloaded"
            path = get_data_path(name)
            print(f"  {name:8s}  {desc:40s}  [{status}]")
            if is_downloaded(name):
                print(f"           {path}")
        print()

    else:
        _print_help()


def _print_help():
    print("text2geo - Offline fuzzy geocoder\n")
    print("Commands:")
    print("  download [dataset]      Download GeoNames data (ru / cis / world)")
    print("  geocode <place_name>    Geocode a place name")
    print("  info                    Show dataset status")
    print()
    print("Examples:")
    print("  python -m text2geo download cis")
    print('  python -m text2geo geocode "Москва"')


if __name__ == "__main__":
    main()
