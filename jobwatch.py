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

FILEDIR = os.path.dirname(__file__)
INDEX_TEMPLATE = os.path.join(FILEDIR, 'index_template.html')
LOG_TEMPLATE = os.path.join(FILEDIR, 'log_template.html')


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


def set_report_attrs(jobwatches):
    error_line = '<a name=error{0}><span class="red">{1}</span></a>'

    for i_jw, jw in enumerate(jobwatches):
        jw.ok = jw.exists and not (jw.stale or
                                   jw.missing_requires or
                                   jw.found_errors)

        jw.abs_filename = os.path.abspath(jw.filename)
        jw.log_html_name = 'log{}.html'.format(i_jw)
        jw.age_str = '{:.2f}'.format(jw.age) if jw.exists else 'None'
        if jw.stale:
            jw.age_str = '<span style="color:red";>{}</span>'.format(
                jw.age_str)
        if i_jw == 0 or jw.type != jobwatches[i_jw - 1].type:
            jw.span_cols_text = jw.type

        maxerrs = 10
        if not jw.ok and jw.found_errors:
            popups = [re.sub(r'[\'"]', '', line.strip())
                      for _, line, _ in jw.found_errors[:maxerrs]]
            if len(jw.found_errors) > maxerrs:
                popups.append('AND {} MORE'.format(
                        len(jw.found_errors) - maxerrs))
            popup = '<br/>'.join(popups)
            jw.overlib = ('ONMOUSEOVER="return overlib (\'{}\', WIDTH, 600);" '
                          'ONMOUSEOUT="return nd();"'.format(popup))

        html_lines = list(jw.filelines)
        for i_line, line, error in jw.found_errors:
            html_lines[i_line] = error_line.format(i_line, line)
        jw.html_lines = '<br/>'.join(html_lines)

        jw.prev_index = ''


def rundate(datenow):
    now = DateTime(datenow)
    return '{} ({})'.format(
        now.date[:8], time.strftime('%a %b %d', time.gmtime(now.unix)))


def make_html_report(jobwatches, rootdir, datenow):
    currdir = DateTime(datenow).greta[:7]
    prevdir = (DateTime(datenow) - 1).greta[:7]
    nextdir = (DateTime(datenow) + 1).greta[:7]
    outdir = os.path.join(rootdir, currdir)
    if not os.path.exists(outdir):
        os.mkdir(outdir)

    log_template = jinja2.Template(open(LOG_TEMPLATE, 'r').read())
    root_prefix = '../{}/'
    curr_prefix = ''
    prev_prefix = root_prefix.format(prevdir)
    next_prefix = root_prefix.format(nextdir)
    for i_jw, jw in enumerate(jobwatches):
        jw.http_prefix = curr_prefix
        jw.prev_http_prefix = prev_prefix
        jw.next_http_prefix = next_prefix
        log_html = log_template.render(**jw.__dict__)

        outfile = open(os.path.join(outdir, jw.log_html_name), 'w')
        outfile.write(log_html)
        outfile.close()

    index_template = jinja2.Template(open(INDEX_TEMPLATE, 'r').read())
    index_html = index_template.render(jobwatches=jobwatches,
                                       rundate=rundate(datenow),
                                       curr_prefix=curr_prefix,
                                       next_prefix=next_prefix,
                                       prev_prefix=prev_prefix,
                                       )

    outfile = open(os.path.join(outdir, 'index.html'), 'w')
    outfile.write(index_html)
    outfile.close()

    # Set an absolute http_prefix for the emailed version of index.html
    root_prefix = 'http://cxc.harvard.edu/mta/ASPECT/skawatch/{}/'
    curr_prefix = root_prefix.format(currdir)
    prev_prefix = root_prefix.format(prevdir)
    next_prefix = root_prefix.format(nextdir)
    for jw in jobwatches:
        jw.http_prefix = root_prefix.format(currdir)
        jw.prev_http_prefix = root_prefix.format(prevdir)
        jw.next_http_prefix = root_prefix.format(nextdir)
    index_html = index_template.render(jobwatches=jobwatches,
                                       rundate=rundate(datenow),
                                       curr_prefix=curr_prefix,
                                       next_prefix=next_prefix,
                                       prev_prefix=prev_prefix,
                                       )

    return index_html


def remove_old_reports(rootdir, date_now, max_age):
    secs_now = DateTime(date_now).secs
    for age in range(max_age, max_age + 30):
        date = DateTime(secs_now - age * 86400).greta[:7]
        outdir = os.path.join(rootdir, date)
        if os.path.exists(outdir):
            shutil.rmtree(outdir)


def sendmail(recipients, html, datenow):
    me = os.environ['USER'] + '@head.cfa.harvard.edu'
    msg = MIMEText(html, 'html')
    msg['Subject'] = 'Ska job status: {}'.format(rundate(datenow))
    msg['From'] = me
    msg['To'] = ','.join(recipients)
    s = smtplib.SMTP('localhost')
    s.sendmail(me, recipients, msg.as_string())
    s.quit()


def copy_errs(vals, removes=[], adds=[]):
    newvals = set(vals) - set(removes)
    newvals.update(adds)
    return newvals
