import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import jobwatch

os.chdir(os.path.dirname(__file__))


def test_path1():
    jw = jobwatch.SkaJobWatch(task='arc', logdir='Logs')
    assert jw.filename == '/proj/sot/ska/data/arc/Logs/daily.0/arc.log'


def test_path2():
    jw = jobwatch.SkaJobWatch(task='eng_archive')
    assert jw.filename == ('/proj/sot/ska/data/eng_archive/' +
                          'logs/daily.0/eng_archive.log')


def test_not_stale():
    filename = 'logs/stale.log'
    os.utime(filename, None)
    jw = jobwatch.JobWatch('stale', filename, maxage=0.1)
    assert jw.stale == False


def test_stale():
    filename = 'logs/stale.log'
    ten_hours_ago = time.time() - 10 * 3600.0
    os.utime(filename, (ten_hours_ago, ten_hours_ago))
    jw = jobwatch.JobWatch('stale', filename, maxage=0.1)
    assert jw.stale == True


def test_exists():
    filename = 'logs/doesnt_exist'
    jw = jobwatch.JobWatch('exists', filename, errors=('warn', 'error'))
    assert jw.exists == False


def test_default_errors():
    jw = jobwatch.JobWatch('errors', 'logs/errors.log',
                           errors=('warn', 'error'))
    assert len(jw.found_errors) == 4
    assert jw.found_errors[2] == (60, 'warn test message 3\n', 'warn')


def test_missing_requires():
    jw = jobwatch.JobWatch('requires', 'logs/errors.log',
                           errors=('warn', 'error'),
                           requires=('hello world', 'appending'))
    assert jw.missing_requires == set(['hello world'])


def test_filewatch():
    jobfile = ('/proj/sot/ska/www/ASPECT/obc_rate_noise/'
               'trending/pitch_hist_recent.png')
    Watch = jobwatch.FileWatch
    jws = [Watch(task='obc_rate_noise', filename=jobfile, maxage=50)]
    jobwatch.make_html_summary(jws, outdir='outfile')


def test_dbwatch():
    Watch = jobwatch.SkaDbWatch
    jws = [Watch('DB acq_stats_data', timekey='tstart',
                 table='acq_stats_data', maxage=4),
           Watch('DB trak_stats_data', timekey='kalman_tstart',
                 table='trak_stats_data', maxage=4),
           Watch('DB obspar', timekey='tstart', table='obspar', maxage=4),
           Watch('DB aiprops', timekey='tstart', table='aiprops', maxage=4),
           ]
    jobwatch.make_html_summary(jws, outdir='outdb')


def test_make_html_summary():
    jws = [jobwatch.JobWatch('errors', 'logs/errors.log',
                             errors=('warn', 'error'),
                             requires=('MISSING REQUIRED OUTPUT',
                                       'MORE missing output',
                                       'APPending')),
           jobwatch.SkaJobWatch(task='eng_archive'),
           jobwatch.SkaJobWatch(task='astromon')]
    jobwatch.make_html_summary(jws)
