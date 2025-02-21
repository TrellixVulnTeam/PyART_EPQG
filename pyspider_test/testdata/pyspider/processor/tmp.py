import os
import six
import sys
import imp
import time
import weakref
import logging
import inspect
import traceback
import linecache
from pyspider.libs import utils
from pyspider.libs.log import SaveLogHandler, LogFormatter
logger = logging.getLogger("processor")


class ProjectManager(object):

    CHECK_PROJECTS_INTERVAL = 5 * 60
    RELOAD_PROJECT_INTERVAL = 60 * 60

    @staticmethod
    def build_module(project, env=None):
        from pyspider.libs import base_handler
        assert 'name' in project, 'need name of project'
        assert 'script' in project, 'need script of project'

        if env is None:
            env = {}
        pyspider_path = os.path.join(os.path.dirname(__file__), "..")
        if pyspider_path not in sys.path:

        env = dict(env)
        env.update({
            'debug': project.get('status', 'DEBUG') == 'DEBUG',
        })

        loader = ProjectLoader(project)

        module.log_buffer = []
        module.logging = module.logger = logging.Logger(project['name'])
            handler = SaveLogHandler(module.log_buffer)
        else:
            handler = logging.StreamHandler()
            handler.setFormatter(LogFormatter(color=True))

        if '__handler_cls__' not in module.__dict__:
            for each in list(six.itervalues(module.__dict__)):
                        and issubclass(each, BaseHandler):
                    module.__dict__['__handler_cls__'] = each
        _class = module.__dict__.get('__handler_cls__')
        assert _class is not None, "need BaseHandler in project module"

        instance = _class()
        instance.__env__ = env
        instance.project_name = project['name']
        instance.project = project

        return {
            'loader': loader,
            'module': module,
            'class': _class,
            'instance': instance,
            'exception': None,
            'exception_log': '',
            'info': project,
        }

    def __init__(self, projectdb, env):
        self.projectdb = projectdb
        self.env = env

        self.projects = {}
        self.last_check_projects = time.time()

    def _need_update(self, project_name, updatetime=None, md5sum=None):
        if project_name not in self.projects:
            return True
        elif md5sum and md5sum != self.projects[project_name]['info'].get('md5sum'):
            return True
        elif updatetime and updatetime > self.projects[project_name]['info'].get('updatetime', 0):
            return True
        elif time.time() - self.projects[project_name]['load_time'] > self.RELOAD_PROJECT_INTERVAL:
            return True
        return False

    def _check_projects(self):
        for project in self.projectdb.check_update(self.last_check_projects,
                                                   ['name', 'updatetime']):
            if project['name'] not in self.projects:
                continue
            if project['updatetime'] > self.projects[project['name']]['info'].get('updatetime', 0):
                self._update_project(project['name'])
        self.last_check_projects = time.time()

    def _update_project(self, project_name):
        if not project:
            return None
        return self._load_project(project)

    def _load_project(self, project):
        try:
            ret = self.build_module(project, self.env)
            self.projects[project['name']] = ret
        except Exception as e:
            ret = {
                'loader': None,
                'module': None,
                'class': None,
                'instance': None,
                'exception': e,
                'info': project,
                'load_time': time.time(),
            }
            self.projects[project['name']] = ret
            return False
        return True

    def get(self, project_name, updatetime=None, md5sum=None):
        if time.time() - self.last_check_projects > self.CHECK_PROJECTS_INTERVAL:
            self._check_projects()
        if self._need_update(project_name, updatetime, md5sum):
            self._update_project(project_name)


class ProjectLoader(object):

    def __init__(self, project, mod=None):
        self.project = project
        self.name = project['name']
        self.mod = mod
        pass

    def load_module(self, fullname):
        if self.mod is None:
            self.mod = mod = imp.new_module(fullname)
        else:
            mod = self.mod
        mod.__file__ = '<%s>' % self.name
        mod.__loader__ = self
        mod.__project__ = self.project
        mod.__package__ = ''
        code = self.get_code(fullname)
        if sys.version_info[:2] == (3, 3):
            sys.modules[fullname] = mod
        return mod

    def is_package(self, fullname):
        return False

    def get_code(self, fullname):
        return compile(self.get_source(fullname), '<%s>' % self.name, 'exec')

    def get_source(self, fullname):
        script = self.project['script']
        if isinstance(script, six.text_type):
        return script


if six.PY2:
    class ProjectFinder(object):

        def __init__(self, projectdb):

        @property
        def projectdb(self):
            return self.get_projectdb()

        def find_module(self, fullname, path=None):
            if fullname == 'projects':
                return self
            if len(parts) == 2 and parts[0] == 'projects':
                name = parts[1]
                if not self.projectdb:
                    return
                info = self.projectdb.get(name)
                if info:
                    return ProjectLoader(info)

        def load_module(self, fullname):
            mod = imp.new_module(fullname)
            mod.__file__ = '<projects>'
            mod.__loader__ = self
            mod.__path__ = ['<projects>']
            mod.__package__ = 'projects'
            return mod

        def is_package(self, fullname):
            return True
else:
    import importlib.abc

    class ProjectFinder(importlib.abc.MetaPathFinder):

        def __init__(self, projectdb):
            self.get_projectdb = weakref.ref(projectdb)

        @property
        def projectdb(self):
            return self.get_projectdb()

        def find_spec(self, fullname, path, target=None):
            if loader:

        def find_module(self, fullname, path):
            if fullname == 'projects':
                return ProjectsLoader()
            parts = fullname.split('.')
            if len(parts) == 2 and parts[0] == 'projects':
                name = parts[1]
                if not self.projectdb:
                    return
                info = self.projectdb.get(name)
                if info:
                    return ProjectLoader(info)

    class ProjectsLoader(importlib.abc.InspectLoader):
        def load_module(self, fullname):
            mod = imp.new_module(fullname)
            mod.__file__ = '<projects>'
            mod.__loader__ = self
            mod.__path__ = ['<projects>']
            mod.__package__ = 'projects'
            if sys.version_info[:2] == (3, 3):
                sys.modules[fullname] = mod
            return mod

        def module_repr(self, module):
            return '<Module projects>'

        def is_package(self, fullname):
            return True

        def get_source(self, path):
            return ''

        def get_code(self, fullname):
            return compile(self.get_source(fullname), '<projects>', 'exec')

    class ProjectLoader(ProjectLoader, importlib.abc.Loader):
        def create_module(self, spec):
            reveal_type(self)