# Copy_Trade_Noti_Bot

This bot aims to post notifications on certain trader's trades in a consise manner.

The script pulls the raw data from an API then transforms the data to check against its current positions to determine to post it as a newly opened trade position, an added/reduced position or a closed position.

It then takes the transformed data and post it into telegram to notify the user
