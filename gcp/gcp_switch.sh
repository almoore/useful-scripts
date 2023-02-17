
#---  FUNCTION  -------------------------------------------------------------------------------------------------------
#          NAME:  gcp-switch
#   DESCRIPTION:  Change between gcp profiles that are locally setup
#----------------------------------------------------------------------------------------------------------------------
gcp-switch() {
    case ${1} in
        "" | clear)
            gcloud config configurations activate default
            ;;
        *)
            gcloud config configurations activate ${1}
            ;;
    esac
}

gcp-profiles () {
    gcloud config configurations list --format text|grep -E "^name"|awk '{print $2}'
}

#--- COMPDEF ------------------------------------------------------------------#
#      FUNCTION: gcp-switch
#   DESCRIPTION: Switch the GCP profile
#------------------------------------------------------------------------------#

_gcp_switch() {
    local -a gcp_profiles
    local curr_arg;
    curr_arg=${COMP_WORDS[COMP_CWORD]}

     _gcp_profiles=$(gcp-profiles)
     COMPREPLY=( $(compgen -W "$_gcp_profiles" -- $curr_arg ) );
}
 
complete -F _gcp_switch gcp-switch
