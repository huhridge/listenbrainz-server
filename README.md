<h1 align="center">
  <br>
  <a href="https://listenbrainz.org"><img src="https://github.com/metabrainz/metabrainz-logos/blob/master/logos/ListenBrainz/SVG/ListenBrainz_logo.svg" alt="ListenBrainz"></a>
</h1>
<h4 align="center">Server for the ListenBrainz project</h4>
<p align="center">
    <a href="https://github.com/metabrainz/listenbrainz-server/commits/master">
    <img src="https://img.shields.io/github/last-commit/metabrainz/listenbrainz-server.svg?style=flat-square&logo=github&logoColor=white"
         alt="GitHub last commit"></a>
    <a href="https://github.com/metabrainz/listenbrainz-server/issues">
    <img src="https://img.shields.io/github/issues-raw/metabrainz/listenbrainz-server.svg?style=flat-square&logo=github&logoColor=white"
         alt="GitHub issues"></a>
    <a href="https://github.com/metabrainz/metabrainz.org/pulls">
    <img src="https://img.shields.io/github/issues-pr-raw/metabrainz/listenbrainz-server?style=flat-square&logo=github&logoColor=white"
         alt="GitHub pull requests"></a>
</p>
<p align="center">
  <a href="https://listenbrainz.org">Website</a> •
  <a href="https://listenbrainz.readthedocs.io">Documentation</a> •
  <a href="https://tickets.metabrainz.org/projects/LB/issues">Bug tracker</a>
</p>

---

## About

ListenBrainz keeps tracks of what music you listen to and
provides you with insights into your listening habits. We're
completely open-source and publish our data as open data.

You can use ListenBrainz to track your music listening habits and
share your taste with others using our visualizations. We also have an
[API](https://listenbrainz.readthedocs.io/en/production/dev/api/)
if you want to do more with our data.

ListenBrainz is operated by the [MetaBrainz Foundation](https://metabrainz.org)
which has a long-standing history of curating, protecting and making music data available to the
public.

For more information about this project and its goals, look at our
[website](https://listenbrainz.org/), specifically the
[goals page](https://listenbrainz.org/goals).

Changes and other important announcements about the ListenBrainz services will be
announced on [our blog](https://blog.metabrainz.org/). If you start using our
services in any production system, we urge you to follow the blog!

## Commercial use

All of our data is available for commercial use. You can find out more about our
[commercial use support tiers](https://metabrainz.org/supporters/account-type) on 
the MetaBrainz site.

## Contributing

If you are interested in helping out, consider
[donating](https://metabrainz.org/donate) to the MetaBrainz Foundation.

If you are interested in contributing code or documentation,
please have a look at the [issue tracker](https://tickets.metabrainz.org/browse/LB)
or come visit us in the #metabrainz IRC channel on irc.libera.chat.

## Development environment

These instructions help you get started with the development process.
Installation in a production environment may be different.

**Read the [development environment
documentation](https://listenbrainz.readthedocs.io/en/production/dev/devel-env.html "Setting up a development environment - ListenBrainz documentation")**

In order to work with Spark, you'll have to setup the Spark development environment.
Read the [documentation](https://listenbrainz.readthedocs.io/en/production/dev/spark-devel-env.html).

## Documentation

Full documentation for the ListenBrainz API is available at
[listenbrainz.readthedocs.org](https://listenbrainz.readthedocs.org). You can
also build the documentation locally:

    cd listenbrainz-server/docs
    pip install -r requirements.txt
    make clean html
    
## Pushing test images using Github Actions

1. Go to Actions -> Push deployment image or click [here](https://github.com/metabrainz/listenbrainz-server/actions/workflows/push-dev-image.yml).
2. Select the branch and enter the docker image tag (version).
![Screenshot (54)](https://user-images.githubusercontent.com/27751938/136417112-20184ff0-3140-425f-89fe-bae625b820a3.png)
3. Click on Run Workflow.
4. The image will be built and pushed to Docker Hub with the desired tag.
5. To monitor the status of the build, wait for the worflow run to appear. You may need to wait for a few seconds and reload the page.
![Screenshot (55)](https://user-images.githubusercontent.com/27751938/136417424-997539aa-79ab-4425-8edd-e8f2cfdd482c.png)

## License Notice

```
listenbrainz-server - Server for the ListenBrainz project

Copyright (C) 2017 MetaBrainz Foundation Inc.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
```
