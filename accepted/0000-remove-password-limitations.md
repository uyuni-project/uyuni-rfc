- Feature Name: remove_password_limitations
- Start Date: 2023-07-21

# Summary
Remove password limitations when setting up UYUNI with YAST

Today we give users, strict limitations when choosing a password during UYUNI setup in YAST. We ask not to use spaces, $ or ! and we suggest that a 7 characters password is the lower bound for a good choice.
This suggests to skilled users that we store passwords somewhere in clear text and that we use them in shell scripts. This can also give advice to an attacker to find weaknesses in customer installations.

I suggest moving over from these limitations, allowing passphrases over passwords with no restriction from characters a user would choose.

# Motivation
Improve security posture of UYUNI / SUSE Manager product and give more confidence to customer that we handle secrets in a secure way. 

Using passphrase over password will give people a more secure product when dealing with authentication issues. 

# Detailed design
I can assume YAST saves password in configuration files used also in shell script for server management.

My suggestion is to store all secrets in the database in an encrypted form (bcrypt or salted SHA 512|256) is good. 
We will modify the SUMA login API and shell scripts to get a session token using the same mechanism as the WEB UI. Maybe a good idea is to translate all scripts from shell to python so to have requests library doing all work the under the hoods.

# Drawbacks

We had to rework all surrounding scripts and this can introduce regressions.

# Alternatives
We can stay as-is, since the actual scenario works, however this will make our product to sound as a non mature solutions for enterprises in 2023.

# Unresolved questions
None at the moment