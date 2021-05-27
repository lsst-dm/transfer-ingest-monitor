# Gather transfer information for each data source being monitored
#

# data_sources=("auxtel_ccs" "auxtel_arc" "comcam_ccs" "comcam_arc" "nts_auxtel" "nts_comcam" "bot")
data_sources=("auxtel_ccs" "auxtel_arc" "comcam_ccs" "comcam_arc" "nts_auxtel" "nts_comcam")
for gen in "2" "3"; do
    for data_source in "${data_sources[@]}"; do
        python3 observing_monitor.py \
            --source_config /etc/config/data_sources.yaml \
            --source_name "${data_source}" \
            --output "$HOME/public_html/$WEB_BASE_PATH/${data_source}" \
            --gen $gen \
            --num_days $MONITOR_NUM_DAYS 
            # --first_day=20210501 --last_day=20210515
    done
done

# Render the summary webpage
#
python3 render_summary_page.py $WEBDIR "${data_sources[*]}"
