# source /software/lsstsw/stack3/loadLSST.bash
WEBDIR=$HOME/public_html/transfer-ingest-monitor
CRONPATH=/home/lsstdbot/SOFTWARE/observing_monitor
REPO=/lsstdata/offline/teststand
python3 break_locks.py $WEBDIR/auxTel $WEBDIR/NCSA_auxTel $WEBDIR/BOT $WEBDIR/comcam_ccs $WEBDIR/NCSA_comcam $WEBDIR/comcam_archiver
python3 observing_monitor.py --input_dir $REPO/auxTel/L1Archiver --output $WEBDIR/auxTel
python3 observing_monitor.py --input_dir $REPO/auxTel/L1Archiver --output $WEBDIR/auxTel --gen 3
python3 observing_monitor.py --input_dir $REPO/NCSA_auxTel --output $WEBDIR/NCSA_auxTel
python3 observing_monitor.py --input_dir $REPO/BOT --output $WEBDIR/BOT --num_days 3
python3 observing_monitor.py --input_dir $REPO/comcam/CCS/ --output $WEBDIR/comcam_ccs
python3 observing_monitor.py --input_dir $REPO/NCSA_comcam/ --output $WEBDIR/NCSA_comcam
python3 observing_monitor.py --input_dir $REPO/comcam/Archiver --output $WEBDIR/comcam_archiver
python3 mainpage.py $WEBDIR auxTel BOT comcam_archiver comcam_ccs NCSA_auxTel  NCSA_comcam
