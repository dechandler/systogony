# Systogony

Automation for self-hosting, home router and desktop systems

# Conventions

### User creation

Roles at `roles/*/user` create and configure users by calling each other, and `roles/base/user` should be the only site of user creation.
