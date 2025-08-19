#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys

def try_encodings(file_path, encodings=['utf-8', 'euc-kr', 'cp949']):
    """Try different encodings to read the file"""
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.readlines(), encoding
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Could not read file with any of the encodings: {encodings}")

def split_file(input_file, output_dir, lines_per_file):
    """Split a file into smaller files with specified number of lines"""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the input file with proper encoding
    try:
        lines, encoding = try_encodings(input_file)
    except UnicodeDecodeError as e:
        print(f"Error: {e}")
        return
    
    # Get base filename without extension
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    
    # Calculate total number of files needed
    total_lines = len(lines)
    file_count = (total_lines + lines_per_file - 1) // lines_per_file
    
    # Split the file
    for i in range(file_count):
        start_idx = i * lines_per_file
        end_idx = min((i + 1) * lines_per_file, total_lines)
        
        output_file = os.path.join(output_dir, f"{base_name}_part{i+1:03d}.txt")
        
        with open(output_file, 'w', encoding=encoding) as f:
            f.writelines(lines[start_idx:end_idx])
        
        print(f"Created {output_file}")

def main():
    if len(sys.argv) != 4:
        print("Usage: python splitFileline_for_only_encodedstr.py <input_file> <output_dir> <lines_per_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_dir = sys.argv[2]
    try:
        lines_per_file = int(sys.argv[3])
    except ValueError:
        print("Error: lines_per_file must be an integer")
        sys.exit(1)
    
    split_file(input_file, output_dir, lines_per_file)

if __name__ == '__main__':
    main() 