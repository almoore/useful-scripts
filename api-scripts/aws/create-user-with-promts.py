#!/usr/bin/env python3
import boto3


def group_selection(iam):
    rsp = iam.list_groups()
    groups = rsp['Groups']
    index = 1

    for group in groups:
        print(f'{index}: {group["GroupName"]}')
        index += 1

    option = int(input("Please pick a group number: "))
    name = groups[option-1]["GroupName"]
    print(f'You selected group {option}: {name}')
    return name


def name_prompt(iam):
    name = input('What is the username?: ')
    user_names = [ u.get('UserName') for u in iam.list_users().get("Users",[])]
    if name in user_names:
        print('That username alreay exists.')
        name = name_prompt(iam)
    return name
        


def main():
    iam = boto3.client('iam')
    name = name_prompt(iam)
    print(f'Captured the name {name}')
    group_name = group_selection(iam)
    print(f'Creating user {name}')
    iam.Create_user(UserName=name)
    print(f'Adding user {name} to the group {group_name}')
    iam.add_user_to_group(GroupName=group_name, UserName=name)
    


if __name__ == "__main__":
    main()
