#!/usr/bin/env python

import os
import argparse
import jobwatch
import time
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

