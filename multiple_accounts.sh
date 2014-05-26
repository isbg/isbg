#! /bin/bash

usernames="user1 user2 user3"

for username in $usernames
do
    isbg --ssl --delete --expunge --imaphost hostname --imapuser $username \
     --imapinbox mbox --spaminbox mbox --noninteractive
done

