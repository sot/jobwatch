#!/usr/bin/env python

import os
import argparse
import jobwatch
import time
from glob import glob
from jobwatch import (FileWatch, JobWatch,
                      make_html_report, copy_errs,
                      set_report_attrs)

SKA = os.environ['SKA']


# Ska-specific watchers
class SkaWebWatch(FileWatch):
    def __init__(self, task, maxage, basename,
                 filename=SKA + '/www/ASPECT/{task}/{basename}'):
        self.basename = basename
        super(SkaWebWatch, self).__init__(task, maxage, filename)


class SkaFileWatch(FileWatch):
    def __init__(self, task, maxage, basename,
                 filename=SKA + '/data/{task}/{basename}'):
        self.basename = basename
        super(SkaFileWatch, self).__init__(task, maxage, filename)

class IfotFileWatch(FileWatch):
    def __init__(self, task, maxage, ifotbasename):
        ifot_root = os.path.join(SKA, 'data', 'arc', 'iFOT_events')
        ifot_files = os.path.join(ifot_root, ifotbasename, "*")
        filename = sorted(glob(ifot_files))[-1]
        self.basename = ifotbasename
        super(IfotFileWatch, self).__init__(task, maxage, filename)
        self.type = 'iFOT query'

class H5Watch(JobWatch):
    def __init__(self, task, maxage, filename=None,):
        self.type = 'H5File'
        full_filename = os.path.join(SKA, 'data', task, filename)
        self.basename = os.path.basename(filename)
        super(H5Watch, self).__init__(task, full_filename, maxage=maxage)

    @property
    def filelines(self):
        return []

    @property
    def age(self):
        if not hasattr(self, '_age'):
            import tables
            from Chandra.Time import DateTime
            import time
            h5 = tables.openFile(self.filename, mode='r')
            table = h5.root.data
            lasttime = table.col('time')[-1]
            h5.close()
            self.filetime = DateTime(lasttime).unix
            self.filedate = time.ctime(self.filetime)
            self._age = (time.time() - self.filetime) / 3600.
        return self._age


parser = argparse.ArgumentParser(description='Replan Central monitor')
parser.add_argument('--date-now',
                    help='Processing date')
parser.add_argument('--rootdir',
                    default='.',
                    help='Output root directory')
parser.add_argument('--email',
                    action='store_true',
                    help='Send email report')
parser.add_argument('--loud',
                    action='store_true',
                    help='Send email report')
args = parser.parse_args()

jobwatch.LOUD = args.loud


jws = []
jws.extend(
    [
        H5Watch('arc', 1, 'ACE.h5'),
        H5Watch('arc', 1, 'hrc_shield.h5'),
        H5Watch('arc', 1, 'GOES_X.h5'),
        IfotFileWatch('arc', 1, 'comm'),
        IfotFileWatch('arc', 1, 'eclipse'),
        IfotFileWatch('arc', 1, 'grating'),
        IfotFileWatch('arc', 1, 'grating'),
        IfotFileWatch('arc', 1, 'load_segment'),
        IfotFileWatch('arc', 1, 'maneuver'),
        IfotFileWatch('arc', 1, 'momentum_mon'),
        IfotFileWatch('arc', 1, 'or_er'),
        IfotFileWatch('arc', 1, 'radmon'),
        IfotFileWatch('arc', 1, 'safe'),
        IfotFileWatch('arc', 1, 'sim'),
        IfotFileWatch('arc', 1, 'sun_pos_mon'),
        SkaFileWatch('arc', 1, 'ace.html'),
        SkaWebWatch('arc', 1, 'index.html'),
        SkaWebWatch('arc', 1, 'chandra.snapshot'),
        SkaWebWatch('arc', 1, 'hrc_shield.png'),
        SkaWebWatch('arc', 1, 'GOES_xray.gif'),
        SkaWebWatch('arc', 1, 'GOES_5min.gif'),
        SkaWebWatch('arc', 8, 'solar_wind.gif'),
        SkaWebWatch('arc', 1, 'solar_flare_monitor.png'),
        SkaWebWatch('arc', 1, 'ACE_5min.gif')])

set_report_attrs(jws)
# Are all the reports OK?
report_ok = all([j.ok for j in jws])
index_html = make_html_report(jws, args.rootdir,
                              index_template='hourly_template.html',
                              just_status=True
                              )
recipients = ['aca@head.cfa.harvard.edu']

if args.email and not report_ok:
    jobwatch.sendmail(
        recipients, index_html, args.date_now,
        subject="Replan Central Status: {}".format(
            time.strftime("%F %T", time.localtime())))

