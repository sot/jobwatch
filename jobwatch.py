"""
Watch log output from processing jobs and check for problems.
"""

import re
import os
import time
import jinja2

class JobWatch(object):
    errors = ('warn', 'error')
    requires = ()

    def __init__(self, logfile,
                 errors=None,
                 requires=None,
                 maxage=1):
        self._logfile = logfile
        self.errors = self.errors if (errors is None) else errors
        self.requires = self.requires if (requires is None) else requires
        self.maxage = maxage

        # Logfile status.  Initial values force NOT OK status by default.
        self.exists = False
        self.stale = True
        self.age = None
        self.missing_requires = True
        self.found_errors = True

        self.check()

    @property
    def logfile(self):
        return self._logfile.format(**self.__dict__)

    def check(self):
        logfile = self.logfile
        self.exists = os.path.exists(logfile)
        if not self.exists:
            return

        self.age = (time.time() - os.path.getmtime(logfile)) / 86400.0
        self.stale = self.age > self.maxage

        found_requires = set()
        found_errors = []

        self.loglines = open(logfile, 'r').readlines()
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
    def __init__(self, task, errors=None, requires=None, logdir='logs',
       logfile='/proj/sot/ska/data/{task}/{logdir}/daily.0/{task}.log',
       maxage=1):
        self.task = task
        self.logdir = logdir
        super(SkaJobWatch, self).__init__(logfile, errors=errors,
                                          requires=requires, maxage=maxage)

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
        status_rows.append({'ok': ok, 'task': task, 'log_html': log_html_name})

        loglines = list(jw.loglines)
        for i_line, line, error in jw.found_errors:
            loglines[i_line] = error_line.format(i_line, loglines[i_line])
        
        log_html = template.render(task=task,
                                   loglines='<br/>'.join(loglines),
                                   found_errors=jw.found_errors,
                                   missing_requires=jw.missing_requires)
        outfile = open(os.path.join(outdir, log_html_name), 'w')
        outfile.write(log_html)
        outfile.close()

    if not os.path.isabs(index_template):
        index_template = os.path.join(filedir, index_template)
    template = jinja2.Template(open(index_template, 'r').read())
    index_html = template.render(status_rows=status_rows)

    outfile = open(os.path.join(outdir, 'index.html'), 'w')
    outfile.write(index_html)
    outfile.close()
    
    
