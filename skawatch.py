#!/usr/bin/env python

import os
import argparse
import jobwatch
from jobwatch import (FileWatch, SkaJobWatch, SkaDbWatch,
                      make_html_report, SkaWebWatch, copy_errs,
                      set_report_attrs)
from Chandra.Time import DateTime

parser = argparse.ArgumentParser(description='Ska processing monitor')
parser.add_argument('--date-now',
                    help='Processing date')
parser.add_argument('--rootdir',
                    default='.',
                    help='Output root directory')
parser.add_argument('--email',
                    action='store_true',
                    help='Send email report')
parser.add_argument('--max-age',
                    type=int,
                    default=30,
                    help='Maximum age of watch reports')
args = parser.parse_args()

jws = []
if 0:
    jws.extend([
    SkaDbWatch('acq_stats_data', 4),
    SkaDbWatch('aiprops', 4),
    SkaDbWatch('cmds', -1, timekey='date'),
    SkaDbWatch('cmd_states', -1, timekey='datestart'),
    SkaDbWatch('load_segments', -1, timekey='datestart'),
    SkaDbWatch('obspar', 4),
    SkaDbWatch('starcheck_obs', 4, timekey='mp_starcat_time'),
    SkaDbWatch('trak_stats_data', 4, timekey='kalman_tstart'),
    ])

jws.extend([
    SkaWebWatch('acq_stat_reports', 10, 'index.html'),
    SkaWebWatch('arc', 1, 'index.html'),
    SkaWebWatch('celmon', 30, 'offsets-ACIS-S-hist.gif'),
    FileWatch('dsn_summary', 1,
              '/proj/sot/ska/data/dsn_summary/dsn_summary.dat'),
    SkaWebWatch('gui_stat_reports', 10, 'index.html'),
    SkaWebWatch('fid_drift', 2, 'drift_acis_s.png'),
    SkaWebWatch('obc_rate_noise', 50, 'trending/pitch_hist_recent.png'),
    SkaWebWatch('perigee_health_plots', 5, 'index.html'),
    ])


py_errs = set(jobwatch.ERRORS)
perl_errs = set(('uninitialized value',
                 '(?<!Program caused arithmetic )error',
                 'warn', 'fatal', 'fail', 'undefined value'))
arc_errs = copy_errs(perl_errs, ['warn'], ['warning(?!:\s+\d+\s)'])
nmass_errs = copy_errs(py_errs, ('warn', 'fail'),
                       ('warn(?!ing: imaging routines will not be available)',
                        'fail(?!ed to import sherpa)'))

psmc_errs = copy_errs(py_errs.union(perl_errs), ['traceback'],
                      ["traceback(?!': True)"])
telem_archive_errs = copy_errs(py_errs, ['fail'],
                               ['(?<!...)fail(?!...)'])
perigee_errs = copy_errs(py_errs, ['warn'],
                         ['warn(?!ing: limit exceeded, dac of)'])

jean_db = '/proj/sot/ska/data/database/Logs/daily.0/{task}.log'
star_stat = '/proj/sot/ska/data/star_stat_db/Logs/daily.0/{task}.log'

if 1:
    jws.extend([
    SkaJobWatch('aca_bgd_mon', 40, errors=perl_errs,
                requires=('Copying plots and log file '
                          'to /proj/sot/ska/www/ASPECT',)),
    SkaJobWatch('arc', 2, errors=arc_errs, logdir='Logs'),
    SkaJobWatch('astromon', 8, errors=perl_errs),
    SkaJobWatch('dsn_summary', 2, errors=perl_errs),
    SkaJobWatch('eng_archive', 2),
    SkaJobWatch('fid_drift_mon', 2, errors=py_errs.union(perl_errs)),
    SkaJobWatch('star_stats', 2, filename=star_stat),
    SkaJobWatch('acq_stats', 2, filename=star_stat),
    SkaJobWatch('timelines', 2, logdir='Logs'),
    SkaJobWatch('taco', 8),
    SkaJobWatch('acq_database', 2, filename=jean_db),
    SkaJobWatch('guide_database', 2, filename=jean_db),
    SkaJobWatch('guide_stat_db', 2, filename=jean_db),
    SkaJobWatch('load_database', 2, filename=jean_db),
    SkaJobWatch('obsid_load_database', 2, filename=jean_db),
    SkaJobWatch('star_database', 2, filename=jean_db),
    SkaJobWatch('starcheck_database', 2, filename=jean_db),
    SkaJobWatch('vv_database', 2, filename=jean_db),
    SkaJobWatch('nmass', 8, errors=nmass_errs, logtask='trend_nmass'),
    SkaJobWatch('psmc', 2, logtask='psmc_daily_check', errors=psmc_errs),
    SkaJobWatch('scs107', 2, logdir='Logs', logtask='scs107_check'),
    SkaJobWatch('telem_archive', 2, errors=telem_archive_errs),
    SkaJobWatch('cmd_states', 2),
    SkaJobWatch('perigee_health_plots', 2, logdir='Logs'),
    ])


set_report_attrs(jws)
basedir = DateTime(args.date_now).greta[:7]
index_html = make_html_report(jws, args.rootdir, basedir)

recipients = ['aldcroft@gmail.com',  # 'head.cfa.harvard.edu',
              # 'jeanconn@head.cfa.harvard.edu'
              ]

if args.email:
    jobwatch.sendmail(recipients, index_html)

jobwatch.remove_old_reports(args.rootdir, args.date_now, args.max_age)
