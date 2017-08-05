from fabric.api import *
from os import path

PRODUCTION = 'coderek@derekzeng.me:22'

env.hosts = ['derekzeng.me']
env.user = 'coderek'

DEST_PATH = '/home/coderek/mysite'
REPO = 'ssh://git@bitbucket.org/zen1986/mysite.git'
PRODUCTION_SETTING = 'configs/settings_prod.py'
SETTING_PATH = '%s/mysite/settings.py' % DEST_PATH

def deploy():
    with settings(warn_only=True):
        if run('test -d %s' % DEST_PATH).failed:
            run('git clone %s %s'% (REPO, DEST_PATH))

    with cd(DEST_PATH):
        run('git fetch')
        changes = run('git diff --stat origin/master')
        run('git merge origin/master')

        with prefix('source /home/coderek/envs/py3/bin/activate'):
            if 'package.json' in changes:
                run('npm install')
            else:
                print('No change to package.json')

            if 'requirements_prod.txt' in changes:
                run('pip install -r configs/requirements_prod.txt')
            else:
                print('No change to requirements_prod.txt')

            run('python3 manage.py collectstatic --noinput')
            run('python3 manage.py migrate')

    restart()
