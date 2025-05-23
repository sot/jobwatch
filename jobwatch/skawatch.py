#!/usr/bin/env python

import argparse
from glob import glob
import astropy.units as u
import time

from cxotime import CxoTime
from kadi import events
import kadi.commands

import jobwatch
from jobwatch import (FileWatch, JobWatch, DbWatch,
                      make_html_report, copy_errs,
                      set_report_attrs)


def get_options():
    parser = argparse.ArgumentParser(description='Ska processing monitor')
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
                        help='Run loudly')
    parser.add_argument('--max-age',
                        type=int,
                        default=30,
                        help='Maximum age of watch reports in days')
    args = parser.parse_args()
    return args


# Ska-specific watchers
class SkaWebWatch(FileWatch):
    def __init__(self, task, maxage, basename,
                 filename='/proj/sot/ska/www/ASPECT/{task}/{basename}'):
        self.basename = basename
        super(SkaWebWatch, self).__init__(task, maxage, filename)


class SkaJobWatch(JobWatch):
    def __init__(self, task, maxage=1, errors=jobwatch.ERRORS, requires=(),
                 logdir='logs', logtask=None,
                 exclude_errors=(),
                 filename=('/proj/sot/ska/data/{task}/'
                           '{logdir}/daily.0/{logtask}.log')):
        self.type = 'Log'
        self.task = task
        self.logtask = logtask or task
        self.logdir = logdir
        super(SkaJobWatch, self).__init__(task, filename, errors=errors,
                                          requires=requires,
                                          exclude_errors=exclude_errors,
                                          maxage=maxage)


class KadiWatch(JobWatch):
    def __init__(self, task, filename, maxage=1):
        self.type = 'Application Data'
        super().__init__(task, filename, maxage=maxage)

    @property
    def filelines(self):
        return []

    @property
    def age(self):
        if not hasattr(self, '_age'):
            last_dwell = events.dwells.all().last()
            self.filetime = CxoTime(last_dwell.stop).unix
            self.filedate = time.ctime(self.filetime)
            self._age = (CxoTime.now() - CxoTime(last_dwell.stop)).to_value(u.day)
        return self._age


class KadiCmdsWatch(JobWatch):
    def __init__(self, task, filename, maxage=1):
        self.type = 'Application Data'
        super().__init__(task, filename, maxage=maxage)

    @property
    def filelines(self):
        return []

    @property
    def age(self):
        if not hasattr(self, '_age'):
            cmds = kadi.commands.get_cmds(start=CxoTime.now() - 7 * u.day, scenario="flight")
            last_cmd = cmds[-1]
            self.filetime = CxoTime(last_cmd['date']).unix
            self.filedate = time.ctime(self.filetime)
            self._age = (CxoTime.now() - CxoTime(last_cmd['date'])).to_value(u.day)
        return self._age


class SkaSqliteDbWatch(DbWatch):
    def __init__(self, task, maxage=1, dbfile=None, table=None, timekey='tstart'):
        super(SkaSqliteDbWatch, self).__init__(
            task, maxage=maxage, table=table, timekey=timekey,
            query='SELECT MAX({timekey}) AS maxtime FROM {table}',
            dbi='sqlite', server=dbfile)


# Customized errors and paths
py_errs = set(('error', 'warn', 'fail', 'fatal', 'exception', 'traceback'))
perl_errs = set(('uninitialized value',
                 '(?<!Program caused arithmetic )error',
                 'warn', 'fatal', 'fail', 'undefined value'))
arc_exclude_errors = [
    r'warning:\s+\d+\s',
    'file contains 0 lines that start with AVERAGE',
    'WARNING: AstropyDeprecationWarning: "Reader" was deprecated',
    "Warning: failed to open URL ftp://ftp.swpc.noaa.gov/pub/lists/ace/ace_epam_5m.txt"]
nmass_errs = copy_errs(py_errs, ('warn', 'fail'),
                       ('warn(?!ing: imaging routines will not be available)',
                        'fail(?!ed to import sherpa)'))
trace_plus_errs = copy_errs(py_errs.union(perl_errs), ['traceback'],
                            ["traceback(?!': True)"])
telem_archive_errs = copy_errs(py_errs, ['fail'],
                               ['(?<!...)fail(?!...)'])
perigee_errs = copy_errs(py_errs, ['warn'],
                         ['warn(?!ing: limit exceeded, dac of)'])
astromon_errs = ('error', 'fatal', 'fail')
engarchive_errs = copy_errs(py_errs, ['fail'],
                            ['(?<!5OHW)FAIL(?!MODE)'])
perigee_errs = copy_errs(py_errs, ['warn'],
                         ['warning(?!: Limit Exceeded. dac of)'])
att_mon_errs = copy_errs(py_errs, ['error'],
                         [r'(?<!\_)error'])
jean_db = '/proj/sot/ska/data/database/Logs/daily.0/{task}.log'
star_stat = '/proj/sot/ska/data/star_stat_db/Logs/daily.0/{task}.log'

last_cheru_log = sorted(glob("/home/kadi/occ_ska_sync_logs/cheru/*.log"))[-1]


def main():

    args = get_options()
    jobwatch.LOUD = args.loud

    jws = []
    jws.extend([
        SkaJobWatch('aca_hi_bgd_mon', 2, errors=py_errs,
                    filename='/proj/sot/ska/data/aca_hi_bgd_mon/logs/daily.0/aca_hi_bgd.log'),
        SkaJobWatch('acdc', 2, errors=py_errs),
        SkaJobWatch('aimpoint_mon3', 2, errors=py_errs),
        SkaJobWatch('arc', 2, errors=perl_errs,
                    exclude_errors=arc_exclude_errors, logdir='Logs'),
        SkaJobWatch('astromon', 8, errors=astromon_errs),
        SkaJobWatch('attitude_error_mon', 2, errors=att_mon_errs),
        SkaJobWatch('aca_weekly_report', 3, errors=py_errs,
                    filename='/proj/sot/ska/data/aca_weekly_report/logs/aca_weekly_report.log'),
        SkaJobWatch("centroid_dashboard", 1, errors=py_errs,
                    filename=("/proj/sot/ska/data/ska_trend/centroid_dashboard/"
                              "logs/daily.0/centroid_dashboard.log")),
        SkaJobWatch('dsn_summary', 2, errors=perl_errs,
                    logtask='dsn_summary_master'),
        SkaJobWatch('eng_archive', 2, errors=engarchive_errs,
                    requires=('Checking dp_pcad32 content',)),
        SkaJobWatch('fid_drift_mon3', 2, errors=py_errs,
                    filename='/proj/sot/ska/data/fid_drift_mon3/logs/daily.0/fid_drift_mon.log'),

        SkaJobWatch('kadi', 1, logtask='kadi_events', errors=py_errs,
                    exclude_errors=['InsecureRequestWarning',
                                    'MajorEvent 2022:097',
                                    'MajorEvent 2022:115',
                                    'MajorEvent 2022:190',
                                    'MajorEvent 2023:047',
                                    'MajorEvent 2023:211',
                                    'MajorEvent 2024:117']),
        SkaJobWatch('kadi', 1, logtask='kadi_cmds', errors=py_errs),
        SkaJobWatch('kadi', 1.5, logtask='kadi_validate', errors=py_errs),
        SkaJobWatch('kalman_watch3', 1, logtask='kalman_watch', errors=py_errs),
        SkaJobWatch('star_stats', 2, filename=star_stat,
                    exclude_errors=['Cannot determine guide transition time']),
        SkaJobWatch('mica', 2, errors=trace_plus_errs,
                    filename='/proj/sot/ska/data/mica/logs/daily.0/mica_archive.log',
                    exclude_errors=["Running get_observed_att_errors",
                                    "HTTP Error 504: Gateway Time-out",
                                    "previous processing error"]),
        SkaJobWatch('acis_taco', 8, filename='/proj/sot/ska/data/acis_taco/logs/daily.0/taco.log'),
        SkaJobWatch('acq_database', 2, filename=jean_db),
        SkaJobWatch('guide_database', 2, filename=jean_db),
        SkaJobWatch('guide_stat_db', 2, filename=jean_db),
        SkaJobWatch('load_database', 2, filename=jean_db),
        SkaJobWatch('obsid_load_database', 2, filename=jean_db),
        SkaJobWatch('occ ska sync cheru', 1,
                    filename=last_cheru_log,
                    requires='total size is',
                    exclude_errors=['Welcome! Warning',
                                    '5OHWFAIL.h5']),
        SkaJobWatch('star_database', 2, filename=jean_db),
        SkaJobWatch('starcheck_database', 2, filename=jean_db),
        SkaJobWatch('vv_database', 2, filename=jean_db),
        SkaJobWatch('telem_archive', 2, errors=telem_archive_errs,
                    exclude_errors=['WARNING - no kalman interval for obsid 4']),
        SkaJobWatch('perigee_health_plots', 2, logdir='Logs',
                    errors=perigee_errs),
        SkaJobWatch(
            'skare3 testing', 3,
            filename='/proj/sot/ska/data/skare3/skare3_data/data/test_logs/ska3-masters/test.log'),
        SkaJobWatch('vv_trend', 10, errors=py_errs),
    ])

    jws.extend([
        SkaWebWatch('acq_stat_reports', 10, 'index.html'),
        SkaWebWatch('aca_weekly_report', 3, 'index.html'),
        SkaWebWatch('aimpoint_mon3', 1, 'index.html'),
        SkaWebWatch('attitude_error_mon', 2, 'one_shot_vs_angle.png'),
        FileWatch('attitude_error_mon', 2, '/proj/sot/ska/data/attitude_error_mon/data.dat'),
        SkaWebWatch('arc', 1, 'index.html'),
        SkaWebWatch('arc', 1, 'chandra.snapshot'),
        SkaWebWatch('arc', 1, 'timeline.png'),
        SkaWebWatch('arc', 1, 'hrc_shield.png'),
        SkaWebWatch('arc', 2, 'GOES_5min.gif'),
        SkaWebWatch('arc', 24, 'solar_wind.png'),
        SkaWebWatch('arc', 24, 'solar_flare_monitor.png'),
        SkaWebWatch('arc', 2, 'ACE_5min.gif'),
        SkaWebWatch('celmon', 30, 'offsets-ACIS-S-history.png'),
        FileWatch('dsn_summary', 1,
                  '/proj/sot/ska/data/dsn_summary/dsn_summary.dat'),
        FileWatch('dsn_summary', 1,
                  '/data/mta4/proj/rac/ops/ephem/dsn_summary.dat'),
        SkaWebWatch('gui_stat_reports', 10, 'index.html'),
        SkaWebWatch('fid_drift_mon3', 2, 'drift_acis_s.png'),
        SkaWebWatch('eng_archive', 2, '',
                    filename='/proj/sot/ska/data/eng_archive/data/dp_pcad32/TIME.h5'),
        FileWatch('kadi3', 1, filename='/proj/sot/ska/data/kadi/events3.db3'),
        FileWatch('mica l0', 2, filename='/proj/sot/ska/data/mica/archive/aca0/archfiles.db3'),
        FileWatch('mica l1', 2, filename='/proj/sot/ska/data/mica/archive/asp1/archfiles.db3'),
        FileWatch('mica vv', 2, filename='/proj/sot/ska/data/mica/archive/vv/vv.h5'),
        FileWatch('mica starcheck', 21,
                  filename='/proj/sot/ska/data/mica/archive/starcheck/starcheck.db3'),
        SkaWebWatch('obc_rate_noise', 50, 'trending/pitch_hist_recent.png'),
        SkaWebWatch('perigee_health_plots', 5, 'index.html'),
        SkaWebWatch('kalman_watch3', 2, 'mon_win_kalman_drops_-45d_-1d.html'),
        SkaWebWatch('kalman_watch3', 2, 'index.html'),
        FileWatch('skare3 dashboard', 2,
                  filename='/proj/sot/ska/www/ASPECT/skare3/dashboard/packages.json'),
        SkaWebWatch('vv_rms', 10, 'hist2d_fig.png'),

    ])

    jws.extend([
        SkaSqliteDbWatch('starcheck_obs', -1, timekey='mp_starcat_time',
                         dbfile='/proj/sot/ska/data/mica/archive/starcheck/starcheck.db3'),
    ])

    jws.extend([KadiWatch('kadi dwells', '/proj/sot/ska/data/kadi/events3.db3', maxage=3)])

    # Commands should go out into the future unless we're in an anomaly state
    jws.extend([KadiCmdsWatch('kadi cmds', '/proj/sot/ska/data/kadi/cmds2.h5', maxage=-1)])

    set_report_attrs(jws)
    index_html = make_html_report(jws, args.rootdir, args.date_now)
    recipients = ['aca@head.cfa.harvard.edu']

    if args.email:
        jobwatch.sendmail(recipients, index_html, args.date_now)

    jobwatch.remove_old_reports(args.rootdir, args.date_now, args.max_age)
