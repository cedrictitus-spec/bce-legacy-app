"""Create demo accounts only in an empty lab database."""

import sys
import warnings
from getpass import GetPassWarning, getpass


def main():
    if not sys.stdin.isatty():
        raise SystemExit("Run this script in an interactive terminal.")
    warnings.simplefilter("error", GetPassWarning)

    from app import app, db, User

    with app.app_context():
        db.create_all()
        if User.query.first() is not None:
            raise SystemExit("Stopped: users already exist. No users were changed.")

        users = []
        for username, role in (
            ("admin", "admin"),
            ("security_manager", "manager"),
            ("staff", "user"),
        ):
            password = getpass(f"New password for {username}: ")
            confirmation = getpass("Confirm password: ")
            if not password or password != confirmation:
                raise SystemExit("Passwords must be nonempty and match. No users were added.")

            user = User(username=username, role=role)
            user.set_password(password)
            users.append(user)

        try:
            db.session.add_all(users)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise SystemExit("Could not create demo users. Changes were rolled back.") from None

        print("Created admin, security_manager, and staff. Passwords are not displayed.")


if __name__ == "__main__":
    main()
