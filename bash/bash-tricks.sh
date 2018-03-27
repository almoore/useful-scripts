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
export shrink_audio
