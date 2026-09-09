# Third-party software and model notices

MV Analyzer source code is licensed under Apache-2.0. Dependencies remain under
their own licenses. This file lists direct/runtime dependencies relevant to the
project; it is not a replacement for the license files shipped by those projects.

## Python runtime

| Dependency | Role | License |
|---|---|---|
| yt-dlp | metadata/media acquisition | Unlicense for the Git repository and PyPI source/wheel |
| PySceneDetect | scene detection | BSD-3-Clause |
| opencv-python-headless / OpenCV | image/video processing | Apache-2.0 |
| librosa | audio analysis | ISC |
| NumPy | numerical computing | BSD-3-Clause and bundled permissive components |
| SciPy | scientific computing | BSD-3-Clause; binary wheels may bundle separately licensed runtime components |
| Matplotlib | research plots | Matplotlib License (PSF/BSD-style) plus separately licensed bundled assets |
| DuckDB | local analytical index | MIT |
| jsonschema | report validation | MIT |

## Optional local GPU / model stack

| Dependency / model | Role | License |
|---|---|---|
| Demucs | source separation | MIT |
| faster-whisper | local ASR runtime | MIT |
| Qwen2.5-VL-7B-Instruct | local VLM baseline | Apache-2.0 |

Model weights are **not distributed in this repository**. Users obtain models
separately and must follow the corresponding model/runtime terms.

## Web application

React, React DOM, React Router, Three.js, Vite, Vitest, Ajv, jsdom, and Testing
Library packages used directly by the Web application are MIT-licensed. TypeScript
and Playwright are Apache-2.0 licensed. Their transitive dependencies retain their
own licenses.

## OpenMontage interoperability boundary

OpenMontage is GNU AGPLv3. MV Analyzer does not declare it as a package dependency,
import its modules, vendor its source files, or include an OpenMontage runtime.
`mv_analyzer/blueprint_export.py` is an interoperability adapter that emits a JSON
shape consumed by a separate external workflow. Before any public release, changes
to this boundary should be reviewed for copied upstream source, not merely imports.

## FFmpeg

FFmpeg is invoked as an external system tool. FFmpeg builds can have different
license configurations depending on enabled components; distributors of bundled
FFmpeg binaries are responsible for the license obligations of that binary.
