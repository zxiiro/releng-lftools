# SPDX-License-Identifier: EPL-1.0
##############################################################################
# Copyright (c) 2018 The Linux Foundation and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Eclipse Public License v1.0
# which accompanies this distribution, and is available at
# http://www.eclipse.org/legal/epl-v10.html
##############################################################################
"""Test deploy command."""

import os
import sys

import pytest
import requests

from lftools import cli
import lftools.deploy as deploy_sys

FIXTURE_DIR = os.path.join(
    os.path.dirname(os.path.realpath(__file__)),
    'fixtures',
    )


def test_format_url():
    """Test url format."""
    test_url=[["192.168.1.1", "http://192.168.1.1"],
         ["192.168.1.1:8081", "http://192.168.1.1:8081"],
         ["192.168.1.1:8081/nexus", "http://192.168.1.1:8081/nexus"],
         ["192.168.1.1:8081/nexus/", "http://192.168.1.1:8081/nexus"],
         ["http://192.168.1.1:8081/nexus", "http://192.168.1.1:8081/nexus"],
         ["https://192.168.1.1:8081/nexus", "https://192.168.1.1:8081/nexus"],
         ["https://192.168.1.1:8081/nexus/", "https://192.168.1.1:8081/nexus"],
         ["www.goodnexussite.org:8081", "http://www.goodnexussite.org:8081"],
         ["192.168.1.1:8081/nexus///", "http://192.168.1.1:8081/nexus"]]

    for url in test_url:
        assert deploy_sys._format_url(url[0]) == url[1]


def test_log_and_exit():
    """Test exit."""
    with pytest.raises(SystemExit) as excinfo:
        deploy_sys._log_error_and_exit("testmsg")
    assert excinfo.type == SystemExit


@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'deploy'),
    )
def test_copy_archive_dir(cli_runner, datafiles):
    """Test copy_archives() command to ensure archives dir is copied."""
    os.chdir(str(datafiles))
    workspace_dir = os.path.join(str(datafiles), 'workspace')
    stage_dir = str(datafiles.mkdir("stage_archive"))

    os.chdir(stage_dir)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'copy-archives', workspace_dir],
        obj={})
    assert result.exit_code == 0

    assert os.path.exists(os.path.join(stage_dir, 'test.log'))

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'deploy'),
    )
def test_copy_archive_pattern(cli_runner, datafiles):
    """Test copy_archives() command to ensure glob patterns are copied."""
    os.chdir(str(datafiles))
    workspace_dir = os.path.join(str(datafiles), 'workspace')
    stage_dir = str(datafiles.mkdir("stage_archive"))

    os.chdir(stage_dir)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'copy-archives', workspace_dir, '**/*.txt'],
        obj={})
    assert result.exit_code == 0

    assert os.path.exists(os.path.join(stage_dir, 'test.log'))
    assert os.path.exists(os.path.join(stage_dir, 'abc.txt'))
    assert not os.path.exists(os.path.join(stage_dir, 'dependencies.log'))
    assert os.path.exists(os.path.join(
        stage_dir, 'aaa', 'aaa-cert', 'target', 'surefire-reports',
        'org.opendaylight.aaa.cert.test.AaaCertMdsalProviderTest-output.txt'))

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'deploy'),
    )
def test_deploy_archive(cli_runner, datafiles, responses):
    """Test deploy_archives() command for expected upload cases."""
    os.chdir(str(datafiles))
    workspace_dir = os.path.join(str(datafiles), 'workspace')

    # Test successful upload
    url = 'https://nexus.example.org/service/local/repositories/logs/content-compressed'
    responses.add(responses.POST, '{}/test/path/abc'.format(url),
                  json=None, status=201)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'archives', 'https://nexus.example.org', 'test/path/abc', workspace_dir],
        obj={})
    assert result.exit_code == 0

    # Test failed upload
    url = 'https://nexus-fail.example.org/service/local/repositories/logs/content-compressed'
    responses.add(responses.POST, '{}/test/fail/path'.format(url),
                  status=404)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'archives', 'https://nexus-fail.example.org', 'test/fail/path', workspace_dir],
        obj={})
    assert result.exit_code == 1

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'deploy'),
    )
def test_deploy_logs(cli_runner, datafiles, responses):
    """Test deploy_logs() command for expected upload cases."""
    os.chdir(str(datafiles))
    workspace_dir = os.path.join(str(datafiles), 'workspace')

    # Test successful upload
    build_url = 'https://jenkins.example.org/job/builder-check-poms/204'
    nexus_url = 'https://nexus.example.org/service/local/repositories/logs/content-compressed'
    responses.add(responses.GET, '{}/consoleText'.format(build_url),
                  status=201)
    responses.add(responses.GET, '{}/timestamps?time=HH:mm:ss&appendLog'.format(build_url),
                  body='This is a console timestamped log.', status=201)
    responses.add(responses.POST, '{}/test/log/upload'.format(nexus_url), status=201)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'logs', 'https://nexus.example.org', 'test/log/upload', build_url],
        obj={})
    assert result.exit_code == 0

@pytest.mark.datafiles(
    os.path.join(FIXTURE_DIR, 'deploy'),
    )
def test_deploy_nexus_zip(cli_runner, datafiles, responses):
    os.chdir(str(datafiles))
    nexus_url = 'https://nexus.example.org'
    nexus_repo = 'test-repo'
    nexus_path = 'test/path'

    # Test success
    success_upload_url = '{}/service/local/repositories/{}/content-compressed/{}'.format(
        nexus_url,
        nexus_repo,
        nexus_path,
    )
    responses.add(responses.POST, success_upload_url,
                  status=201)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'nexus-zip', 'https://nexus.example.org', 'test-repo', 'test/path', 'zip-test-files/test.zip'],
        obj={})
    assert result.exit_code == 0

    # Test repository 404
    upload_404 = """<html>
  <head>
    <title>404 - Not Found</title>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>


    <link rel="icon" type="image/png" href="https://nexus.opendaylight.org/favicon.png">
    <!--[if IE]>
    <link rel="SHORTCUT ICON" href="https://nexus.opendaylight.org/favicon.ico"/>
    <![endif]-->

    <link rel="stylesheet" href="https://nexus.opendaylight.org/static/css/Sonatype-content.css?2.14.7-01" type="text/css" media="screen" title="no title" charset="utf-8">
  </head>
  <body>
    <h1>404 - Not Found</h1>
    <p>Repository with ID=&quot;logs2&quot; not found</p>
  </body>
</html>
"""
    upload_404_url = '{}/service/local/repositories/{}/content-compressed/{}'.format(
        nexus_url,
        'logs2',
        nexus_path,
    )
    responses.add(responses.POST, upload_404_url,
                  body=upload_404, status=404)
    result = cli_runner.invoke(
        cli.cli,
        ['--debug', 'deploy', 'nexus-zip', 'https://nexus.example.org', 'logs2', 'test/path', 'zip-test-files/test.zip'],
        obj={})
    assert result.exit_code == 1

def mocked_log_error(msg1=None, msg2=None):
    """Mock local_log_error_and_exit function.
    This function is modified to simply raise an Exception.
    The original will print msg1 & msg2, then call sys.exit(1)."""
    if 'Could not connect to URL:' in msg1:
        raise ValueError('connection_error')
    if 'Invalid URL:' in msg1:
        raise ValueError('invalid_url')
    if 'Not valid URL:' in msg1:
        raise ValueError('missing_schema')
    raise ValueError('fail')


def mocked_requests_post(*args, **kwargs):
    """Mock requests.post function."""
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json_data

        def json(self):
            return self.json_data

    if 'connection.error.test' in args[0]:
        raise requests.exceptions.ConnectionError
    if 'invalid.url.test' in args[0]:
        raise requests.exceptions.InvalidURL
    if 'missing.schema.test' in args[0]:
        raise requests.exceptions.MissingSchema
    return MockResponse(None, 404)


def test_local_request_post(mocker):
    """Test local_request_post."""
    mocker.patch('requests.post', side_effect=mocked_requests_post)
    mocker.patch('lftools.deploy._log_error_and_exit', side_effect=mocked_log_error)

    xml_doc='''
        <promoteRequest>
            <data>
                <stagedRepositoryId>test1-1027</stagedRepositoryId>
                <description>Close staging repository.</description>
            </data>
        </promoteRequest>
        '''
    with pytest.raises(ValueError) as excinfo:
        deploy_sys._request_post('connection.error.test', xml_doc, "{'Content-Type': 'application/xml'}")
    assert 'connection_error' in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        deploy_sys._request_post('invalid.url.test:8081nexus', xml_doc, "{'Content-Type': 'application/xml'}")
    assert 'invalid_url' in str(excinfo.value)
    with pytest.raises(ValueError) as excinfo:
        deploy_sys._request_post('http:/missing.schema.test:8081nexus', xml_doc, "{'Content-Type': 'application/xml'}")
    assert 'missing_schema' in str(excinfo.value)
