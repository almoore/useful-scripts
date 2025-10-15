import os
import glob
import re
import argparse


def extract_tf_names(file_content):
    """Extracts resource and module names from a Terraform file content."""
    pattern = r'^(resource|module)\s+"([^"]+)"\s+"([^"]+)"'
    matches = re.findall(pattern, file_content, re.MULTILINE)
    return matches


def generate_target_strings(names):
    """Generates Terraform resource target strings."""
    targets = []
    for category, name_type, name in names:
        if category == "module":
            target = f'module.{name}'
        else:  # For resources
            target = f'{name_type}.{name}'
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
                        help='Directory or pattern to search for Terraform files (default: current directory).')

    args = parser.parse_args()

    # Resolve file pattern
    file_paths = glob.glob(os.path.join(args.directory_or_pattern, '**/*.tf'),
                           recursive=True)

    # Process files to extract names and generate target paths
    target_strings = process_files(file_paths)

    if target_strings:
        print("Generated Terraform Target Strings:")
        for target in target_strings:
            print(target)
    else:
        print("No Terraform resources or modules found.")


if __name__ == "__main__":
    main()
