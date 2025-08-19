import os
import json
import sys
import fnmatch

def delete_files_by_json(json_files):
    """Delete files listed in JSON files, supporting wildcard patterns"""
    failed_files = []
    deleted_count = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                patterns = json.load(f)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
            continue
        
        if not isinstance(patterns, list):
            print(f"Error: {json_file} must contain a list of file patterns")
            continue
        
        for pattern in patterns:
            # Handle both direct file paths and wildcard patterns
            if '*' in pattern:
                # For wildcard patterns, walk through directory
                for root, _, files in os.walk('.'):
                    for file in files:
                        file_path = os.path.join(root, file).replace('\\', '/')
                        if file_path.startswith('./'):
                            file_path = file_path[2:]  # Remove './' prefix
                        if fnmatch.fnmatch(file_path, pattern):
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                                print(f"Deleted: {file_path}")
                            except Exception as e:
                                failed_files.append((file_path, str(e)))
            else:
                # For direct file paths
                try:
                    if os.path.exists(pattern):
                        os.remove(pattern)
                        deleted_count += 1
                        print(f"Deleted: {pattern}")
                except Exception as e:
                    failed_files.append((pattern, str(e)))
    
    # Record failed deletions
    if failed_files:
        os.makedirs('_tmp', exist_ok=True)
        with open('_tmp/delFailFiles.txt', 'w', encoding='utf-8') as f:
            for file_path, error in failed_files:
                f.write(f"{file_path}: {error}\n")
        print(f"\nFailed to delete {len(failed_files)} files. See _tmp/delFailFiles.txt for details.")
    
    print(f"\nTotal files deleted: {deleted_count}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python delbyJson.py <json_file1> [json_file2 ...]")
        sys.exit(1)
    
    json_files = sys.argv[1:]
    delete_files_by_json(json_files)

if __name__ == '__main__':
    main() 