#!/bin/bash

# This bash script calls isbg for spam checking for all the mail accounts
# in the provided list.

declare -A usernames

usernames=( ["user1"]="passwd1" \
	["user2"]="passwd2" \
	["user3"]="passwd3" \
       	["user4"]="passwd4" )

hostname="hostname"


for username in "${!usernames[@]}"
do
    python isbg.py --ssl --delete --expunge --imaphost $hostname \
    --imapuser $username --imappasswd ${usernames[$username]} \
    --imapinbox INBOX --spaminbox INBOX.Spam --noninteractive
done
