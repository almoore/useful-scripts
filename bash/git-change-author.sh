#!/bin/bash

usage(){
read -r -d '' USAGE << EOU
Usage: ${0##*/} old_email new_email
  This tool is meant to easily change
  the git history commit author. 

Options:
    -u USERNAME    The username to use 
EOU
echo -e "$USAGE"
}

while [ "$1" != "" ] ; do
    case $1 in
        -u | --user )
            shift
            USER=$1
        ;;
        -h | --help )
            usage
            exit
        ;;
        *)
            ARGS+=( $1 )
        ;;
    esac
    shift
done

if [ ${#ARGS[@]} -lt 2 ]; then
    echo "You only entered ${#ARGS[@]} args 2 are required"
    echo ""
    usage
    exit 1
fi

if [ -z "$USER" ]; then
    USER=$(git config --get user.name)
fi

TMPFILE=$(mktemp)
echo $TMPFILE

cat << EOF > $TMPFILE
git filter-branch --env-filter '

OLD_EMAIL="${ARGS[0]}"
CORRECT_NAME="${USER}"
CORRECT_EMAIL="${ARGS[1]}"

if [ "\$GIT_COMMITTER_EMAIL" = "$OLD_EMAIL" ]
then
    if [ -z "\${CORRECT_NAME}" ]; then
    export GIT_COMMITTER_NAME="\$CORRECT_NAME"
    fi
    export GIT_COMMITTER_EMAIL="\$CORRECT_EMAIL"
fi
if [ "\$GIT_AUTHOR_EMAIL" = "\$OLD_EMAIL" ]
then
    if [ -z "\${CORRECT_NAME}" ]; then
    export GIT_AUTHOR_NAME="\$CORRECT_NAME"
    fi
    export GIT_AUTHOR_EMAIL="\$CORRECT_EMAIL"
fi
' --tag-name-filter cat -- --branches --tags
EOF

cat $TMPFILE
bash $TMPFILE
rm $TMPFILE
