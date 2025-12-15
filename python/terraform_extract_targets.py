#!/usr/bin/env python3
import os
import glob
import re
import argparse


def extract_tf_names(file_content):
    """Extracts resource and module names from a Terraform file content."""
    # Separate regex patterns for resources and modules
    resource_pattern = r'^resource\s+"([^"]+)"\s+"([^"]+)"'
    module_pattern = r'^module\s+"([^"]+)"'

    # Find all matches separately for resources and modules
    resource_matches = re.findall(resource_pattern, file_content, re.MULTILINE)
    module_matches = re.findall(module_pattern, file_content, re.MULTILINE)

    # Convert module matches to the same format
    module_matches_formatted = [('module', module_name) for module_name in
                                module_matches]

    # Combine all matches
    return resource_matches + module_matches_formatted


def generate_target_strings(names):
    """Generates Terraform resource target strings."""
    targets = []
    for item in names:
        if len(item) == 2 and item[0] == "module":
            # Module
            target = f'module.{item[1]}'
        elif len(item) == 2:
            # Resource
            target = f'{item[0]}.{item[1]}'
        targets.append(target)
    return targets


def process_files(file_paths):
    """Processes each file to extract names and generate target strings."""
    all_targets = []
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            content = file.read()
            tf_names = extract_tf_names(content)
            targets = generate_target_strings(tf_names)
            all_targets.extend(targets)
    return all_targets


def main():
    """Main function to process directories or specific file patterns."""
    # Setup argument parsing
    parser = argparse.ArgumentParser(
        description='Process Terraform files to generate target strings for resources and modules.')
    parser.add_argument('directory_or_pattern', nargs='?', default='.',
                        help='Directory, file, or pattern to search for Terraform files (default: current directory).')

    args = parser.parse_args()

    # Determine if input is a file or pattern
    if os.path.isfile(args.directory_or_pattern):
        # Single file provided
        file_paths = [args.directory_or_pattern]
    else:
        # Treat as pattern or directory
        file_pattern = os.path.join(args.directory_or_pattern, '*.tf')
        file_paths = glob.glob(file_pattern)

    # Process files to extract names and generate target paths
    target_strings = process_files(file_paths)

    if target_strings:
        print("terraform apply \\")
        for i, target in enumerate(target_strings):
            if i < len(target_strings) - 1:
                print(f'-target={target} \\')
            else:
                print(f'-target={target}')
    else:
        print("No Terraform resources or modules found.")


if __name__ == "__main__":
    main()
