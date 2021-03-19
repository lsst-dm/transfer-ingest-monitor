#! /usr/bin/bash
#source /software/lsstsw/stack3/loadLSST.bash
#Setting number of days that will be probed. We default to 2 to cover overnight transfer

OUTDIR=~/public_html
#OUTDIR=/lsstdata/offline/web_data/processing_monitor
#OUTDIR=/lsstdata/user/staff/web_data/processing_monitor/


#Options
# --last_day 20200501 (or some other 8 character date) will set the last night to be something other than tonight (e.g. to check data 
# from an earlier night)
# --first_day 20200501 (or some other 8 character date) will set the first night to be something other than last night (e.g. to check data 
# from a long time ago)
# If neighter first night nor last night are set, it will just check last night and tonight
# --query_links is set for repos that are not organized by date (necessitating a query). This incluess BOT and comcam.
#OPTIONS=''

#INPUT is the directory 1 level up from the repo
#OUTPUT is where the html and a small db will be written

INPUT=/lsstdata/offline/teststand/auxTel/L1Archiver
OUTPUT=$OUTDIR/auxTel
OPTIONS="--first_day=202102015 --gen 3"

set -x
python3 observing_monitor.py --input_dir $INPUT --output $OUTPUT $OPTIONS

#INPUT=/lsstdata/offline/teststand/comcam/CCS
#OUTPUT=$OUTDIR/comcam_ccs
#OPTIONS="--first_day=20190716"

#INPUT=/lsstdata/offline/teststand/NCSA_auxTel
#OUTPUT=$OUTDIR/NCSA_auxTel
#OPTIONS="--first_day=20200325"

#INPUT=/lsstdata/offline/teststand/BOT 
#OUTPUT=$OUTDIR/BOT 
#OPTIONS="--first_day=20201117"

#INPUT=/lsstdata/offline/teststand/comcam/Archiver
#OUTPUT=$OUTDIR/comcam_archiver
#OPTIONS="--first_day=20190715"

#INPUT=/lsstdata/offline/teststand/NCSA_comcam
#OUTPUT=$OUTDIR/NCSA_comcam
#OPTIONS="--first_day=20200306"
