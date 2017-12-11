<!--
Copyright 2017 IBM Corp.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->
# Versioning scheme

The library uses semantic versioning compliant with PEP440 in the form `MAJOR.MINOR.PATCH`, as explained in [Semanic Versioning](https://semver.org).
In summary, this means:

- `MAJOR` gets incremented when backwards incompatible API changes are introduced;
- `MINOR` gets incremented when backwards compatible API changes are introduced;
- `PATCH` gets incremented when fixes in a backwards compatible way are implemented.

As of today since the library is still in early development phase, `MAJOR=0`. That means the API can still change frequently.

This is how the version is determined for a given commit:

- if commit matches a release tag: `{release_tag}`
- if commit matches a release tag and there are local changes: `{release_tag}.dev0+g{commit_id}.dirty`
- if commit is after a release tag: `{release_tag}.post{commit_qty}.dev0+g{commit_id}`
- if commit is after a release tag and there are local changes: `{release_tag}.post{commit_qty}.dev0+g{commit_id}.dirty`
- if there's no release tag: `0.post{commit_qty}.dev0+g{commit_id}`
- if there's no release tag and there are local changes: `0.post{commit_qty}.dev0+g{commit_id}.dirty`
- if git is not available to determine version (i.e. no `.git` directory): `0+unknown`

Note that `{commit_qty}` is the number of commits since the tagged commit.

Some examples:

- commit matching release tag 1.1.0: `1.1.0`
- two commits after the release tag: `1.1.0.post2.dev0+c18ff82d`
- two commits after the release tag with local changes: `1.1.0.post2.dev0+c18ff82d.dirty`
