# A simple way to see if the current file is being sorced
# This seems to be portable between Bash and Korn
[[ $_ != $0 ]] && echo "Script is being sourced" || echo "Script is a subshell"
