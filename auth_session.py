"""In-process authentication context. Never populated from command-line arguments."""
_session = None

def start_session(username, role):
    global _session
    if _session is not None:
        raise RuntimeError('Session already established')
    if not username or role not in ('admin','cashier'):
        raise ValueError('Invalid authentication context')
    _session = {'username': username, 'role': role}

def current_session():
    return None if _session is None else dict(_session)
