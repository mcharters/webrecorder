import json

from bottle import request, HTTPError

from webrecorder.basecontroller import BaseController
from webrecorder.webreccork import ValidationException


class ApiController(BaseController):
    def __init__(self, app, jinja_env, manager, config):
        super(ApiController, self).__init__(app, jinja_env, manager, config)

    def init_routes(self):

        @self.app.post('/api/v1/login')
        def login():
            """Authenticate users"""
            data = request.json
            username = data.get('username', '')
            password = data.get('password', '')

            if not self.manager.cork.login(username, password):
                return HTTPError(status=401)

            sesh = self.get_session()
            sesh.curr_user = username
            sesh.curr_role = self.manager.cork.user(sesh.curr_user).role

            remember_me = (data.get('remember_me') in ('1', 'on'))
            sesh.logged_in(remember_me)

            return {
                'username': sesh.curr_user,
                'role': sesh.curr_role,
                'coll_count': self.manager.num_collections(username),
                'anon': False
            }

        @self.app.get('/api/v1/logout')
        def logout():
            self.manager.cork.logout(success_redirect='/')

        @self.app.get('/api/v1/load_auth')
        def load_auth():
            sesh = self.get_session()

            if sesh:
                # current user
                u = self.manager.get_curr_user()
                count = self.manager.num_collections(u) if u else 0

                return {
                    'username': sesh.curr_user,
                    'role': sesh.curr_role,
                    'anon': sesh.is_anon(),
                    'coll_count': count,
                }

            return {'username': None, 'role': None, 'anon': None}

        @self.app.get('/api/v1/username_check')
        def test_username():
            username = request.query.username
            users = self.manager.get_users()

            if username in users or username in self.manager.RESTRICTED_NAMES:
                return {'available': False}

            return {'available': True}

        @self.app.post('/api/v1/updatepassword')
        def update_password():
            # check user is logged in and is an archivist or higher
            self.manager.cork.require(role='archivist', fail_redirect='/_login')

            curr_password = self.post_get('currPass')
            password = self.post_get('newPass')
            confirm_password = self.post_get('newPass2')

            try:
                self.manager.update_password(curr_password, password,
                                             confirm_password)
                return {}
            except ValidationException as ve:
                return self._raise_error(403, str(ve), api=True)
