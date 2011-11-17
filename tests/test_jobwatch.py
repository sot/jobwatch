import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import jobwatch

os.chdir(os.path.dirname(__file__))

def test_path1():
    jw = jobwatch.SkaJobWatch(task='arc', logdir='Logs')
    assert jw.logfile == '/proj/sot/ska/data/arc/Logs/daily.0/arc.log'

def test_path2():
    jw = jobwatch.SkaJobWatch(task='eng_archive')
    assert jw.logfile == ('/proj/sot/ska/data/eng_archive/' +
                          'logs/daily.0/eng_archive.log')

def test_not_stale():
    logfile = 'logs/stale.log'
    os.utime(logfile, None)
    jw = jobwatch.JobWatch(logfile, maxage=0.1)
    assert jw.stale == False
    
def test_stale():
    logfile = 'logs/stale.log'
    ten_hours_ago = time.time() - 10 * 3600.0
    os.utime(logfile, (ten_hours_ago, ten_hours_ago))
    jw = jobwatch.JobWatch(logfile, maxage=0.1)
    assert jw.stale == True
    
def test_exists():
    logfile = 'logs/doesnt_exist'
    jw = jobwatch.JobWatch(logfile, errors=('warn', 'error'))
    assert jw.exists == False

def test_default_errors():
    jw = jobwatch.JobWatch('logs/errors.log', errors=('warn', 'error'))
    assert len(jw.found_errors) == 4
    assert jw.found_errors[2] == (60, 'warn test message 3\n', 'warn')

def test_missing_requires():
    jw = jobwatch.JobWatch('logs/errors.log', errors=('warn', 'error'),
                           requires=('hello world', 'appending'))
    assert jw.missing_requires == set(['hello world'])

def test_make_html_summary():
    jws = [jobwatch.JobWatch('logs/errors.log',
                             errors=('warn', 'error'),
                             requires=('MISSING REQUIRED OUTPUT',
                                       'MORE missing output',
                                       'APPending')),
           jobwatch.SkaJobWatch(task='eng_archive'),
           jobwatch.SkaJobWatch(task='astromon')]
    jobwatch.make_html_summary(jws)
    assert True
    
