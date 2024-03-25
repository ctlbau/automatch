#!/bin/zsh

# Define the directory for downloaded maps and the final merged file
WORK_DIR="/Users/ctl/APIgarden/Graphhopper_prebuilt_jar/maps"
MERGED_FILE="${WORK_DIR}/merged.osm.pbf"

# Ensure the working directory exists
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

# List of regions (use the exact file names)
regions=("andalucia-latest.osm.pbf" "cataluna-latest.osm.pbf" "madrid-latest.osm.pbf" "valencia-latest.osm.pbf")

# Download, verify with MD5, and re-download if necessary
for region in $regions; do
    # Download the .osm.bz2 file and its MD5 checksum
    wget -N "http://download.geofabrik.de/europe/spain/${region}"
    wget -N "http://download.geofabrik.de/europe/spain/${region}.md5"

    # Extract the expected MD5 checksum
    expected_checksum=$(cut -d ' ' -f1 < "${region}.md5")

    # Calculate the MD5 checksum of the downloaded .osm.bz2 file
    calculated_checksum=$(md5 -q "${region}")

    # Compare the checksums
    if [ "$calculated_checksum" != "$expected_checksum" ]; then
        echo "Checksum verification failed for ${region}. Attempting to redownload."
        rm -f "${region}"
        wget "http://download.geofabrik.de/europe/spain/${region}"
        
        # Re-calculate checksum after re-downloading
        calculated_checksum=$(md5 -q "${region}")
        
        if [ "$calculated_checksum" != "$expected_checksum" ]; then
            echo "Checksum verification failed again for ${region}. Exiting."
            exit 1
        else
            echo "Checksum verification passed on second attempt for ${region}."
        fi
    else
        echo "Checksum verification passed for ${region}."
    fi
done

# Merge the OSM files using Osmosis
# osmosis --read-xml file="cataluna-latest.osm.bz2" --read-xml file="madrid-latest.osm.bz2" --merge --read-xml file="valencia-latest.osm.bz2" --merge --read-xml file="andalucia-latest.osm.bz2" --merge --write-xml file="${MERGED_FILE}"
osmium merge andalucia-latest.osm.pbf cataluna-latest.osm.pbf madrid-latest.osm.pbf valencia-latest.osm.pbf -o "${MERGED_FILE}"

