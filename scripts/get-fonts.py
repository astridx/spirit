#!/usr/bin/env python3
'''This script is designed to load fonts
for rendering maps. It differs from the usual scripts to do this in that it is
designed to take its configuration from a file rather than be a series of shell
commands.

Some implicit assumptions are
- Time spent querying (rendering) the data is more valuable than the one-time
    cost of loading it
- The script will not be running multiple times in parallel. This is not
    normally likely because the script is likely to be called daily or less,
    not minutely.
- Usage patterns will be similar to typical map rendering
'''

import yaml
from urllib.parse import urlparse
import os
import argparse
import shutil

# modules for getting data
import zipfile
import requests
import io

# modules for converting
import subprocess

import logging
from datetime import datetime

class Downloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'get-fonts.py/spirit'})

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.session.close()

    def _download(self, url, headers=None):
        if url.startswith('file://'):
            filename = url[7:]
            if headers and 'If-Modified-Since' in headers:
                if str(os.path.getmtime(filename)) == headers['If-Modified-Since']:
                    return DownloadResult(status_code = requests.codes.not_modified)
            with open(filename, 'rb') as fp:
                return DownloadResult(status_code = 200, content = fp.read(),
                                      last_modified = str(os.fstat(fp.fileno()).st_mtime))
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        return DownloadResult(status_code = response.status_code, content = response.content,
                              last_modified = response.headers.get('Last-Modified', None))

    def download(self, url, name, opts, fonts_dir, filename, filename_lastmod):
        if os.path.exists(filename) and os.path.exists(filename_lastmod):
            with open(filename_lastmod, 'r') as fp:
                lastmod_cache = fp.read()
            with open(filename, 'rb') as fp:
                cached_data = DownloadResult(status_code = 200, content = fp.read(),
                                             last_modified = lastmod_cache)
        else:
            cached_data = None
            lastmod_cache = None

        result = None
        # Variable used to tell if we downloaded something
        download_happened = False

        if opts.no_update and (cached_data):
            # It is ok if this returns None, since we are opts.no-update
            result = cached_data
        else:
            if opts.force:
                headers = {}
            else:
                # If not exist, value will be None and it will have the same effect as not having If-Modified-Since set
                headers = {'If-Modified-Since': lastmod_cache}

            response = self._download(url, headers)
            # Check status codes
            if response.status_code == requests.codes.ok:
                logging.info("  Download complete ({} bytes)".format(len(response.content)))
                download_happened = True
                # Write - we need to write because fontnik needs a path
                with open(filename, 'wb') as fp:
                    fp.write(response.content)
                with open(filename_lastmod, 'w') as fp:
                    fp.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                result = response
            elif response.status_code == requests.codes.not_modified:
                result = cached_data
            else:
                logging.critical("  Unexpected response code ({}".format(response.status_code))
                logging.critical("  Content {} was not downloaded".format(name))
                return None

        return result


class DownloadResult:
    def __init__(self, status_code, content=None, last_modified=None):
        self.status_code = status_code
        self.content = content
        self.last_modified = last_modified


def main():
    # parse options
    parser = argparse.ArgumentParser(
        description="Load and convert fonts")

    parser.add_argument("-f", "--force", action="store_true",
                        help="Download and import new data, even if not required.")
    parser.add_argument("--no-update", action="store_true",
                        help="Don't download newer data than what is locally available (in cache). Overridden by --force")

    parser.add_argument("--delete-cache", action="store_true",
                        help="Execute as usual, but delete cached data")

    parser.add_argument("-c", "--config", action="store", default="fonts.yml",
                        help="Name of configuration file (default fonts.yml)")
    parser.add_argument("-D", "--data", action="store",
                        help="Override data download directory")

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Be more verbose. Overrides -q")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Only report serious problems")

    opts = parser.parse_args()

    if opts.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif opts.quiet:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    if opts.force and opts.no_update:
        opts.no_update = False
        logging.warning("Force (-f) flag overrides --no-update flag")

    logging.info("Starting load of fonts")

    with open(opts.config) as config_file:
        config = yaml.safe_load(config_file)
        fonts_dir = opts.data or config["settings"]["fonts_dir"]
        os.makedirs(fonts_dir, exist_ok=True)

        with Downloader() as d:

            for name, source in config["sources"].items():
                filename = os.path.join(fonts_dir, os.path.basename(urlparse(source["url"]).path))
                filename_lastmod = filename + '.lastmod'

                # This will fetch data needed for convert
                download = d.download(source["url"], name, opts, fonts_dir, filename, filename_lastmod)

                # Check if there is need to convert
                if download == None and (not opts.force):
                    logging.info("  {} did not require updating".format(name))
                    continue

                workingdir = os.path.join(fonts_dir, name)
                shutil.rmtree(workingdir, ignore_errors=True)
                os.makedirs(workingdir, exist_ok=True)
                
                command = ['npx', '-p', 'fontnik', 'build-glyphs', filename, workingdir]
                subprocess.run(command, check=True)

                if "archive" in source and source["archive"]["format"] == "zip":
                    logging.info("  Decompressing file")
                    zip = zipfile.ZipFile(io.BytesIO(download.content))
                    for member in source["archive"]["files"]:
                        zip.extract(member, workingdir)

                logging.info("  Import complete")

                if opts.delete_cache:
                    try:
                        os.remove(filename)
                        os.remove(filename_lastmod)
                        logging.info("  Cache deleted")
                    except FileNotFoundError:
                        pass


if __name__ == '__main__':
    main()
