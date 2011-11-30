"""
Watch log output from processing jobs and check for problems.
"""

import re
import os
import time
import smtplib
from email.mime.text import MIMEText
import shutil

import jinja2
import Ska.DBI
from Chandra.Time import DateTime

LOUD = False
ERRORS = ('error', 'warn', 'fail', 'fatal', 'exception', 'traceback')


class JobWatch(object):
    def __init__(self, task, filename,
                 errors=(),
                 requires=(),
                 maxage=1):
        self.task = task
        self._filename = filename
        self.errors = errors
        self.requires = requires
        self.maxage = maxage
        self.filetime = None
        self.filedate = None

        self.check()

    @property
    def filename(self):
        return self._filename.format(**self.__dict__)

    @property
    def filelines(self):
        if not hasattr(self, '_filelines'):
            if self.exists:
                self._filelines = open(self.filename, 'r').readlines()
            else:
                self._filelines = []
        return self._filelines

    @property
    def age(self):
        if not hasattr(self, '_age'):
            self.filetime = os.path.getmtime(self.filename)
            self.filedate = time.ctime(self.filetime)
            self._age = (time.time() - self.filetime) / 86400.0
        return self._age

    @property
    def exists(self):
        if not hasattr(self, '_exists'):
            self._exists = os.path.exists(self.filename)
        return self._exists

    def check(self):
        if LOUD:
            print 'Checking ', repr(self)
        if not self.exists:
            self.stale = False
            self.missing_requires = set()
            self.found_errors = []
            return

        self.stale = self.age > self.maxage

        found_requires = set()
        found_errors = []
        for i, line in enumerate(self.filelines):
            for error in self.errors:
                if re.search(error, line, re.IGNORECASE):
                    found_errors.append((i, line, error))
            for require in self.requires:
                if re.search(require, line, re.IGNORECASE):
                    found_requires.add(require)

        self.missing_requires = set(self.requires) - found_requires
        self.found_errors = found_errors

    def __repr__(self):
        return '<JobWatch type={} task={}>'


class FileWatch(JobWatch):
    """Watch the date of a file but do not look into the file contents for
    errors.
    """
    def __init__(self, task, maxage=1,
                 filename=None):
        self.type = 'File'
        super(FileWatch, self).__init__(task, filename, maxage=maxage,
                                        errors=(), requires=())

    @property
    def filelines(self):
        return []


class SkaWebWatch(FileWatch):
    def __init__(self, task, maxage, basename,
                 filename='/proj/sot/ska/www/ASPECT/{task}/{basename}'):
        self.basename = basename
        super(SkaWebWatch, self).__init__(task, maxage, filename)


class SkaJobWatch(JobWatch):
    def __init__(self, task, maxage=1, errors=ERRORS, requires=(),
                 logdir='logs', logtask=None,
                 filename='/proj/sot/ska/data/{task}/' \
                         '{logdir}/daily.0/{logtask}.log'):
        self.type = 'Log'
        self.task = task
        self.logtask = logtask or task
        self.logdir = logdir
        super(SkaJobWatch, self).__init__(task, filename, errors=errors,
                                          requires=requires, maxage=maxage)


class SkaDbWatch(JobWatch):
    def __init__(self, task, maxage=1, table=None, timekey='tstart',
                 query='SELECT MAX({timekey}) AS maxtime FROM {table}'):
        self.type = 'DB'
        self.task = task
        self._query = query
        self.table = table or task
        self.timekey = timekey
        super(SkaDbWatch, self).__init__(task, filename='NONE', maxage=maxage)

    @property
    def query(self):
        return self._query.format(**self.__dict__)

    @property
    def filelines(self):
        return []

    @property
    def exists(self):
        return True

    @property
    def age(self):
        if not hasattr(self, '_age'):
            row = self.db.fetchone(self.query)
            self.filetime = DateTime(row['maxtime']).unix
            self.filedate = time.ctime(self.filetime)
            self._age = (time.time() - self.filetime) / 86400.0
        return self._age

    @property
    def db(self):
        if not hasattr(self.__class__, '_db'):
            self.__class__._db = Ska.DBI.DBI(dbi='sybase', server='sybase',
                                             user='aca_read', database='aca')
        return self._db


def make_html_report(jobwatches, outdir='out',
                     index_template='index_template.html',
                     log_template='log_template.html'):
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    filedir = os.path.dirname(__file__)
    error_line = '<a name=error{0}><span class="red">{1}</span></a>'

    if not os.path.isabs(log_template):
        log_template = os.path.join(filedir, log_template)
    template = jinja2.Template(open(log_template, 'r').read())

    rows = []
    for i_jw, jw in enumerate(jobwatches):
        ok = jw.exists and not (jw.stale or jw.missing_requires or
                                jw.found_errors)

        log_html_name = 'log{}.html'.format(i_jw)
        age = '{:.2f}'.format(jw.age) if jw.exists else 'None'
        if i_jw == 0 or jw.type != rows[-1]['type']:
            rows.append({'type': jw.type, 'task': None})
        rows.append({'ok': ok, 'task': jw.task, 'log_html': log_html_name,
                     'filedate': jw.filedate, 'age': age,
                     'type': jw.type, 'maxage': jw.maxage})

        filelines = list(jw.filelines)
        for i_line, line, error in jw.found_errors:
            filelines[i_line] = error_line.format(i_line, filelines[i_line])

        log_html = template.render(task=jw.task,
                                   filename=os.path.abspath(jw.filename),
                                   filelines='<br/>'.join(filelines),
                                   found_errors=jw.found_errors,
                                   missing_requires=jw.missing_requires,
                                   filedate=jw.filedate)
        outfile = open(os.path.join(outdir, log_html_name), 'w')
        outfile.write(log_html)
        outfile.close()

    if not os.path.isabs(index_template):
        index_template = os.path.join(filedir, index_template)
    template = jinja2.Template(open(index_template, 'r').read())
    index_html = template.render(status_rows=rows,
                                 rundate=time.ctime(),
                                 )

    outfile = open(os.path.join(outdir, 'index.html'), 'w')
    outfile.write(index_html)
    outfile.close()

    return index_html


def remove_old_reports(rootdir, date_now, max_age):
    secs_now = DateTime(date_now).secs
    for age in range(max_age, max_age + 30):
        date = DateTime(secs_now - age * 86400).greta[:7]
        outdir = os.path.join(rootdir, date)
        if os.path.exists(outdir):
            print 'Removing', outdir
            shutil.rmtree(outdir)


def sendmail(recipients, html):
    me = os.environ['user'] + '@head.cfa.harvard.edu'
    msg = MIMEText(html, 'html')
    msg['Subject'] = 'Skawatch monitor'
    msg['From'] = me
    msg['To'] = ','.join(recipients)
    s = smtplib.SMTP('localhost')
    s.sendmail(me, recipients, msg.as_string())
    s.quit()


def copy_errs(vals, removes=[], adds=[]):
    newvals = set(vals) - set(removes)
    newvals.update(adds)
    return newvals
