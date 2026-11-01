"""Create or remove a disposable PostgreSQL database for manual PR testing."""

import argparse
import re
import sys
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.config import Settings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "dispose"))
    parser.add_argument("pr_number", help="GitHub pull request number")
    args = parser.parse_args()
    if not re.fullmatch(r"[1-9][0-9]*", args.pr_number):
        parser.error("PR number must be a positive integer without leading zeroes")
    settings = Settings()
    url = make_url(settings.database_url)
    if not url.drivername.startswith("postgresql") or not url.database:
        parser.error("PRINT_JOB_MANAGER_DATABASE_URL must name a PostgreSQL database")
    source = url.database
    if source.endswith("_pr_clone") or re.search(r"_pr_[1-9][0-9]*$", source):
        parser.error("Configure the original database URL, not a clone URL")
    target = f"{source}_pr_{args.pr_number}"
    if len(target.encode("utf-8")) > 63:
        parser.error("Clone database name exceeds PostgreSQL's 63-byte limit")

    admin_url = make_url(settings.admin_database_url) if settings.admin_database_url else url
    if (admin_url.host, admin_url.port or 5432) != (url.host, url.port or 5432):
        parser.error("The admin and application URLs must use the same host and port")
    engine = sa.create_engine(admin_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            quote = connection.dialect.identifier_preparer.quote_identifier
            exists = connection.execute(
                sa.text("SELECT EXISTS (SELECT 1 FROM pg_database WHERE datname = :name)"),
                {"name": target},
            ).scalar_one()
            if args.action == "dispose":
                if not exists:
                    print(f"Clone {target!r} does not exist; nothing to dispose.")
                    return 0
                print(f"This permanently deletes database {target!r} and all its data.")
                if input(f"Type {target} to confirm: ") != target:
                    print("Cancelled; no database was deleted.")
                    return 1
                connection.exec_driver_sql(f"DROP DATABASE {quote(target)}")
                print(f"Deleted database {target!r}. Artifact files were not touched.")
                return 0

            if exists:
                print(f"Clone {target!r} already exists; refusing to overwrite it.")
                return 1
            row = connection.execute(
                sa.text("""
                    SELECT pg_get_userbyid(datdba) AS owner
                    FROM pg_database WHERE datname = :name
                """),
                {"name": source},
            ).one()
            can_set_owner = connection.execute(
                sa.text("SELECT pg_has_role(current_user, :owner, 'SET')"),
                {"owner": row.owner},
            ).scalar_one()
            if not can_set_owner:
                print(
                    f"The current role cannot assign database owner {row.owner!r}. "
                    "Set PRINT_JOB_MANAGER_ADMIN_DATABASE_URL to a privileged role "
                    "on the same server (see backend/.env.example).",
                    file=sys.stderr,
                )
                return 1
            sessions = connection.execute(
                sa.text("SELECT count(*) FROM pg_stat_activity WHERE datname = :name"),
                {"name": source},
            ).scalar_one()
            if sessions:
                print(
                    f"Source database {source!r} has {sessions} active connection(s). "
                    "Disconnect the app and database clients, then retry.",
                    file=sys.stderr,
                )
                return 1
            grants = connection.execute(
                sa.text("""
                    SELECT CASE WHEN acl.grantee = 0 THEN NULL
                                ELSE pg_get_userbyid(acl.grantee) END AS grantee,
                           acl.privilege_type, acl.is_grantable
                    FROM pg_database d,
                         LATERAL aclexplode(COALESCE(d.datacl, acldefault('d', d.datdba))) acl
                    WHERE d.datname = :name AND acl.grantee <> d.datdba
                """),
                {"name": source},
            ).all()
            print(f"Cloning {source!r} to {target!r}; source connections must be closed.")
            connection.exec_driver_sql(
                f"CREATE DATABASE {quote(target)} WITH TEMPLATE {quote(source)} OWNER {quote(row.owner)}"
            )
            try:
                connection.exec_driver_sql(
                    f"REVOKE ALL PRIVILEGES ON DATABASE {quote(target)} FROM PUBLIC"
                )
                for grant in grants:
                    grantee = "PUBLIC" if grant.grantee is None else quote(grant.grantee)
                    grant_option = " WITH GRANT OPTION" if grant.is_grantable else ""
                    connection.exec_driver_sql(
                        f"GRANT {grant.privilege_type} ON DATABASE {quote(target)} TO {grantee}{grant_option}"
                    )
            except Exception:
                print(
                    f"Clone {target!r} was created, but copying database grants failed. "
                    "It may be incomplete; inspect or dispose of it before retrying.",
                    file=sys.stderr,
                )
                raise
            print(f"Created clone {target!r}. Set PRINT_JOB_MANAGER_DATABASE_URL to:")
            print(url.set(database=target).render_as_string(hide_password=True))
            print("Use the original password; copy artifact storage separately.")
            return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
