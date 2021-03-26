# Output website files:
WEBDIR=$HOME/public_html/transfer-ingest-monitor
# Data source files:
REPO=/lsstdata/offline/instrument
REPO_NTS=/lsstdata/offline/teststand

# The method for checking if a monitor is running does not work in the Kubernetes environment:
# python3 break_locks.py $WEBDIR/auxTel $WEBDIR/NCSA_auxTel $WEBDIR/LSSTCam-bot $WEBDIR/comcam_ccs $WEBDIR/NCSA_comcam $WEBDIR/comcam_archiver

# Gather transfer information for each data source being monitored
python3 observing_monitor.py --input_dir $REPO_NTS/NCSA_auxTel --output $WEBDIR/NCSA_auxTel --num_days $MONITOR_NUM_DAYS
python3 observing_monitor.py --input_dir $REPO/LATISS --output $WEBDIR/auxTel --num_days $MONITOR_NUM_DAYS
python3 observing_monitor.py --input_dir $REPO/LATISS --output $WEBDIR/auxTel --num_days $MONITOR_NUM_DAYS --gen 3 
python3 observing_monitor.py --input_dir $REPO/LSSTCam-bot --output $WEBDIR/LSSTCam-bot --num_days $MONITOR_NUM_DAYS
python3 observing_monitor.py --input_dir $REPO/LSSTComCam-ccs/ --output $WEBDIR/comcam_ccs --num_days $MONITOR_NUM_DAYS
python3 observing_monitor.py --input_dir $REPO_NTS/NCSA_comcam/ --output $WEBDIR/NCSA_comcam --num_days $MONITOR_NUM_DAYS
python3 observing_monitor.py --input_dir $REPO/LSSTComCam --output $WEBDIR/comcam_archiver --num_days $MONITOR_NUM_DAYS
# Render summary page
python3 mainpage.py $WEBDIR \
    auxTel \
    comcam_archiver \
    comcam_ccs \
    NCSA_auxTel \
    NCSA_comcam \
    BOT
