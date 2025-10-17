# Admin Account Creation Guide

## Overview

The `novalabs-admin` command provides an interactive way to create the first admin user for your NovaLabs Hub installation. It includes validation and prevents duplicate admin creation.

## Command Syntax

```bash
novalabs-admin [OPTIONS]
```

### Options

- `--force`, `-f`: Replace the existing admin user (requires confirmation)

### Examples

```bash
# Create first admin (interactive)
novalabs-admin

# Replace existing admin
novalabs-admin --force

# Short form
novalabs-admin -f
```

## Usage

### First-time Setup

When no admin exists in the database, the command will prompt you interactively:

```bash
$ novalabs-admin

============================================================
NovaLabs Hub - Admin Account Creation
============================================================

No admin user found. Let's create one.

Email address: admin@example.com
First name: John
Last name: Doe
Institution (optional): Villanova University
Password: 
Confirm password: 

============================================================
Admin user created successfully!
Email: admin@example.com
Name: John Doe
Institution: Villanova University
============================================================

You can now start the hub server with: novalabs-hub
```

### When Admin Already Exists

If an admin user already exists, the command will inform you:

```bash
$ novalabs-admin

An admin user already exists in the database.
Current admin: admin@example.com

To replace the existing admin, use: novalabs-admin --force
```

### Replacing an Existing Admin

To replace the current admin user, use the `--force` or `-f` flag:

```bash
$ novalabs-admin --force

Replacing existing admin user:
Email: admin@example.com
Name: John Doe

Authentication required to replace admin user
Enter password for admin@example.com: ********
Password verified

Are you sure you want to delete this admin? (yes/no): yes
Existing admin deleted.

============================================================
NovaLabs Hub - Admin Account Creation
============================================================

No admin user found. Let's create one.

Email address: newadmin@example.com
...
```

**Security features:**

- Requires current admin password verification
- Requires explicit confirmation ("yes") before deletion
- Shows current admin details before deletion
- Can be cancelled at any point
- Supports both `--force` and `-f` flags

## Validation Rules

The command validates all inputs:

### Email

- **Required**
- Must contain an `@` symbol
- Will loop until a valid email is provided

### First Name

- **Required**
- Cannot be empty
- Will loop until provided

### Last Name

- **Required**
- Cannot be empty
- Will loop until provided

### Institution

- **Optional**
- Can be left blank by pressing Enter

### Password

- **Required**
- Minimum 8 characters
- Uses `getpass` for secure input (no echo)
- Must be confirmed by re-entering
- Will loop until:
  - Password is at least 8 characters
  - Both entries match

## Features

### Security

- Passwords are hidden during input (no echo)
- Password confirmation prevents typos
- Minimum password length enforced (8 characters)
- Passwords are hashed with bcrypt before storage

### User Experience

- Clear prompts with validation messages
- Graceful handling of Ctrl+C (KeyboardInterrupt)
- Professional formatting with separators

### Safety

- Checks for existing admin before prompting
- Prevents accidental duplicate admin creation
- Database is automatically initialized if needed
- Comprehensive error handling

## Error Handling

The script handles various error scenarios:

### Duplicate Email

```bash
Error: User with email admin@example.com already exists
```

### Invalid Input
```ascii
Please enter a valid email address
First name cannot be empty
Password must be at least 8 characters long
Passwords do not match
```

### User Cancellation

```ascii
^C
Admin creation cancelled.
```

### Unexpected Errors

```ascii
Unexpected error: <error details>
```

## Alternative Methods

### Python Module

```bash
python -m hub.create_admin
```

### Direct Import (for automation/testing)

```python
from hub.create_admin import main
main()
```

## After Creation

Once the admin user is created:

1. **Start the server:**

   ```bash
   novalabs-hub
   ```

2. **Seed sample labs (for testing only!):**
   ```bash
   novalabs-seed
   ```

3. **Login via API:**

   ```bash
   curl -X POST "http://localhost:8100/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin@example.com&password=your-password"
   ```

4. **Access the API docs:**

   - Interactive: http://localhost:8100/docs
   - ReDoc: http://localhost:8100/redoc

## Creating Additional Admins

To create additional admin users after the first one:

1. Use the API with an existing admin token
2. Or use the web interface (when available)

The `novalabs-admin` command only creates the **first** admin user to bootstrap the system.

## Troubleshooting

### Command not found

Make sure the package is installed:

```bash
pip install -e .
```

### Database locked

Ensure no other processes are using the database:

```bash
ps aux | grep novalabs
```

### Permission denied

Check file permissions on the `hub/data/` directory:

```bash
ls -la hub/data/
```

## Implementation Details

The script performs these steps:

1. Initialize the database (creates tables if needed)
2. Check if an admin user exists
3. If no admin:
   - Prompt for all required fields
   - Validate inputs with loops
   - Confirm password matches
   - Create user with bcrypt-hashed password
   - Set role to "admin"
4. Display success message with details
5. Suggest next steps

## Code Location

- Script: `hub/create_admin.py`
- Entry point: `[project.scripts]` in `pyproject.toml`
- Functions:
  - `check_existing_admin()` - Check for existing admin users
  - `prompt_admin_details()` - Interactive prompt for user details
  - `main()` - Main execution function
