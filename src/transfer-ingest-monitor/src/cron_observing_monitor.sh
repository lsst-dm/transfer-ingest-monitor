source /software/lsstsw/stack3/loadLSST.bash
WEBDIR=/lsstdata/offline/web_data/processing_monitor
CRONPATH=/home/lsstdbot/SOFTWARE/observing_monitor
REPO=/lsstdata/offline/teststand
$CRONPATH/break_locks.py $WEBDIR/auxTel $WEBDIR/NCSA_auxTel $WEBDIR/BOT $WEBDIR/comcam_ccs $WEBDIR/NCSA_comcam $WEBDIR/comcam_archiver
$CRONPATH/observing_monitor.py --input_dir $REPO/auxTel/L1Archiver --output $WEBDIR/auxTel
$CRONPATH/observing_monitor.py --input_dir $REPO/auxTel/L1Archiver --output $WEBDIR/auxTel --gen 3
$CRONPATH/observing_monitor.py --input_dir $REPO/NCSA_auxTel --output $WEBDIR/NCSA_auxTel
$CRONPATH/observing_monitor.py --input_dir $REPO/BOT --output $WEBDIR/BOT --num_days 3
$CRONPATH/observing_monitor.py --input_dir $REPO/comcam/CCS/ --output $WEBDIR/comcam_ccs
$CRONPATH/observing_monitor.py --input_dir $REPO/NCSA_comcam/ --output $WEBDIR/NCSA_comcam
$CRONPATH/observing_monitor.py --input_dir $REPO/comcam/Archiver --output $WEBDIR/comcam_archiver
$CRONPATH/mainpage.py $WEBDIR auxTel BOT comcam_archiver comcam_ccs NCSA_auxTel  NCSA_comcam
