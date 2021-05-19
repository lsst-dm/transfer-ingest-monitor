# Output website files:
WEBDIR=$HOME/public_html/$WEB_BASE_PATH
# Data source files:
REPO=/lsstdata/offline/instrument
REPO_NTS=/lsstdata/offline/teststand

# The method for checking if a monitor is running does not work in the Kubernetes environment:
# python3 break_locks.py $WEBDIR/auxTel $WEBDIR/NCSA_auxTel $WEBDIR/LSSTCam-bot $WEBDIR/comcam_ccs $WEBDIR/NCSA_comcam $WEBDIR/comcam_archiver

# Gather transfer information for each data source being monitored
#
for gen in "--gen 3" "--gen 2"; do
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name auxtel_ccs --output $WEBDIR/auxtel --num_days $MONITOR_NUM_DAYS $gen 
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name auxtel_arc --output $WEBDIR/auxtel_archiver --num_days $MONITOR_NUM_DAYS $gen
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name nts_auxtel --output $WEBDIR/nts_auxtel --num_days $MONITOR_NUM_DAYS $gen 
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name comcam_ccs --output $WEBDIR/comcam --num_days $MONITOR_NUM_DAYS $gen
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name comcam_arc --output $WEBDIR/comcam_archiver --num_days $MONITOR_NUM_DAYS $gen
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name nts_comcam --output $WEBDIR/nts_comcam --num_days $MONITOR_NUM_DAYS $gen
    python3 observing_monitor.py --source_config /etc/config/data_sources.yaml --source_name bot --output $WEBDIR/bot --num_days $MONITOR_NUM_DAYS $gen
done

# Render the webpage
#
python3 mainpage.py $WEBDIR \
    auxtel \
    auxtel_archiver \
    nts_auxtel \
    comcam \
    comcam_archiver \
    nts_comcam \
    bot
