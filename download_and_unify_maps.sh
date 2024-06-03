#!/bin/bash

# Define the directory for downloaded maps and the final merged file
WORK_DIR="/home/ctl/graphhopper/maps"
MERGED_FILE="${WORK_DIR}/merged.osm.pbf"
TEMP_MERGED_FILE="${WORK_DIR}/temp_merged.osm.pbf"
LOG_FILE="${WORK_DIR}/merge_log.log"

# Ensure the working directory exists and navigate to it
mkdir -p "${WORK_DIR}"
cd "${WORK_DIR}"

# Log the start of the process
echo "Starting map update process: $(date)" >> "${LOG_FILE}"

# List of regions (use the exact file names)
regions=("andalucia-latest.osm.pbf" "cataluna-latest.osm.pbf" "madrid-latest.osm.pbf" "valencia-latest.osm.pbf")

# Download, verify with MD5, and re-download if necessary
for region in "${regions[@]}"; do
    # Download the .osm.pbf file and its MD5 checksum
    wget -N "http://download.geofabrik.de/europe/spain/${region}"
    wget -N "http://download.geofabrik.de/europe/spain/${region}.md5"

    # Extract the expected MD5 checksum
    expected_checksum=$(cut -d ' ' -f1 < "${region}.md5")

    # Calculate the MD5 checksum of the downloaded .osm.pbf file
    calculated_checksum=$(md5sum "${region}" | cut -d ' ' -f1)

    # Compare the checksums
    if [ "$calculated_checksum" != "$expected_checksum" ]; then
        echo "Checksum verification failed for ${region}. Attempting to redownload." >> "${LOG_FILE}"
        rm -f "${region}"
        wget "http://download.geofabrik.de/europe/spain/${region}"
        
        # Re-calculate checksum after re-downloading
        calculated_checksum=$(md5sum "${region}" | cut -d ' ' -f1)
        
        if [ "$calculated_checksum" != "$expected_checksum" ]; then
            echo "Checksum verification failed again for ${region}. Exiting." >> "${LOG_FILE}"
            exit 1
        else
            echo "Checksum verification passed on second attempt for ${region}." >> "${LOG_FILE}"
        fi
    else
        echo "Checksum verification passed for ${region}." >> "${LOG_FILE}"
    fi
done

# Create a backup before overwriting
if [ -f "${MERGED_FILE}" ]; then
    BACKUP_FILE="${MERGED_FILE}_backup_$(date +%Y%m%d_%H%M%S).pbf"
    cp "${MERGED_FILE}" "${BACKUP_FILE}"
    echo "Backup of the previous merged file created as ${BACKUP_FILE}." >> "${LOG_FILE}"
fi

# Merge the OSM files using Osmium into a temporary file
osmium merge "${regions[@]}" -o "${TEMP_MERGED_FILE}"

# Check if merge was successful
if [ $? -eq 0 ]; then
    mv "${TEMP_MERGED_FILE}" "${MERGED_FILE}"
    echo "Merge successful, updated map file in place." >> "${LOG_FILE}"
else
    echo "Merge failed, previous map file untouched." >> "${LOG_FILE}"
    exit 1
fi

# Restart the GraphHopper service
echo "Restarting GraphHopper service..." >> "${LOG_FILE}"
sudo systemctl restart graphhopper.service
if [ $? -eq 0 ]; then
    echo "GraphHopper service restarted successfully." >> "${LOG_FILE}"

    # Clean up the directory
    echo "Cleaning up downloaded, backup files and MD5 checksum files..." >> "${LOG_FILE}"
    find "${WORK_DIR}" -type f -name '*.osm.pbf' -not -name 'merged.osm.pbf' -delete
    find "${WORK_DIR}" -type f -name '*.md5' -delete
    echo "Cleanup completed successfully." >> "${LOG_FILE}"
else
    echo "Failed to restart GraphHopper service." >> "${LOG_FILE}"
    exit 1
fi
