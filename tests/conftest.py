"""Settings every test process shares."""

import os

# LiteLLM fetches its model map from the internet when it is first loaded unless told otherwise: the tests, as the
# worker of the installation, use the map bundled with the version in uv.lock (ADR 0148).
os.environ.setdefault("LITELLM_OFFLINE_MODE", "true")
