import os
import time

import jobwatch


# Ska-specific watchers
class SkaWebWatch(jobwatch.FileWatch):
    def __init__(self, task, maxage, basename,
                 filename='/proj/sot/ska/www/ASPECT/{task}/{basename}'):
        self.basename = basename
        super(SkaWebWatch, self).__init__(task, maxage, filename)


class SkaJobWatch(jobwatch.JobWatch):
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


class SkaSqliteDbWatch(jobwatch.DbWatch):
    def __init__(self, task, maxage=1, dbfile=None, table=None, timekey='tstart'):
        super(SkaSqliteDbWatch, self).__init__(
            task, maxage=maxage, table=table, timekey=timekey,
            query='SELECT MAX({timekey}) AS maxtime FROM {table}',
            dbi='sqlite', server=dbfile)


os.chdir(os.path.dirname(__file__))


def test_path1():
    jw = SkaJobWatch(task='arc', logdir='Logs')
    assert jw.filename == '/proj/sot/ska/data/arc/Logs/daily.0/arc.log'


def test_path2():
    jw = SkaJobWatch(task='eng_archive')
    assert jw.filename == ('/proj/sot/ska/data/eng_archive/' +
                           'logs/daily.0/eng_archive.log')


def test_not_stale():
    filename = 'logs/stale.log'
    os.utime(filename, None)
    jw = jobwatch.JobWatch('stale', filename, maxage=0.1)
    assert jw.stale is False


def test_stale():
    filename = 'logs/stale.log'
    ten_hours_ago = time.time() - 10 * 3600.0
    os.utime(filename, (ten_hours_ago, ten_hours_ago))
    jw = jobwatch.JobWatch('stale', filename, maxage=0.1)
    assert jw.stale is True


def test_exists():
    filename = 'logs/doesnt_exist'
    jw = jobwatch.JobWatch('exists', filename, errors=('warn', 'error'))
    assert jw.exists is False


def test_default_errors():
    jw = jobwatch.JobWatch('errors', 'logs/errors.log',
                           errors=('warn', 'error'))
    assert len(jw.found_errors) == 5
    assert jw.found_errors[2] == (60, 'warn test message 3\n', 'warn')


def test_missing_requires():
    jw = jobwatch.JobWatch('requires', 'logs/errors.log',
                           errors=('warn', 'error'),
                           requires=('hello world', 'appending'))
    assert jw.missing_requires == set(['hello world'])


def test_filewatch(tmpdir):
    jobfile = ('/proj/sot/ska/www/ASPECT/obc_rate_noise/'
               'trending/pitch_hist_recent.png')
    Watch = jobwatch.FileWatch
    jws = [Watch(task='obc_rate_noise', filename=jobfile, maxage=50)]
    jobwatch.set_report_attrs(jws)
    jobwatch.make_html_report(jws, rootdir=os.path.join(tmpdir, 'out_file'))


def test_make_html_report(tmpdir):
    perlidl_errs = ('Use of uninitialized value',
                    '(?<!Program caused arithmetic )error',
                    'warn',
                    'fatal')

    jws = [jobwatch.JobWatch('errors', 'logs/errors.log',
                             errors=perlidl_errs,
                             requires=('MISSING REQUIRED OUTPUT',
                                       'MORE missing output',
                                       'APPending')),
           SkaJobWatch(task='eng_archive'),
           SkaJobWatch(task='astromon')]
    jobwatch.set_report_attrs(jws)
    jobwatch.make_html_report(jws, rootdir=os.path.join(tmpdir, 'out_report'))
