"""Release identity shared by the UI, Windows resources and installer build."""
VERSION = '2.0.1'
DEVELOPER = 'Ahsan Iftikhar'
PRODUCT_NAME = 'Ainak Mahal'
try:
    from _build_info import BUILD_ID, FILE_VERSION
except ImportError:
    BUILD_ID = 'source'
    FILE_VERSION = (2, 0, 1, 0)

DISPLAY_VERSION = f'{VERSION} · Build {BUILD_ID}'
DEVELOPER_CREDIT = f'Developed by {DEVELOPER}'
