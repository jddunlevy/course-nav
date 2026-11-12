"""Configuration: environment variables with a .env loader (AR14).

This module exists so that the session secret is not loaded as a side effect of
importing the optional reranker. `load_env` used to live in `rank_llm.py`, which
`app.py` imports; that worked while the only key was an API key, but a security
control must not depend on an optional feature module staying imported.
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Overridable so a caller can point at a different file, or at none: the boot
# refusal below cannot be exercised while a developer's own .env is sitting
# next to the module, because that file IS a configured secret.
ENV_FILE = os.environ.get("NAVIGATOR_ENV_FILE") or os.path.join(HERE, ".env")

# Refused outright. A prototype that boots on a shipped default is the failure
# mode this check exists to prevent (Story 1.5, AC 5).
PLACEHOLDER_SECRETS = {
    "", "dev", "development", "change-me", "changeme", "secret", "default",
    "test", "password", "your-secret-here", "replace-me",
}

SECRET_ENV = "NAVIGATOR_SECRET_KEY"


def load_env(path=ENV_FILE):
    """Read KEY=value lines from a gitignored .env into os.environ.

    Env vars set in a shell do not survive between separate invocations, and on
    Windows `setx` needs a restart before running processes see it. A file next
    to the app sidesteps both. Existing environment values always win.
    """
    if not os.path.exists(path):
        return []
    loaded = []
    # utf-8-sig, not utf-8: PowerShell's Out-File / Set-Content write a BOM,
    # which would otherwise become part of the first key name and never match.
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and not os.environ.get(key):
                os.environ[key] = value
                loaded.append(key)
    return loaded


class MissingSecret(SystemExit):
    """Raised at boot when no usable session secret is configured."""


def secret_key():
    """The Flask session secret, or refuse to start (Story 1.5, AC 5).

    Signed sessions are the whole of the access control added in Story 1.5. A
    default secret is a forgeable session, so there is no safe fallback value to
    pick -- the only correct behaviour is to stop. The message says how to fix
    it, because a prototype that dies without saying why sends the next person
    looking for the switch that turns the check off.
    """
    value = (os.environ.get(SECRET_ENV) or "").strip()
    if value.lower() in PLACEHOLDER_SECRETS:
        raise MissingSecret(
            "{} is not set to a real value.\n"
            "\n"
            "Sessions are signed with it; on a default or empty secret anyone can\n"
            "forge one, so the application refuses to start (Story 1.5, AC 5).\n"
            "\n"
            "Generate one and put it in .env next to app.py (.env is gitignored):\n"
            '    python -c "import secrets; print(\'{}=\' + secrets.token_hex(32))" >> .env\n'
            .format(SECRET_ENV, SECRET_ENV))
    if len(value) < 32:
        raise MissingSecret(
            "{} is shorter than 32 characters. Use a generated value:\n"
            '    python -c "import secrets; print(\'{}=\' + secrets.token_hex(32))" >> .env\n'
            .format(SECRET_ENV, SECRET_ENV))
    return value


load_env()
