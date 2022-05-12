#!/usr/bin/env bash
original_image="${1:?Need input image}"
new_image="${2:?Need output image}"
text="${3:-Copyright}"

set -x

convert -background transparent \
        -fill red \
        -rotate 30 \
        -font Helvetica \
        -size 300x80 \
        -pointsize 24 \
        -gravity southeast \
        label:"${text}" \
        miff:- | \
    composite -tile - "$original_image" "$new_image"
