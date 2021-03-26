# source /software/lsstsw/stack3/loadLSST.bash
WEBDIR=$HOME/public_html/transfer-ingest-monitor
CRONPATH=/home/lsstdbot/SOFTWARE/observing_monitor
REPO=/lsstdata/offline/instrument
REPO_NTS=/lsstdata/offline/teststand
python3 break_locks.py $WEBDIR/auxTel $WEBDIR/NCSA_auxTel $WEBDIR/LSSTCam-bot $WEBDIR/comcam_ccs $WEBDIR/NCSA_comcam $WEBDIR/comcam_archiver
python3 observing_monitor.py --input_dir $REPO_NTS/NCSA_auxTel --output $WEBDIR/NCSA_auxTel --num_days 30
python3 observing_monitor.py --input_dir $REPO/LATISS --output $WEBDIR/auxTel --num_days 30
python3 observing_monitor.py --input_dir $REPO/LATISS --output $WEBDIR/auxTel --gen 3 --num_days 30
python3 observing_monitor.py --input_dir $REPO/LSSTCam-bot --output $WEBDIR/LSSTCam-bot --num_days 30
python3 observing_monitor.py --input_dir $REPO/LSSTComCam-ccs/ --output $WEBDIR/comcam_ccs --num_days 30
python3 observing_monitor.py --input_dir $REPO_NTS/NCSA_comcam/ --output $WEBDIR/NCSA_comcam --num_days 30
python3 observing_monitor.py --input_dir $REPO/LSSTComCam --output $WEBDIR/comcam_archiver --num_days 30
python3 mainpage.py $WEBDIR auxTel BOT comcam_archiver comcam_ccs NCSA_auxTel  NCSA_comcam --num_days 30
