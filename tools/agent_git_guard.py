#!/usr/bin/env python3
"""Git pre-push guard. An accident barrier, not a security boundary against shell access."""
import sys

def permitted(lines):
    for line in lines:
        parts = line.split()
        if len(parts) != 4:
            return False
        if not parts[2].startswith('refs/heads/agent/'):
            return False
        if set(parts[1]) == {'0'}:  # branch deletion
            return False
    return True

if __name__ == '__main__':
    if not permitted(sys.stdin):
        print('NOVA: pushes may only target agent/* work branches; deletion is denied.', file=sys.stderr)
        sys.exit(1)
