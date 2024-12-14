# Systogony

Automation for self-hosting, home router and desktop systems

## Getting started


#### bootstrap.yml

The starting point for a newly kicked system is the playbook `bootstrap.yml`. It uses a default or temporary user for initial access to create a proper automation user and lock down SSHD. The last step of this can break access, so it's just meant to be run once.

#### main.yml

This is the main playbook, meant to do setup for all hosts and all services and be regularly rerun.

## Variables and private directories

I'm not putting some details in the repo for security and privacy reasons. These things go in `group_vars`, `host_vars`, and `private` directories that I'll put dummy versions of in the repo later.

## Conventions

### User creation

Roles at `roles/*/user` create and configure users by calling each other, and `roles/base/user` should be the only site of user creation.
