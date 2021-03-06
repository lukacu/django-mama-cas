# -*- coding: utf-8 -*-

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.utils import modify_settings
from django.test.utils import override_settings

from mama_cas.utils import services as service_config
from mama_cas.utils import add_query_params
from mama_cas.utils import can_proxy_authentication
from mama_cas.utils import clean_service_url
from mama_cas.utils import get_callbacks
from mama_cas.utils import is_scheme_https
from mama_cas.utils import is_valid_proxy_callback
from mama_cas.utils import is_valid_service
from mama_cas.utils import match_service
from mama_cas.utils import redirect
from mama_cas.utils import to_bool


class UtilsTests(TestCase):
    def tearDown(self):
        try:
            # Remove cached property so the valid services
            # setting can be changed per-test
            del service_config.services
        except AttributeError:
            pass

    def test_add_query_params(self):
        """
        When called with a URL and a dict of parameters,
        ``add_query_params()`` should insert the parameters into the
        original URL.
        """
        url = 'http://www.example.com/?test3=blue'
        params = {'test1': 'red', 'test2': '', 'test3': 'indigo'}
        url = add_query_params(url, params)

        self.assertIn('test1=red', url)
        # Parameters with empty values should be ignored
        self.assertNotIn('test2=', url)
        # Existing parameters with the same name should be overwritten
        self.assertIn('test3=indigo', url)

    def test_add_query_params_unicode(self):
        """
        When Unicode parameters are provided, ``add_query_params()``
        should encode them appropriately.
        """
        params = {'unicode1': u'ä', u'unicode²': 'b'}
        url = add_query_params('http://www.example.com/', params)
        self.assertIn('unicode1=%C3%A4', url)
        self.assertIn('unicode%C2%B2=b', url)

    def test_is_scheme_https(self):
        """
        When called with a URL, ``is_scheme_https()`` should return
        ``True`` if the scheme is HTTPS, and ``False`` otherwise.
        """
        self.assertTrue(is_scheme_https('https://www.example.com/'))
        self.assertFalse(is_scheme_https('http://www.example.com/'))

    def test_clean_service_url(self):
        """
        When called with a URL, ``clean_service_url()`` should return
        the ``scheme``, ``netloc`` and ``path`` components of the URL.
        """
        url = 'http://www.example.com/test?test3=blue#green'
        self.assertEqual('http://www.example.com/test', clean_service_url(url))
        url = 'https://example.com:9443/'
        self.assertEqual('https://example.com:9443/', clean_service_url(url))

    def test_match_service(self):
        """
        When called with two service URLs, ``match_service()`` should return
        ``True`` if the ``scheme``, ``netloc`` and ``path`` components match
        and ``False`` otherwise.
        """
        self.assertTrue(match_service('https://www.example.com:80/', 'https://www.example.com:80/'))
        self.assertFalse(match_service('https://www.example.com:80/', 'https://www.example.com/'))
        self.assertFalse(match_service('https://www.example.com', 'https://www.example.com/'))

    @override_settings(MAMA_CAS_VALID_SERVICES=('http://.*\.example\.com',))
    def test_is_valid_service_tuple(self):
        """
        When valid services are configured, ``is_valid_service()``
        should return ``True`` if the provided URL matches, and
        ``False`` otherwise.
        """
        self.assertTrue(is_valid_service('http://www.example.com'))
        self.assertFalse(is_valid_service('http://www.example.org'))

    def test_is_valid_service(self):
        """
        When valid services are configured, ``is_valid_service()``
        should return ``True`` if the provided URL matches, and
        ``False`` otherwise.
        """
        self.assertTrue(is_valid_service('http://www.example.com'))
        self.assertFalse(is_valid_service('http://www.example.org'))

    @override_settings(MAMA_CAS_VALID_SERVICES=())
    def test_empty_valid_services_tuple(self):
        """
        When no valid services are configured,
        ``is_valid_service()`` should return ``True``.
        """
        self.assertTrue(is_valid_service('http://www.example.com'))

    @override_settings(MAMA_CAS_VALID_SERVICES=[])
    def test_empty_valid_services(self):
        """
        When no valid services are configured,
        ``is_valid_service()`` should return ``True``.
        """
        self.assertTrue(is_valid_service('http://www.example.com'))

    @override_settings(MAMA_CAS_VALID_SERVICES=[{}])
    def test_invalid_valid_services(self):
        """
        When invalid services are configured, ``is_valid_service``
        should raise ``ImproperlyConfigured``.
        """
        with self.assertRaises(ImproperlyConfigured):
            is_valid_service('http://www.example.com')

    @modify_settings(MAMA_CAS_VALID_SERVICES={
        'append': [{'SERVICE': 'http://example\.com/proxy', 'PROXY_ALLOW': False}]
    })
    def test_can_proxy_authentication(self):
        """
        When a service is configured to allow proxy authentication,
        `can_proxy_authentication()` should return `True`. If proxy
        authentication is disallowed, it should return `False`.
        """
        self.assertTrue(can_proxy_authentication('http://www.example.com'))
        self.assertFalse(can_proxy_authentication('http://example.com/proxy'))
        self.assertFalse(can_proxy_authentication('http://example.org'))

    def test_is_valid_proxy_callback(self):
        """
        When a valid pgturl is provided, `is_valid_proxy_callback()`
        should return `True`, otherwise it should return `False`.
        """
        self.assertTrue(is_valid_proxy_callback('https://www.example.com', 'https://www.example.com'))
        self.assertTrue(is_valid_proxy_callback('http://example.org', 'https://www.example.com'))
        self.assertFalse(is_valid_proxy_callback('http://example.org', 'http://example.org'))

    def test_get_callbacks(self):
        """
        When a valid service with a configured callbacks is provided,
        `get_callbacks()` should return the configured callbacks. If
        the service has no callbacks or an invalid service is provided,
        an empty list should be returned.
        """
        self.assertEqual(get_callbacks('https://www.example.com'), ['mama_cas.callbacks.user_name_attributes'])
        self.assertEqual(get_callbacks('http://example.com'), [])
        self.assertEqual(get_callbacks('http://example.org'), [])

    def test_redirect(self):
        """
        When redirecting, params should be injected on the redirection
        URL.
        """
        r = redirect('http://www.example.com', params={'test1': 'red'})
        self.assertEqual('http://www.example.com?test1=red', r['Location'])
        r = redirect('cas_login', params={'test3': 'blue'})
        self.assertEqual('/login?test3=blue', r['Location'])

    def test_redirect_no_params(self):
        """
        When redirecting, if no params are provided only the URL
        should be present.
        """
        r = redirect('http://www.example.com')
        self.assertEqual('http://www.example.com', r['Location'])
        r = redirect('cas_login')
        self.assertEqual('/login', r['Location'])

    def test_redirect_invalid(self):
        """
        A non-URL that does not match a view name should raise the
        appropriate exception.
        """
        r = redirect('http')
        self.assertEqual('/login', r['Location'])

    def test_to_bool(self):
        """
        Any string value should evaluate as ``True``. Empty strings
        or strings of whitespace should evaluate as ``False``.
        """
        self.assertTrue(to_bool('true'))
        self.assertTrue(to_bool('1'))
        self.assertFalse(to_bool(None))
        self.assertFalse(to_bool(''))
        self.assertFalse(to_bool('   '))
