#!/usr/bin/env python3
'''This script is designed to load fonts.

Some implicit assumptions are
- Time spent querying (rendering) the data is more valuable than the one-time
    cost of loading it
- The script will not be running multiple times in parallel. This is not
    normally likely because the script is likely to be called daily or less,
    not minutely.
- Usage patterns will be similar to typical map rendering
'''

import logging
import argparse
import yaml
import os
import requests
from urllib.parse import urlparse




class Downloader:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'get-fonts.py/spirit'})

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.session.close()

    def _download(self, url, headers=None):
        logging.info("_download")
        logging.info(url)
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
        logging.info(url)
        return DownloadResult(status_code = response.status_code, content = response.content,
                              last_modified = response.headers.get('Last-Modified', None))

    def download(self, url, name, opts, data_dir):
        filename = os.path.join(data_dir, os.path.basename(urlparse(url).path))
        filename_lastmod = filename + '.lastmod'
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
        logging.info(filename)

        if (cached_data):
            # It is ok if this returns None, because for this to be None, 
            # we need to have something in table and therefore need not import (since we are opts.no-update)
            result = cached_data
        else:
            # If none of those 2 exist, value will be None and it will have the same effect as not having If-Modified-Since set
            headers = {'If-Modified-Since': lastmod_cache}

            response = self._download(url, headers)
            # Check status codes
            if response.status_code == requests.codes.ok:
                logging.info("  Download complete ({} bytes)".format(len(response.content)))
                download_happened = True
                result = response
            elif response.status_code == requests.codes.not_modified:
                # Now we need to figure out if our not modified data came from table or cache
                if os.path.exists(filename) and os.path.exists(filename_lastmod):
                    logging.info("  Cached file {} did not require updating".format(url))
                    result = cached_data
                else:
                    result = None
            else:
                logging.critical("  Unexpected response code ({}".format(response.status_code))
                logging.critical("  Content {} was not downloaded".format(name))
                return None



class DownloadResult:
    def __init__(self, status_code, content=None, last_modified=None):
        self.status_code = status_code
        self.content = content
        self.last_modified = last_modified





def main():
    # parse options
    parser = argparse.ArgumentParser(
        description="Get fonts")

    parser.add_argument("-c", "--config", action="store", default="fonts.yml",
                        help="Name of configuration file (default fonts.yml)")

    opts = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    logging.info("Starting download of fonts")

    with open(opts.config) as config_file:
        config = yaml.safe_load(config_file)
        fonts_dir = config["settings"]["fonts_dir"]
        os.makedirs(fonts_dir, exist_ok=True)

        with Downloader() as d: 
            for name, source in config["sources"].items():
                download = d.download(source["url"], name, opts, fonts_dir)






    logging.info("  Download complete")

if __name__ == '__main__':
    main()
