#! /software/lsstsw/stack_20200515/python/miniconda3-4.7.12/envs/lsst-scipipe/bin/python
import psutil, sys, os
for pid in psutil.pids():
  if "observing_monit" in psutil.Process(pid).name():
     print("Observing monitor running. Not deleting locks.")
     sys.exit()
for num in range(1,len(sys.argv)):
  lock=sys.argv[num]+'/.monitor.lock'
  if os.path.exists(lock):
    print("No instances of observering monitor running. Deleting "+lock)
    os.remove(lock)
