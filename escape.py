import argparse
from escaperoom.engine import run



def main() -> None:
    parser = argparse.ArgumentParser(description="Cyber Escape Room")
    parser.add_argument("--start", metavar="start", type=str, help="enter the starting room")
    parser.add_argument("--data", metavar="data", type=str, help="enter the data path")
    parser.add_argument("--transcript", metavar="transcript", type=str, help="enter the log file path")

    args = parser.parse_args()

    run(args.start, args.data, args.transcript)

if __name__ == "__main__":
    main()

