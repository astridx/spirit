#!/bin/sh
set -e


TTFDIR="./ttf"
PBFDIR="./pbf"

mkdir -p "${TTFDIR}"
mkdir -p "${PBFDIR}"

# See https://github.com/gravitystorm/openstreetmap-carto/blob/master/scripts/get-fonts.sh
download() {
  curl --fail --compressed -A "get-fonts.sh/osm-carto" -o "$1" -z "$1" -L "$2" || { echo "Failed to download $1 $2"; rm -f "$1"; exit 1; }
}

REGULAR_BOLD="NotoSans"

for font in $REGULAR_BOLD; do
  regular="$font-Regular.ttf"
  bold="$font-Bold.ttf"
  italic="$font-Italic.ttf"
  download "${TTFDIR}/${regular}" "https://github.com/notofonts/noto-fonts/raw/main/hinted/ttf/${font}/${regular}"
  download "${TTFDIR}/${bold}" "https://github.com/notofonts/noto-fonts/raw/main/hinted/ttf/${font}/${bold}"
done


for input_file in ${TTFDIR}/*.ttf; do
    
    base_name=$(basename "$input_file" .ttf)
    
    output_dir="${PBFDIR}/$base_name"



    if [ -d "$output_dir" ]; then
        echo "Hinweis: Das Verzeichnis $output_dir existiert bereits. Überspringe Erstellung."
    else
        mkdir "$output_dir"
        if [ $? -ne 0 ]; then
            echo "Fehler beim Erstellen des Verzeichnisses $output_dir"
            exit 1
        fi
    fi    

    npx -p fontnik build-glyphs "$input_file" "$output_dir"
done