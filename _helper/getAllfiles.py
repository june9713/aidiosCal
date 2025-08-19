import os
import json
import sys

def get_all_files(root_dir='.', exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = [
            './core', './backup', './__pycache__', 
            './game_states', './logs', './log'
        ]
    
    # Add additional exclude dirs from command line arguments
    if len(sys.argv) > 1:
        exclude_dirs.extend(sys.argv[1:])
    
    all_files = []
    
    for root, dirs, files in os.walk(root_dir):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if os.path.join(root, d).replace('\\', '/') not in exclude_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            # Convert Windows path to Unix-style
            rel_path = os.path.relpath(file_path, root_dir).replace('\\', '/')
            all_files.append(rel_path)
    
    return all_files

def main():
    # Read additional exclude dirs from file if exists
    additional_exclude_file = '_usrtest/additional_exclude_dirs.txt'
    additional_excludes = []
    if os.path.exists(additional_exclude_file):
        with open(additional_exclude_file, 'r') as f:
            additional_excludes = [line.strip() for line in f if line.strip()]
    
    # Get all files
    files = get_all_files(exclude_dirs=additional_excludes)
    
    # Write to JSON file
    with open('_helper/all_files.json', 'w', encoding='utf-8') as f:
        json.dump(files, f, indent=2, ensure_ascii=False)

if __name__ == '__main__':
    main() 