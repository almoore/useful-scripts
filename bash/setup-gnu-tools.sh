#!/usr/bin/env bash

# Make sure brew is installed
[[ -z "$(command -v brew)" ]] && echo "brew not setup" && exit 1

brew_list=$(brew list)
INSTALL_LIST="
binutils
diffutils
ed
findutils
gawk
gnu-indent
gnu-sed
gnu-tar
gnu-which
gnutls
grep
gzip
screen
watch
wdiff
wget
"

RC="\033[1;31m"
GC="\033[1;32m"
RESET="\033[0m"

print_red() {
    printf "${RC}%s${RESET}\n" "$*"
}

print_green() {
    printf "${GC}%s${RESET}\n" "$*";
}

# ensure the packeges are installed
for pkg in ${INSTALL_LIST}; do
    if ! echo "$brew_list" | grep -q "$pkg"; then
        print_green $pkg
        brew install $pkg
    else
        print_red skipping $pkg
    fi
done

# link them all with default names
GNUBIN_LIST=$(find /usr/local/Cellar -name gnubin)
for gnubin in ${GNUBIN_LIST}; do
    print_green "$gnubin"
    _bin=$(find -L ${gnubin} -type f)
    echo "$_bin"
    for b in $_bin; do
        print_green "Linking $b => /usr/local/bin"
        ln -s $b /usr/local/bin/
    done
done
