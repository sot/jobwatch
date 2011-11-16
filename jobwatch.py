"""
Watch log output from processing jobs and check for problems.
"""

import re
import os
import time


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

        # logfile status checks
        self.exists = None
        self.stale = None
        self.age = None
        self.missing_requires = None
        self.found_errors = None

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

        for i, line in enumerate(open(logfile, 'r')):
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
