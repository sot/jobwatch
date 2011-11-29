#!/usr/bin/env python

from jobwatch import FileWatch, SkaJobWatch, SkaDbWatch, make_html_summary
import jobwatch

dbs = 1 or [
    SkaDbWatch('acq_stats_data', 4),
    SkaDbWatch('aiprops', 4),
    SkaDbWatch('cmds', -1, timekey='date'),
    SkaDbWatch('cmd_states', -1, timekey='datestart'),
    SkaDbWatch('load_segments', -1, timekey='datestart'),
    SkaDbWatch('obspar', 4),
    SkaDbWatch('starcheck_obs', 4, timekey='mp_starcat_time'),
    SkaDbWatch('trak_stats_data', 4, timekey='kalman_tstart'),
    ]


class WebWatch(FileWatch):
    def __init__(self, task, maxage, basename,
                 filename='/proj/sot/ska/www/ASPECT/{task}/{basename}'):
        self.basename = basename
        super(WebWatch, self).__init__(task, maxage, filename)


files = 1 or [
    WebWatch('acq_stat_reports', 10, 'index.html'),
    WebWatch('arc', 1, 'index.html'),
    WebWatch('celmon', 30, 'offsets-ACIS-S-hist.gif'),
    FileWatch('dsn_summary', 1,
              '/proj/sot/ska/data/dsn_summary/dsn_summary.dat'),
    WebWatch('gui_stat_reports', 10, 'index.html'),
    WebWatch('fid_drift', 2, 'drift_acis_s.png'),
    WebWatch('obc_rate_noise', 50, 'trending/pitch_hist_recent.png'),
    WebWatch('perigee_health_plots', 5, 'index.html'),
    ]

perl_errs = set(('uninitialized value',
                 '(?<!Program caused arithmetic )error',
                 'warn', 'fatal', 'fail', 'undefined value'))
arc_errs = perl_errs.copy()
arc_errs.remove('warn')
arc_errs.add('warning(?!:\s+\d+\s)')
py_errs = set(jobwatch.ERRORS)
jean_db = '/proj/sot/ska/data/database/Logs/daily.0/{task}.log'
nmass_errs = set(('error', 'fatal', 'exception', 'traceback',
                  'warn(?!ing: imaging routines will not be available)',
                  'fail(?!ed to import sherpa)'))
star_stat = '/proj/sot/ska/data/star_stat_db/Logs/daily.0/{task}.log'

psmc_errs = set(jobwatch.ERRORS)
psmc_errs.remove('traceback')
psmc_errs.add("traceback(?!': True)")

jobs = [
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
    SkaJobWatch('scs107', 2, logtask='scs107_check'),
    SkaJobWatch('telem_archive', 2, errors=py_errs.union(perl_errs)),
    SkaJobWatch('cmd_states', 2),
    SkaJobWatch('perigee_health_plots', 2, logdir='Logs'),
    ]


# dbs + files +
make_html_summary(jobs, outdir='ska')
