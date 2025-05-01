import json

import boto3
import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('hosted_zone_id')
    parser.add_argument('--exclude-file', help='A json file with a list of entries to excludecd ')
    return parser.parse_args()


def get_route53_records(hosted_zone_id):
    profile_name = os.getenv('AWS_PROFILE', 'default')

    # Create a session using the specified profile
    session = boto3.Session(profile_name=profile_name)
    """Fetches all record sets from a specified AWS Route 53 hosted zone."""
    client = session.client('route53')

    paginator = client.get_paginator('list_resource_record_sets')
    records = []

    for page in paginator.paginate(HostedZoneId=hosted_zone_id):
        records.extend(page['ResourceRecordSets'])

    return records

def route53_record_to_terraform(record, hosted_zone_id):
    """Converts a Route 53 record set to a Terraform resource configuration."""
    record_name = record['Name'].rstrip('.').replace('\\052', '*')
    record_type = record['Type']
    set_identifier = record.get('SetIdentifier')
    tf_resource_name = f"{record_type.lower()}_{record_name.replace('.', '_').replace('-', '_').replace('*', 'star')}"
    if set_identifier:
        tf_resource_name = f"{tf_resource_name}_{set_identifier.replace('-', '_')}"

    tf_resource = f'resource "aws_route53_record" "{tf_resource_name}" {{\n'
    tf_resource += f'  zone_id = "{hosted_zone_id}"\n'
    tf_resource += f'  name    = "{record_name}"\n'
    tf_resource += f'  type    = "{record["Type"]}"\n'

    if 'TTL' in record:
        tf_resource += f'  ttl     = {record["TTL"]}\n'

    # Handle the different record types
    if 'ResourceRecords' in record:
        value_list = ', '.join([f'"{r["Value"].replace('"', '')}"' for r in record['ResourceRecords']])
        if len(value_list) > 80:
            value_list = f"\n{value_list.replace(', ', ',\n    ')}\n"
        tf_resource += f'  records = [{value_list}]\n'
    elif 'AliasTarget' in record:
        alias_target = record['AliasTarget']
        tf_resource += f'  alias {{\n'
        tf_resource += f'    name    = "{alias_target["DNSName"]}"\n'
        tf_resource += f'    zone_id = "{alias_target["HostedZoneId"]}"\n'
        tf_resource += f'    evaluate_target_health = {str(alias_target["EvaluateTargetHealth"]).lower()}\n'
        tf_resource += f'  }}\n'

    if set_identifier and 'Weight' in record:
        tf_resource += f'  set_identifier   = "{record["SetIdentifier"]}"\n'
        tf_resource += f'  weighted_routing_policy {{\n'
        tf_resource += f'    weight = {record["Weight"]}\n'
        tf_resource += f'  }}\n'

    tf_resource += '}\n'
    return tf_resource

def generate_terraform_import_commands(records, zone_id, exclude):
    import_commands = []
    for record in records:
        skip = False
        for exclude_record in exclude:
            if record['Name'].rstrip('.') == exclude_record['name'] and record['Type'] == exclude_record['type']:
                skip = True
        if skip:
            continue
        record_name = record['Name'].rstrip('.').replace('\\052', '*')
        record_type = record['Type']
        set_identifier = record.get('SetIdentifier')

        # Construct the unique record ID
        if set_identifier:
            record_id = f"{zone_id}_{record_name}_{record_type}_{set_identifier}"
        else:
            record_id = f"{zone_id}_{record_name}_{record_type}"

        # Determine the Terraform resource name
        tf_resource_name = f"{record_type.lower()}_{record_name.replace('.', '_').replace('-', '_').replace('*', 'star')}"
        if set_identifier:
            tf_resource_name = f"{tf_resource_name}_{set_identifier.replace('-', '_')}"
        # Replace any other invalid characters for a Terraform resource name as needed

        import_command = f"terraform import aws_route53_record.{tf_resource_name} {record_id}"
        import_commands.append(import_command)

    return import_commands

def main():
    args = parse_args()
    print(args)
    hosted_zone_id = args.hosted_zone_id
    records = get_route53_records(hosted_zone_id)
    terraform_configs = []
    exclude = []
    if args.exclude_file:
        with open(args.exclude_file) as f:
            exclude = json.load(f)

    for record in records:
        skip = False
        record_name = record['Name'].rstrip('.').replace('\\052', '*')
        for exclude_record in exclude:
            if record_name == exclude_record['name'] and record['Type'] == exclude_record['type']:
                print(f"Skipping: {exclude_record}")
                skip = True
        if skip:
            continue
        tf_resource = route53_record_to_terraform(record, hosted_zone_id)
        terraform_configs.append(tf_resource)

    with open('route53_records.tf', 'w') as tf_file:
        for config in terraform_configs:
            tf_file.write(config + '\n\n')
    print("Terraform configuration file 'route53_records.tf' has been created.")

    import_commands = generate_terraform_import_commands(records, hosted_zone_id, exclude)
    with open('import_route53_records.sh', 'w') as sh_file:
        sh_file.write('\n'.join(import_commands))
    print("Terraform import file 'import_route53_records.sh' has been created.")


if __name__ == "__main__":
    main()
