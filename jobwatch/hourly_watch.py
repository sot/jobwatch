#!/usr/bin/env python

import os
import argparse
import jobwatch
import time
from datetime import datetime
import pytz
import requests
import tables
from glob import glob

from chandra_time import DateTime

from jobwatch import (FileWatch, JobWatch,
                      make_html_report,
                      set_report_attrs)

SKA = os.environ['SKA']
HOURS = 1 / 24.
FILEDIR = os.path.dirname(__file__)


def get_options():
    parser = argparse.ArgumentParser(description='Hourly status monitor')
    parser.add_argument('--date-now',
                        help='Processing date')
    parser.add_argument('--jobs',
                        default='ska',
                        help='Jobs to watch ("ska" | "mta", default="ska"')
    parser.add_argument('--rootdir',
                        default='.',
                        help='Output root directory')
    parser.add_argument('--email',
                        action='store_true',
                        help='Send email report')
    parser.add_argument('--loud',
                        action='store_true',
                        help='Run loudly')
    args = parser.parse_args()
    return args


# Ska-specific watchers
class SkaURLWatch(JobWatch):
    def __init__(self, task, maxage_hours, url=None,):
        self.type = 'URL'
        self.basename = url
        super(SkaURLWatch, self).__init__(task, url, maxage=maxage_hours * HOURS)

    @property
    def headers(self):
        if not hasattr(self, '_headers'):

            try:
                response = requests.get(self.basename)
            except Exception:
                self._exists = False
                self._headers = None
            else:
                self._exists = response.ok
                self._headers = response.headers
        return self._headers

    @property
    def exists(self):
        if not hasattr(self, '_exists'):
            self._exists = self.headers is not None
        return self._exists

    @property
    def age(self):
        if not hasattr(self, '_age'):
            if self.headers is not None:
                if 'last-modified' in self.headers:
                    time_header = 'last-modified'
                else:
                    time_header = 'date'
                # Parse the time including time zone. Make a new datetime object corresponding
                # to the parsed time, then make a new datetime object for NOW in the same time
                # zone.  Finally subtract the two to get an age.
                tm = time.strptime(self.headers[time_header],
                                   "%a, %d %b %Y %H:%M:%S %Z")
                dtm_url = datetime(tm.tm_year, tm.tm_mon, tm.tm_mday, tm.tm_hour,
                                   tm.tm_min, tm.tm_sec,
                                   tzinfo=pytz.timezone(tm.tm_zone))
                # Current local time;  .astimezone() makes this explicitly tz-aware
                dtm_now_local = datetime.now().astimezone()
                tzinfo_local = dtm_now_local.tzinfo

                # Convert URL time to local (needed for filetime and filedate)
                dtm_url_local = dtm_url.astimezone(tzinfo_local)

                self.filetime = time.mktime(dtm_url_local.timetuple())
                self.filedate = time.ctime(self.filetime)
                self._age = (dtm_now_local - dtm_url_local).total_seconds() / 86400
            else:
                self._age = None
        return self._age

    @property
    def filelines(self):
        return []


class SkaWebWatch(FileWatch):
    def __init__(self, task, maxage_hours, basename,
                 filename=SKA + '/www/ASPECT/{task}/{basename}'):
        self.basename = basename
        super(SkaWebWatch, self).__init__(task, maxage_hours * HOURS, filename)


class SkaFileWatch(FileWatch):
    def __init__(self, task, maxage_hours, basename,
                 filename=SKA + '/data/{task}/{basename}'):
        self.basename = basename
        super(SkaFileWatch, self).__init__(task, maxage_hours * HOURS, filename)


class NonSkaFileWatch(FileWatch):
    def __init__(self, task, maxage_hours, filename):
        self.basename = filename
        super(NonSkaFileWatch, self).__init__(task, maxage_hours * HOURS, filename)


class IfotFileWatch(FileWatch):
    def __init__(self, task, maxage_hours, ifotbasename):
        ifot_root = os.path.join(SKA, 'data', 'arc', 'iFOT_events')
        ifot_files = os.path.join(ifot_root, ifotbasename, "*")
        filename = sorted(glob(ifot_files))[-1]
        self.basename = ifotbasename
        super(IfotFileWatch, self).__init__(task, maxage_hours * HOURS, filename)
        self.type = 'iFOT query'


class H5Watch(JobWatch):
    def __init__(self, task, maxage_hours, filename=None,):
        self.type = 'H5File'
        full_filename = os.path.join(SKA, 'data', task, filename)
        self.basename = os.path.basename(filename)
        super(H5Watch, self).__init__(task, full_filename, maxage=maxage_hours * HOURS)

    @property
    def filelines(self):
        return []

    @property
    def age(self):
        if not hasattr(self, '_age'):
            h5 = tables.open_file(self.filename, mode='r')
            table = h5.root.data
            lasttime = table.col('time')[-1]
            h5.close()
            self.filetime = DateTime(lasttime).unix
            self.filedate = time.ctime(self.filetime)
            self._age = (time.time() - self.filetime) / 86400.0
        return self._age


def main():

    args = get_options()
    jobwatch.LOUD = args.loud

    if args.jobs == 'ska':
        jws = [
            SkaURLWatch('kadi', 1, 'https://kadi.cfa.harvard.edu'),
            SkaFileWatch('kadi', 1, 'cmd_events.csv')
        ]
    elif args.jobs == 'mta':
        jws = [
            SkaURLWatch('arc', 1, 'http://cxc.harvard.edu/mta/ASPECT/arc/index.html'),
            SkaURLWatch('arc', 1, 'http://cxc.harvard.edu/mta/ASPECT/arc/timeline.png'),
            SkaURLWatch('arc', 20, 'http://cxc.harvard.edu/mta/ASPECT/arc/ACE_5min.gif'),
            # SkaURLWatch('arc', 2, 'http://cxc.harvard.edu/mta/ASPECT/arc/GOES_5min.gif'),
            # SkaURLWatch('arc', 2, 'http://cxc.harvard.edu/mta/ASPECT/arc/GOES_xray.gif'),
            # SkaURLWatch('arc', 1, 'http://cxc.harvard.edu/mta/ASPECT/arc/hrc_shield.png'),
            H5Watch('arc', 1, 'ACE.h5'),
            # H5Watch('arc', 1, 'hrc_shield.h5'),
            # H5Watch('arc', 1, 'GOES_X.h5'),
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
            NonSkaFileWatch('mta snapshot', 1, '/data/mta4/www/Snapshot/chandra.snapshot'),
            SkaWebWatch('arc', 1, 'index.html'),
            SkaWebWatch('arc', 1, 'chandra.snapshot'),
            # SkaWebWatch('arc', 1, 'hrc_shield.png'),
            # SkaWebWatch('arc', 2, 'GOES_xray.gif'),
            # SkaWebWatch('arc', 2, 'GOES_5min.gif'),
            SkaWebWatch('arc', 20, 'ACE_5min.gif')
        ]
    else:
        raise ValueError('jobs argument must be either "ska" or "mta"')

    set_report_attrs(jws)
    # Are all the reports OK?
    report_ok = all([j.ok for j in jws])
    errors = [job.basename for job in jws if not job.ok]
    # Set the age strings manually to display in hours
    for jw in jws:
        jw.age_str = '{:.2f}'.format(jw.age / HOURS) if jw.exists else 'None'
    index_html = make_html_report(jws, args.rootdir,
                                  index_template=os.path.join(FILEDIR,
                                                              'hourly_template.html'),
                                  just_status=True)

    if args.jobs == 'ska':
        recipients = ['aca@cfa.harvard.edu']
    elif args.jobs == 'mta':
        recipients = ['aca@cfa.harvard.edu', 'mtadude@cfa.harvard.edu']

    if args.email and not report_ok:
        jobwatch.sendmail(
            recipients, index_html, args.date_now,
            subject="{} {} Week {} errors: {}".format(
                args.jobs.upper(),
                time.strftime("%Y", time.localtime()),
                time.strftime("%W", time.localtime()),
                ", ".join(errors)))


if __name__ == '__main__':
    main()
