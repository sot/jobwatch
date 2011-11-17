"""
Watch log output from processing jobs and check for problems.
"""

import re
import os
import time
import jinja2

class JobWatch(object):
    def __init__(self, logfile,
                 errors=(),
                 requires=(),
                 maxage=1):
        self._logfile = logfile
        self.errors = errors
        self.requires = requires
        self.maxage = maxage

        # Logfile status

        self.check()

    @property
    def logfile(self):
        return self._logfile.format(**self.__dict__)

    @property
    def loglines(self):
        if not hasattr(self, '_loglines'):
            self._loglines = open(self.logfile, 'r').readlines()
        return self._loglines

    @property
    def age(self):
        if not hasattr(self, '_age'):
            self.filetime = os.path.getmtime(self.logfile)
            self.filedate = time.ctime(self.filetime)
            self._age = (time.time() - self.filetime) / 86400.0
        return self._age

    @property
    def exists(self):
        if not hasattr(self, '_exists'):
            self._exists = os.path.exists(self.logfile)
        return self._exists

    def check(self):
        if not self.exists:
            self.stale = False
            self.missing_requires = set()
            self.found_errors = []
            return

        self.stale = self.age > self.maxage

        found_requires = set()
        found_errors = []

        for i, line in enumerate(self.loglines):
            for error in self.errors:
                if re.search(error, line, re.IGNORECASE):
                    found_errors.append((i, line, error))
            for require in self.requires:
                if re.search(require, line, re.IGNORECASE):
                    found_requires.add(require)

        self.missing_requires = set(self.requires) - found_requires
        self.found_errors = found_errors


class SkaJobWatch(JobWatch):
    def __init__(self, task, errors=('warn', 'error'), requires=(),
                 logdir='logs', maxage=1,
                 logfile='/proj/sot/ska/data/{task}/{logdir}/daily.0/{task}.log'):
        self.task = task
        self.logdir = logdir
        super(SkaJobWatch, self).__init__(logfile, errors=errors,
                                          requires=requires, maxage=maxage)

class SkaDbWatch(JobWatch):
    def __init__(self, task, maxage=1, query=None, logfile='NONE'):
        self.task = task
        super(SkaDbWatch, self).__init__('NONE', maxage=maxage)

    @property
    def loglines(self):
        return list()

    def check(self):
        self.exists = True
        pass

def make_html_summary(jobwatches, outdir='out',
                     index_template='index_template.html',
                     log_template='log_template.html'):
    filedir = os.path.dirname(__file__)
    error_line = '<a name=error{0}><span class="red">{1}</span></a>'

    if not os.path.isabs(log_template):
        log_template = os.path.join(filedir, log_template)
    template = jinja2.Template(open(log_template, 'r').read())

    status_rows = []
    for i_jw, jw in enumerate(jobwatches):
        ok = jw.exists and not (jw.stale or jw.missing_requires or
                                jw.found_errors)
        try:
            task = jw.task
        except AttributeError:
            task = os.path.basename(jw.logfile)

        
        log_html_name = 'log{}.html'.format(i_jw)
        rundate = time.ctime()
        status_rows.append({'ok': ok, 'task': task, 'log_html': log_html_name,
                            'filedate': jw.filedate, 'age': jw.age,
                            'maxage': jw.maxage})

        loglines = list(jw.loglines)
        for i_line, line, error in jw.found_errors:
            loglines[i_line] = error_line.format(i_line, loglines[i_line])
        
        log_html = template.render(task=task,
                                   logfile=os.path.abspath(jw.logfile),
                                   loglines='<br/>'.join(loglines),
                                   found_errors=jw.found_errors,
                                   missing_requires=jw.missing_requires,
                                   filedate=jw.filedate)
        outfile = open(os.path.join(outdir, log_html_name), 'w')
        outfile.write(log_html)
        outfile.close()

    if not os.path.isabs(index_template):
        index_template = os.path.join(filedir, index_template)
    template = jinja2.Template(open(index_template, 'r').read())
    index_html = template.render(status_rows=status_rows,
                                 rundate=time.ctime(),
                                 )

    outfile = open(os.path.join(outdir, 'index.html'), 'w')
    outfile.write(index_html)
    outfile.close()
    
    
