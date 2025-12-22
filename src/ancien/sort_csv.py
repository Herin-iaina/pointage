import csv
import argparse
import sys
import os

def sort_csv(input_file, output_file=None, sort_column='user_id'):
    """
    Sorts a CSV file by a given column.
    """
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return

    try:
        with open(input_file, mode='r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            
            if sort_column not in fieldnames:
                print(f"Error: Column '{sort_column}' not found in CSV. Available columns: {', '.join(fieldnames)}")
                return

            data = list(reader)
            
            # Try to convert to int for sorting if possible, otherwise string sort
            try:
                data.sort(key=lambda x: int(x[sort_column]) if x[sort_column] else 0)
            except ValueError:
                data.sort(key=lambda x: x[sort_column])

        if output_file is None:
            output_file = input_file

        with open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
        print(f"Successfully sorted '{input_file}' by '{sort_column}' and saved to '{output_file}'.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sort a CSV file by a specific column.")
    parser.add_argument("input_file", help="Path to the input CSV file")
    parser.add_argument("-o", "--output", help="Path to the output CSV file (optional, overwrites input if not provided)")
    parser.add_argument("-c", "--column", default="user_id", help="Column to sort by (default: user_id)")

    args = parser.parse_args()

    sort_csv(args.input_file, args.output, args.column)
