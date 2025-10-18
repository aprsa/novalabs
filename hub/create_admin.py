import getpass
import sys
from sqlmodel import Session, select
from .database import engine, init_db
from .auth import create_user, verify_password
from .models import User


def get_existing_admin(session: Session) -> User | None:
    """Get the existing admin user if one exists"""
    statement = select(User).where(User.role == "admin")
    return session.exec(statement).first()


def delete_admin(session: Session, admin: User) -> None:
    """Delete an admin user from the database"""
    session.delete(admin)
    session.commit()


def prompt_admin_details() -> dict:
    """Prompt user for admin account details"""
    print("\n" + "=" * 60)
    print("NovaLabs Hub - Admin Account Creation")
    print("=" * 60)
    print("\nNo admin user found. Let's create one.\n")
    
    # Email
    while True:
        email = input("Email address: ").strip()
        if email and "@" in email:
            break
        print("❌ Please enter a valid email address")
    
    # First name
    while True:
        first_name = input("First name: ").strip()
        if first_name:
            break
        print("❌ First name cannot be empty")
    
    # Last name
    while True:
        last_name = input("Last name: ").strip()
        if last_name:
            break
        print("❌ Last name cannot be empty")
    
    # Institution (optional)
    institution = input("Institution (optional): ").strip() or None
    
    # Password
    while True:
        password = getpass.getpass("Password: ")
        if len(password) < 8:
            print("❌ Password must be at least 8 characters long")
            continue
        password_confirm = getpass.getpass("Confirm password: ")
        if password == password_confirm:
            break
        print("❌ Passwords do not match")
    
    return {
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "institution": institution,
        "password": password
    }


def verify_admin_password(admin: User) -> bool:
    """Verify admin password before allowing replacement"""
    print("\nAuthentication required to replace admin user")
    password = getpass.getpass(f"Enter password for {admin.email}: ")

    if verify_password(password, admin.hashed_password):
        return True

    print("Incorrect password.")
    return False


def main():
    """Entry point for creating admin user"""
    # Check for --force flag
    force = '--force' in sys.argv or '-f' in sys.argv

    # Initialize database
    init_db()

    with Session(engine) as session:
        # Check if admin already exists
        existing_admin = get_existing_admin(session)

        if existing_admin and not force:
            print("\nAn admin user already exists in the database.")
            print(f"Current admin: {existing_admin.email}")
            print("\nTo replace the existing admin, use: novalabs-admin --force")
            return

        if existing_admin and force:
            print("\nReplacing existing admin user:")
            print(f"Email: {existing_admin.email}")
            print(f"Name: {existing_admin.first_name} {existing_admin.last_name}")

            # Verify admin password
            if not verify_admin_password(existing_admin):
                print("\nAuthentication failed. Admin replacement cancelled.")
                return

            # Confirm deletion
            confirm = input("\nAre you sure you want to delete this admin? (yes/no): ").strip().lower()
            if confirm != 'yes':
                print("\nAdmin replacement cancelled.")
                return

            delete_admin(session, existing_admin)
            print("Existing admin deleted.\n")

        # Prompt for admin details
        try:
            details = prompt_admin_details()

            # Create admin user
            admin = create_user(
                session,
                email=details["email"],
                password=details["password"],
                first_name=details["first_name"],
                last_name=details["last_name"],
                role="admin",
                institution=details["institution"]
            )

            print("\n" + "=" * 60)
            print("Admin user created successfully!")
            print(f"  Email: {admin.email}")
            print(f"  Name: {admin.first_name} {admin.last_name}")
            if admin.institution:
                print(f"  Institution: {admin.institution}")
            print("=" * 60)
            print("\nYou can now start the hub server with: novalabs-hub")
            
        except ValueError as e:
            print(f"\n❌ Error: {e}")
        except KeyboardInterrupt:
            print("\n\n⚠ Admin creation cancelled.")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()
