import json

import jwt
import requests
from werkzeug.wrappers import Request, Response

from telicent_lib.exceptions import ConfigurationException
from telicent_lib.logging import CoreLoggerFactory

__license__ = """
Copyright (c) Telicent Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


auth_failed = {"ok": False, "message": "Authorization failed"}


class AccessMiddleware:
    """
    Simple middleware to validate and decode tokens
    """
    def __init__(self, app, jwt_header, logger=None, jwks_url=None, public_key_url=None):
        self.app = app
        if jwks_url is None and public_key_url is None:
            raise ConfigurationException(
                "access_middleware",
                "jwks_url or public_key_url",
                "Access middleware requires either a jwks_url or public_key_url"
            )
        self.jwks_url = jwks_url

        self.public_key_url = public_key_url
        if isinstance(self.public_key_url, str):
            self.public_key_url = self.public_key_url.strip("/")
        self.jwt_header = jwt_header
        if logger is None:
            self.logger = CoreLoggerFactory.get_logger(
                'Authenticator',
            )
        else:
            self.logger = logger

    def __call__(self, environ, start_response):
        request = Request(environ)
        if self.jwt_header not in request.headers:
            self.logger.error(
                f"Unauthorized access: No required header: {self.jwt_header}", log_type='UNAUTHORIZED'
            )
            res = Response(json.dumps(auth_failed), mimetype='application/json', status=401)
            return res(environ, start_response)
        encoded = request.headers[self.jwt_header]

        token = self.validate_token(encoded)

        if token is None:
            self.logger.error("Unauthorized access: token not valid", log_type="UNAUTHORIZED")
            res = Response(json.dumps(auth_failed), mimetype='application/json', status=401)
            return res(environ, start_response)
        environ['token'] = token
        return self.app(environ, start_response)

    def validate_token(self, token):
        try:
            headers = jwt.get_unverified_header(token)
            if self.jwks_url is not None:
                self.logger.debug("Validating token with jwks_url", log_type="GENERAL")
                jwks_client = jwt.PyJWKClient(self.jwks_url)
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                key = signing_key.key
            elif self.public_key_url is not None:
                self.logger.debug("Validating token with elb public key", log_type="GENERAL")
                public_key_ep = f"{self.public_key_url}/{headers['kid']}"
                req = requests.get(public_key_ep)
                key = req.text
            else:
                raise ConfigurationException("access_middleware", "jwks_url or public_key_url",
                                             "Token decoding requires either a jwks_url or public_key_url")
            data = jwt.decode(token, key, algorithms=[headers['alg']])
        except Exception as e:
            self.logger.error(f"Exception validating token: {str(e)}", log_type="UNAUTHORIZED")
            return None
        return data
