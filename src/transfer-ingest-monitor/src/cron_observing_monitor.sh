# Output website files:
WEBDIR=$HOME/public_html/$WEB_BASE_PATH

# Gather transfer information for each data source being monitored
#
for gen in "--gen 3" "--gen 2"; do
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name auxtel_ccs --output $WEBDIR/auxtel_ccs --num_days $MONITOR_NUM_DAYS $gen # --first_day=20210501 --last_day=20210515
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name auxtel_arc --output $WEBDIR/auxtel_arc --num_days $MONITOR_NUM_DAYS $gen # --first_day=20210501 --last_day=20210515
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name comcam_ccs --output $WEBDIR/comcam_ccs --num_days $MONITOR_NUM_DAYS $gen # --first_day=20210501 --last_day=20210515
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name comcam_arc --output $WEBDIR/comcam_arc --num_days $MONITOR_NUM_DAYS $gen # --first_day=20210501 --last_day=20210515
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name nts_auxtel --output $WEBDIR/nts_auxtel --num_days $MONITOR_NUM_DAYS $gen # --first_day=20210501 --last_day=20210515
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name nts_comcam --output $WEBDIR/nts_comcam --num_days $MONITOR_NUM_DAYS $gen # --first_day=20210501 --last_day=20210515
    # python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name bot --output $WEBDIR/bot --num_days $MONITOR_NUM_DAYS $gen
done

# Render the webpage
#
python3 mainpage.py $WEBDIR \
    auxtel_ccs \
    auxtel_arc \
    comcam_ccs \
    comcam_arc \
    nts_auxtel \
    nts_comcam 
    # bot
