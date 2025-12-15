import argparse
from googleapiclient import discovery
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError


def list_gpu_types_and_availability(project, specific_region=None):
    # Use Application Default Credentials to authenticate API client
    credentials, default_project = default()

    # Use the default project if no project ID is provided
    if not project:
        project = default_project
        if not project:
            raise ValueError(
                "No project ID provided and could not determine the default project. "
                "Please set the Cloud project using 'gcloud config set project PROJECT_ID' or specify the project ID using the command line.")

    service = discovery.build('compute', 'v1', credentials=credentials)
    regions_request = service.regions().list(project=project)

    while regions_request is not None:
        response = regions_request.execute()

        # Iterate over each region or just the specified one
        for region in response['items']:
            region_name = region['name']
            if specific_region and region_name != specific_region:
                continue

            print(f'Region: {region_name}')

            # Request zones for the region
            zones_request = service.zones().list(project=project,
                                                 filter=f'region eq .*{region_name}.*')
            zones_response = zones_request.execute()

            # Check GPU availability in each zone
            for zone in zones_response.get('items', []):
                zone_name = zone['name']

                # Request available accelerator (GPU) types for the zone
                try:
                    accelerator_types_request = service.acceleratorTypes().list(
                        project=project, zone=zone_name
                    )
                    accelerator_types_response = accelerator_types_request.execute()

                    # Print out available GPU types in this zone
                    for accelerator_type in accelerator_types_response.get(
                        'items', []):
                        print(
                            f"  - {accelerator_type['name']} available in zone {zone_name}: {accelerator_type['description']}")

                except Exception as e:
                    print(
                        f"Failed to retrieve GPU types for zone {zone_name}: {e}")

        regions_request = service.regions().list_next(
            previous_request=regions_request, previous_response=response)


def main():
    parser = argparse.ArgumentParser(
        description='List GPU types in GCP regions.')
    parser.add_argument('--project', type=str,
                        help='Google Cloud project ID (optional)')
    parser.add_argument('--region', type=str,
                        help='Specific region to check for GPUs', default=None)

    args = parser.parse_args()

    try:
        list_gpu_types_and_availability(args.project, args.region)
    except ValueError as e:
        print(e)


if __name__ == '__main__':
    main()
