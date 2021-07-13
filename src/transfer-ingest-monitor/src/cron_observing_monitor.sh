# set -e
set -x
# Gather transfer information for each data source being monitored
#

data_sources=("comcam_arc" "auxtel_arc" "nts_auxtel" "nts_comcam" "comcam_ccs" "auxtel_ccs")
for data_source in "${data_sources[@]}"; do
    python3 observing_monitor.py \
        --source_config /etc/config/data_sources.yaml \
        --source_name "${data_source}" \
        --output "$HOME/public_html/$WEB_BASE_PATH/${data_source}" \
        --num_days $MONITOR_NUM_DAYS 
done

# Render the summary webpage
#
python3 render_summary_page.py "$HOME/public_html/$WEB_BASE_PATH" ${data_sources[*]}
