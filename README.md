# Unraid Discord Bot
 Basic Unraid command line controls from Discord


All the user variables that need to be changed before use need to be in a file called '.env'.

The .env file should look like this:
DISCORD_TOKEN=<Discord Token>
DISCORD_GUILD=<Server Name>
CHANNEL_GENERAL=<Channel ID>
MAC_ADDRESS=<Mac address for sending wake on LAN request to.>
IP_ADDRESS=<IP address for the wake on LAN PC.>
POWER_CHECK_TIMEOUT=<Number of seconds to wait before assuming the PC didn't wake up.>