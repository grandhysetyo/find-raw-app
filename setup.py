from setuptools import setup

APP = ['app.py']
DATA_FILES = ['client_secret.json']
OPTIONS = {
    'argv_emulation': True,
    'packages': [
        'google',
        'google_auth_oauthlib',
        'google.oauth2',
        'google.auth.transport',
        'requests',  # penting
        'idna',      # untuk urllib
    ],
    'includes': ['idna.idnadata'],
    'resources': ['client_secret.json'],
    'plist': {
        'CFBundleName': 'RAW Finder',
        'CFBundleDisplayName': 'RAW Finder',
        'CFBundleIdentifier': 'com.raysmoments.rawfinder',
        'CFBundleVersion': '1.0',
        'CFBundleShortVersionString': '1.0',
    },
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
