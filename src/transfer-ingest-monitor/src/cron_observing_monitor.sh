set -e
set -x
# Gather transfer information for each data source being monitored
#

# data_sources=("auxtel_ccs" "auxtel_arc" "comcam_ccs" "comcam_arc" "nts_auxtel" "nts_comcam" "bot")
data_sources=("comcam_ccs" "comcam_arc" "auxtel_ccs" "auxtel_arc" "nts_auxtel" "nts_comcam")
# data_sources=("comcam_ccs" "comcam_arc")
for data_source in "${data_sources[@]}"; do
    python3 observing_monitor.py \
        --source_config /etc/config/data_sources.yaml \
        --source_name "${data_source}" \
        --output "$HOME/public_html/$WEB_BASE_PATH/${data_source}" \
        --num_days $MONITOR_NUM_DAYS 
        # --num_days 10
        # --first_day=20210501 --last_day=20210515
        # --gen $gen \
done

# Render the summary webpage
#
python3 render_summary_page.py "$HOME/public_html/$WEB_BASE_PATH" ${data_sources[*]}
