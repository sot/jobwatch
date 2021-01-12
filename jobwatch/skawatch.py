#!/usr/bin/env python

import argparse
import jobwatch
from glob import glob
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


class SkaDbWatch(DbWatch):
    def __init__(self, task, maxage=1, table=None, timekey='tstart'):
        super(SkaDbWatch, self).__init__(
            task, maxage=maxage, table=table, timekey=timekey,
            query='SELECT MAX({timekey}) AS maxtime FROM {table}',
            dbi='sybase', server='sybase', user='aca_read', database='aca')


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
arc_exclude_errors = [r'warning:\s+\d+\s',
                      'file contains 0 lines that start with AVERAGE']
nmass_errs = copy_errs(py_errs, ('warn', 'fail'),
                       ('warn(?!ing: imaging routines will not be available)',
                        'fail(?!ed to import sherpa)'))
trace_plus_errs = copy_errs(py_errs.union(perl_errs), ['traceback'],
                            ["traceback(?!': True)"])
telem_archive_errs = copy_errs(py_errs, ['fail'],
                               ['(?<!...)fail(?!...)'])
perigee_errs = copy_errs(py_errs, ['warn'],
                         ['warn(?!ing: limit exceeded, dac of)'])
astromon_errs = ('uninitialized value', 'warn', 'fatal', 'fail',
                 'undefined value',
                 'ERROR(?!: Data::ParseTable: FITS ' +
                 'files cannot be passed as arrays)')
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
        SkaJobWatch('aimpoint_mon', 2, errors=py_errs),
        SkaJobWatch('arc', 2, errors=perl_errs,
                    exclude_errors=arc_exclude_errors, logdir='Logs'),
        SkaJobWatch('astromon', 8, errors=astromon_errs),
        SkaJobWatch('attitude_error_mon', 2, errors=att_mon_errs),
        SkaJobWatch('dsn_summary', 2, errors=perl_errs,
                    logtask='dsn_summary_master'),
        SkaJobWatch('eng_archive', 1, errors=engarchive_errs,
                    requires=('Checking dp_pcad32 content',)),
        SkaJobWatch('fid_drift_mon', 2, errors=py_errs.union(perl_errs)),

        SkaJobWatch('kadi', 1, logtask='kadi_events', errors=py_errs,
                    exclude_errors=['InsecureRequestWarning']),

        SkaJobWatch('kadi', 1, logtask='kadi_cmds', errors=py_errs),
        SkaJobWatch('star_stats', 2, filename=star_stat,
                    exclude_errors=['Cannot determine guide transition time']),
        SkaJobWatch('timelines', 2, logtask='timelines_cmd_states', logdir='Logs'),
        SkaJobWatch('mica', 2, errors=trace_plus_errs),
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
        SkaJobWatch('validate_states', 2, errors=trace_plus_errs),
        SkaJobWatch('scs107', 2, logdir='Logs', logtask='scs107_check'),
        SkaJobWatch('telem_archive', 2, errors=telem_archive_errs),
        SkaJobWatch('perigee_health_plots', 2, logdir='Logs',
                    errors=perigee_errs),
        SkaJobWatch('vv_trend', 10, errors=py_errs),
    ])

    jws.extend([
        SkaWebWatch('acq_stat_reports', 10, 'index.html'),
        SkaWebWatch('aimpoint_mon', 1, 'index.html'),
        SkaWebWatch('aimpoint_mon', 1, 'info.json'),
        SkaWebWatch('attitude_error_mon', 2, 'one_shot_vs_angle.png'),
        FileWatch('attitude_error_mon', 2, '/proj/sot/ska/data/attitude_error_mon/data.dat'),
        SkaWebWatch('arc', 1, 'index.html'),
        SkaWebWatch('arc', 1, 'chandra.snapshot'),
        # SkaWebWatch('arc', 1, 'hrc_shield.png'),
        # SkaWebWatch('arc', 2, 'GOES_xray.gif'),
        # SkaWebWatch('arc', 2, 'GOES_5min.gif'),
        SkaWebWatch('arc', 24, 'solar_wind.gif'),
        SkaWebWatch('arc', 24, 'solar_flare_monitor.png'),
        SkaWebWatch('arc', 2, 'ACE_5min.gif'),
        SkaWebWatch('celmon', 30, 'offsets-ACIS-S-hist.gif'),
        FileWatch('dsn_summary', 1,
                  '/proj/sot/ska/data/dsn_summary/dsn_summary.dat'),
        FileWatch('dsn_summary', 1,
                  '/data/mta4/proj/rac/ops/ephem/dsn_summary.dat'),
        SkaWebWatch('gui_stat_reports', 10, 'index.html'),
        SkaWebWatch('fid_drift', 2, 'drift_acis_s.png'),
        SkaWebWatch('eng_archive', 1, '',
                    filename='/proj/sot/ska/data/eng_archive/data/dp_pcad32/TIME.h5'),
        SkaWebWatch('kadi', 1, '', filename='/proj/sot/ska/data/kadi/events.db3'),
        SkaWebWatch('obc_rate_noise', 50, 'trending/pitch_hist_recent.png'),
        SkaWebWatch('perigee_health_plots', 5, 'index.html'),
        SkaWebWatch('vv_rms', 10, 'hist2d_fig.png'),
    ])

    jws.extend([
        SkaDbWatch('acq_stats_data', 4),
        SkaDbWatch('aiprops', 4),
        SkaDbWatch('cmds', -1, timekey='date'),
        SkaDbWatch('cmd_states', -1, timekey='datestart'),
        SkaDbWatch('load_segments', -1, timekey='datestop'),
        SkaDbWatch('obspar', 4),
        SkaDbWatch('starcheck_obs', 4, timekey='mp_starcat_time'),
        SkaDbWatch('trak_stats_data', 4, timekey='kalman_tstart'),
    ])

    jws.extend([
        SkaSqliteDbWatch('cmds', -1, timekey='date',
                         dbfile='/proj/sot/ska/data/cmd_states/cmd_states.db3'),
        SkaSqliteDbWatch('cmd_states', -1, timekey='datestart',
                         dbfile='/proj/sot/ska/data/cmd_states/cmd_states.db3'),
        SkaSqliteDbWatch('load_segments', -1, timekey='datestop',
                         dbfile='/proj/sot/ska/data/cmd_states/cmd_states.db3'),
        SkaSqliteDbWatch('timeline_loads', -1, timekey='datestop',
                         dbfile='/proj/sot/ska/data/cmd_states/cmd_states.db3'),
    ])

    set_report_attrs(jws)
    index_html = make_html_report(jws, args.rootdir, args.date_now)
    recipients = ['aca@head.cfa.harvard.edu']

    if args.email:
        jobwatch.sendmail(recipients, index_html, args.date_now)

    jobwatch.remove_old_reports(args.rootdir, args.date_now, args.max_age)
