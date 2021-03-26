# observing_monitor
Prototype code that monitors the images being transferred via rsync
and ingested into Gen2 Butler repositories.

* Determines what files have been transferred
* Determines what files have been ingested
* Cross-matches the two list
* Makes webpage with observing night, file counts, most recent ingest/transfer time
* Makes webpage with all files in a night so observer can determine which files were not ingested
* Typically finishes in night of data in a few seconds and can be used on frequent CRON jobs

## Requires
* Python3
* configargparse
* sqlite3
* Read access to rsync'd files, Gen2 repo

## Examples

Multiples examples listed in `observing_monitor_test.sh`
```
OPTIONS=''
INPUT=/lsstdata/offline/instrument/LATISS
OUTPUT=/home/emorgan2/public_html/auxTel
python observing_monitor.py --input_dir $INPUT --output $OUTPUT $OPTIONS
```
`INPUT` is the directory with a gen2repo and file store.

`OUTPUT` is where HTML will be written

By default, program will check new files for the last two days. It is generally useful to do at least 2 days to avoid midnight problems

If you wanted to track many pages at once, set `NDAY=400` or some other number large enough to capture all relevant data.

If you want to check data from older nights, you could use the `--last_day 20200501` (for May 1, 2020). Processing will then count backwards from `last_day` instead of the current day. 

If you want to check many nights, you probably want to set `--last_day` and `--first_day`

If the files in your gen2repo are not organized by date (e.g. BOT and comCam), you need to use the `--query_links` OPTION. This option should never cause problems, but does slow the process down a bit.

## Notes
If you repo has been remade you may need to remake you monitoring page with a command like:
```
rm $OUTPUT 
python observing_monitor.py --input_dir $INPUT --output $OUTPUT --num_days 400
```
This would then remake the last 400 nights of data.

This repo also contains `cron_observing_monitor.sh` ,  the script we use to check 6 separate repos. 
