import json
import os
import stat

SESSION_DIR = os.path.expanduser("~/.config/bcextr")
SESSION_PATH = os.path.join(SESSION_DIR, "session.json")


def save_session(username: str, identity_cookie: str) -> None:
    os.makedirs(SESSION_DIR, exist_ok=True)
    with open(SESSION_PATH, "w") as fh:
        json.dump({"username": username, "identity_cookie": identity_cookie}, fh)
    os.chmod(SESSION_PATH, stat.S_IRUSR | stat.S_IWUSR)


def load_session() -> dict:
    if not os.path.exists(SESSION_PATH):
        raise FileNotFoundError(
            f"No session found at {SESSION_PATH}. Run `bcextr api login` first."
        )
    with open(SESSION_PATH) as fh:
        return json.load(fh)
