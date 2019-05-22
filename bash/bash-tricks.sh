#!/usr/bin/env bash
# Aliases
#========

# I'm a bad typist

alias sl=ls
alias mdkir=mkdir
alias soruce=source
alias souce=source

# Short things are better

alias v=vagrant
alias g=git
alias d=docker

# Short things are better (git)
alias gs='git show --pretty=oneline'
alias gpom='git push origin master'
alias gpod='git push origin development'
alias grom='git reset --hard origin/master'
alias gp='git pull'
alias gpar='git pull --autostash --rebase'

# Env Overload
alias utcdate='TZ=utc date'

# Just fun
alias fucking=sudo

# Stored Regular Expressions

alias reg_mac='echo [0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}'
alias grep_mac='grep -E `reg_mac`'
alias reg_email='echo "[^[:space:]]+@[^[:space:]]+"'
alias reg_ip='echo "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"'

# Reference
alias alphabet='echo a b c d e f g h i j k l m n o p q r s t u v w x y z'
alias unicode='echo ✓ ™  ♪ ♫ ☃ ° Ɵ ∫'
alias numalphabet='alphabet; echo 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6'
alias ascii='man ascii | grep -m 1 -A 63 --color=never Oct'

# Simple but easy
alias ssh300='ssh-add -t 300'
alias sshnull='ssh -o "UserKnownHostsFile=/dev/null" -o "StrictHostKeyChecking=no"'

# Validate things
alias yamlcheck='python -c "import sys, yaml as y; y.safe_load(open(sys.argv[1]))"'
alias jsoncheck='jq "." >/dev/null <'
alias ppv='puppet parser validate'

# Misc
alias urlencode='python -c "import sys, urllib as ul; print ul.quote_plus(sys.argv[1])"'
alias urlhost='python3 -c "import sys, urllib.parse as up; print(up.urlparse(sys.argv[1]).hostname)"'
alias urlpath='python3 -c "import sys, urllib.parse as up; print(up.urlparse(sys.argv[1]).path)"'
alias bsc='git add .; git commit -a -m "Bull Shit Commit"; git push origin master'
alias stripcolors='sed -E "s/[[:cntrl:]]\[[0-9]{1,3}m//g"'

# OSX stuff
if [ "$OSTYPE" = "darwin" ]; then
  if ! $(command -v md5suml) ; then
    mkdir -p ~/bin
    if [ ! -f  ~/bin/md5sum ]; then
        cat <<EOF > ~/bin/md5sum
md5 -r "${@}"
EOF
    fi
    chmod +x ~/bin/md5sum
  fi
fi

if command -v git > /dev/null; then
    git config --global alias.unstage 'reset --'
    git config --global alias.diff-cached 'diff --cached'
    git config --global alias.ws 'rebase --whitespace=fix'
    git config --global alias.top 'rev-parse --show-toplevel'
fi

# Functions
#==========

# Get to the top of a git tree
cdp () {

  TEMP_PWD=`pwd`
  while ! [ -d .git ]; do
  cd ..
  done
  OLDPWD=$TEMP_PWD

}

cdtop() {
    local top=$(git rev-parse --show-toplevel) &&  cd $top
}


# Interact with gerrit
gerrit () {

    if [ $1 = "wip" ]; then
        commit_sha=`git rev-parse HEAD`
        if [ -z $commit_sha ]; then
            echo "Not in git directory?"
            return 1
        fi
        gerrit review $commit_sha --workflow -1
        return $?
    fi
    username=`git config gitreview.username`

    ssh -o VisualHostKey=no -p 29418 $username@review.openstack.org gerrit $*
}
# export -f gerrit

# Check out a Pull request from github
function pr() {
  id=$1
  if [ -z $id ]; then
      echo "Need Pull request number as argument"
      return 1
  fi
  git fetch origin pull/${id}/head:pr_${id}
  git checkout pr_${id}
}


# I used to run this every now and then, now I don't have to think
function cleanfloat() {
    for ip in `nova floating-ip-list | awk '/ - / {print $4}'`
        do echo $ip
        nova floating-ip-delete $ip
    done
}

# Connect to windows for fun
gobook() {
    ssh -N -f -L 3389:localhost:3389 telescope.fqdn
    rdesktop -K -u nibz -p $WINDOWS_PASSWORD -g 95% localhost
}


# Have vim inspect command history
vim () {
    last_command=$(history | tail -n 2 | head -n 1)
    if [[ $last_command =~ 'git grep' ]] && [[ "$*" =~ :[0-9]+:$ ]]; then
        line_number=$(echo $* | awk -F: '{print $(NF-1)}')
        /usr/bin/vim +${line_number} ${*%:${line_number}:}
    else
        /usr/bin/vim "$@"
    fi
}

# maybe this can be used like 'bc' ?
pcp () {
    python -c "print($@)"
}

# Eject after burning
wodim () {
    /usr/bin/wodim -v $1
    eject -T
}

shrink_audio () {
 
    if [ -z "${1}" ] || [ -z "${2}" ]; then
        in=in.mp3
        if [ -z "${1}" ]; then
            in=in.mp3
        fi
        if [ -z "${2}" ]; then
            out=out.mp3
        fi
        echo "Useage:"
        echo "ffmpeg -i ${in} -map 0:a:0 -b:a 96k ${out}"
    else
        ffmpeg -i "${1}" -map 0:a:0 -b:a 96k "${2}"
    fi
}
# export -f shrink_audio

lsd_compare () {
    # option 1 (time real	0m0.005s)
    DIR=${PWD}
    find ${DIR} -type d -maxdepth 1 | grep -v "^${DIR}$"
    # option 2 (time real	0m0.006s)
    ls -pAL ${DIR} | grep "/"
    # option 3 (time real	0m0.007s)
    ls -dA */ .*/ | grep -v -E "^[.]+/$"
}
lsd () {
    DIR=${PWD}
    find ${DIR} -type d -maxdepth 1 | grep -v "^${DIR}$"
}
# export -f lsd

dirmd5() {
    DIR=$1
    if [ -z "${DIR}" ];then
        DIR=${PWD}
    fi
    find $DIR -type f -exec md5sum {} \; | sort -k 2 | md5sum
}
# export -f dirmd5

fingerprints() {
  local file="${1:-$HOME/.ssh/authorized_keys}"
  while read l; do
    [[ -n $l && ${l###} = $l ]] && ssh-keygen -l -f /dev/stdin <<<$l
  done < "${file}"
}

path() {
    OLDIFS=$IFS
    IFS=':'
    for p in $PATH; do
        echo $p
    done
    IFS=$OLDIFS
}
