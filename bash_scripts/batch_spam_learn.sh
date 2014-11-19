#!/bin/bash

# This bash script calls isbg for spam learning for all the mail
# accounts in the provided list.

declare -A usernames

usernames=( ["user1"]="passwd1" \
	["user2"]="passwd2" \
	["user3"]="passwd3" \
       	["user4"]="passwd4" )

hostname="hostname"


for username in "${!usernames[@]}"
do
    python isbg.py --ssl --teachonly --imaphost $hostname \
    --imapuser $username --imappasswd ${usernames[$username]} \
    --learnhambox INBOX --learnspambox INBOX.Spam --noninteractive
done
