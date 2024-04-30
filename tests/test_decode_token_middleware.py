import logging
import unittest
from unittest import mock

from telicent_lib.exceptions import ConfigurationException
from telicent_lib.middleware.decode_token import AccessMiddleware


class DecodeTokenTestCase(unittest.TestCase):

    def test_urls_must_be_set(self):
        self.assertRaises(ConfigurationException, AccessMiddleware, **{'app': None, 'jwt_header': None})

        mw = AccessMiddleware(app=None, jwt_header=None, jwks_url='https://example.com',
                              logger=logging.LoggerAdapter(logging.getLogger(), extra={}))
        self.assertEqual(mw.jwks_url, 'https://example.com')

        mw = AccessMiddleware(app=None, jwt_header=None, public_key_url='https://example.com/',
                              logger=logging.LoggerAdapter(logging.getLogger(), extra={}))
        self.assertEqual(mw.public_key_url, 'https://example.com')

    @mock.patch('telicent_lib.middleware.decode_token.jwt')
    def test_validate_jwks_token(self, mock_jwt):
        mock_jwt.get_unverified_header.return_value = {'alg': 'abc'}
        mock_jwt.PyJWKClient.return_value.get_signing_key_from_jwt.return_value = mock.Mock()

        mw = AccessMiddleware(app=None, jwt_header=None, jwks_url='https://example.com/',
                              logger=logging.LoggerAdapter(logging.getLogger(), extra={}))
        mw.validate_token('123456')

        mock_jwt.get_unverified_header.assert_called_with('123456')
        mock_jwt.PyJWKClient.assert_called_with('https://example.com/')
        mock_jwt.decode.assert_called_with(
            '123456', mock_jwt.PyJWKClient.return_value.get_signing_key_from_jwt().key, algorithms=['abc']
        )

    @mock.patch('telicent_lib.middleware.decode_token.requests')
    @mock.patch('telicent_lib.middleware.decode_token.jwt')
    def test_validate_public_key_token(self, mock_jwt, mock_requests):
        mock_jwt.get_unverified_header.return_value = {'kid': 'abc', 'alg': 'def'}
        mock_requests.get.return_value = mock.Mock()

        mw = AccessMiddleware(app=None, jwt_header=None, public_key_url='https://example.com/',
                              logger=logging.LoggerAdapter(logging.getLogger(), extra={}))
        mw.validate_token('123456')

        mock_jwt.get_unverified_header.assert_called_with('123456')
        mock_requests.get.assert_called_with('https://example.com/abc')
        mock_jwt.decode.assert_called_with(
            '123456', mock_requests.get().text, algorithms=['def']
        )
