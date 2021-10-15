# Serial connections don't have a standard way of setting terminal geometry. The assumed geometry is often 80x23 or 80x24 (terminals with zero to two status lines).
# Once you're logged in, you can set your preferred geometry via the shell, using something like
stty rows 50 cols 400
