import os
import discord
import subprocess
import asyncio

from threading import Thread
from dotenv import load_dotenv
from wakeonlan import send_magic_packet
from pythonping import ping
from time import sleep

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = int(os.getenv('CHANNEL_GENERAL'))
MAC = os.getenv('MAC_ADDRESS')
IP = os.getenv('IP_ADDRESS')
timeLimit = int(os.getenv('POWER_CHECK_TIMEOUT'))

client = discord.Client()

cancelWakeUp = False

@client.event
async def on_ready():
    print(f'{client.user.name} has connected.')
    # await SendMessage(f'{client.user.name} has connected.')
    pass

@client.event
async def on_message(message):
    message:discord.message.Message

    if message.author == client.user:
        return
    else:
        await RunCommand(message.content)


async def RunCommand(command):
    if command.lower().startswith('!') == False:
        return
    command:str
    global cancelWakeUp
    commandLower = command.lower()

    if "!wake" in commandLower:
        pcName = command.replace("!wake", "").strip()
        try:
            pcName = pcName.split("-t")[0].strip()
        except: pass

        waitTime = 0
        if "-t" in command:
            try:
                split = commandLower.split(" ")
                waitTime = round(float(split[split.index("-t")+1]))
            except: pass
        
        cancelWakeUp = False
        await WakeUp(pcName, waitTime)
    elif "!abort" in commandLower:
        cancelWakeUp = True
    elif "!shutdown" in commandLower:
        pcName = command.replace("!shutdown", "").strip()
        force = False
        if "-f" in pcName or "-F" in pcName:
            force = True
            pcName = pcName.replace("-f", "").replace("-F", "").strip()

        await Shutdown(pcName, force)
    elif "!reboot" in commandLower:
        pcName = command.replace("!reboot", "").strip()
        await Reboot(pcName)
    elif "!kill yourself" in commandLower:
        await Kill()
    elif "!status" in commandLower:
        await Status()
    elif "!list" in commandLower:
        await ListVM()
    elif "!bash" in commandLower:
        await RawCommand(command)
    elif "!help" in commandLower:
        await ShowHelp()
    pass


async def CheckPower():
    global IP
    timer = 0
    success = False
    print("sending ping " + IP)
    
    while timer < timeLimit:
        result = ping(IP, timeout=1,count=1)

        if result.success(option=1):
            success = True
            break
        
        timer+=1
        pass

    if success:
        await SendMessage("Machine powered on.")
    else:
        await SendMessage("Machine took too long to respond. May have failed power on.")

async def SendMessage(message):
    channel = client.get_channel(CHANNEL)
    await channel.send(message)
    pass

async def BashCommand(command, useOutput=True):
    if not useOutput: command = f"{command}> /dev/null"
    
    proc = subprocess.Popen(command, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    out, err = proc.communicate()

    try:
        if useOutput:
            if out != "" and out != '\n':
                if len(out) > 2000:
                    await SendMessage("The output of this command is too large to display.")
                else:
                    await SendMessage(out)
            if err != "" and err != '\n':
                if len(out) > 2000:
                    await SendMessage("This command had an error, but the output is too large to display.")
                else:
                    await SendMessage(err)
    except:
        print("output:")
        print(repr(out))
        print("\nerror:")
        print(repr(err))
    
    return out, err

########### Commands ###########

async def WakeUp(pc = "", waitTime = 0):
    global cancelWakeUp
    if pc == "": # powers on main PC
        if waitTime > 0:
            await SendMessage("Wating {} second(s) to wake up PC.".format(waitTime))
        
        for t in range(waitTime):
            if cancelWakeUp:
                await SendMessage("Aborted wake up for PC.")
                return
            await asyncio.sleep(1)
        
        await SendMessage("Sending wake on lan request.")
        send_magic_packet(MAC)
        await CheckPower()
    else: # powers on virtual machine
        if waitTime > 0:
            await SendMessage("Wating {} second(s) to wake up {}.".format(waitTime, pc))
        
        for t in range(waitTime):
            if cancelWakeUp:
                await SendMessage("Aborted wake up for {}.".format(pc))
                return
            await asyncio.sleep(1)

        await SendMessage(f"Powering on {pc}")
        await BashCommand(f'virsh start "{pc}"')

    pass

async def Shutdown(pcName, force=False):
    if force:
        await BashCommand(f'virsh destroy "{pcName}"')
    else:
        await BashCommand(f'virsh shutdown "{pcName}"')
    pass

async def Reboot(pcName):
        await BashCommand(f'virsh reboot "{pcName}"')
    

async def RawCommand(command):
    command = command.replace("!bash", "").strip()
    await BashCommand(command)
    pass

async def ListVM():
    await BashCommand('virsh list --all')
    pass

async def Kill():
    await SendMessage("Killing discord bot.")
    await client.close()

async def Status():
    await SendMessage("Yes, I'm still here.")

async def ShowHelp():
    helpText = """!wake [vm name] [-t (seconds)]\n    Without a VM name argument, it will attempt to use wake on lan to power on my PC. Optional '-t' will add a delay in seconds before booting.\n
!abort\n    If !wake was used with a delay, this will abort the power on.
!shutdown [vm name]\n    This requires a VM name. Shutting down my main PC is not implemented. This will perform a clean shutdown, if that doesn't work add -f to the command.\n
!reboot [vm name]\n    This requires a VM name. Rebooting my main PC is not implemented.\n
!list\n   Show a list of all VMs installed on the server.\n
!kill yourself\n    This will shutdown the discord bot. There will be no way to start it back up again unless you have access to the unraid server.\n
!status\n    This only confirms that discord bot is still working by reading and sending a message in response.\n
!bash\n   Run a bash command directly on the server. This will not work on commands that require a user response. It also will not print anything with very large outputs.\n
!help\n    That's this message."""
    await SendMessage(helpText)


closedByError = False
try:
    client.run(TOKEN)
except:
    closedByError = True

print("closed")

# Send a notification to unraid when the bot closes.
notifMessage = '/usr/local/emhttp/webGui/scripts/notify -e "Discord Bot Notice" -s "Discord Bot" -d '

if closedByError:
    notifMessage +='"Discord Bot has crashed and was shutdown." -i "warning"'
else:
    notifMessage +='"Discord Bot has been gracefully shutdown."'

notifCommand = f'{notifMessage}> /dev/null'
proc = subprocess.Popen(notifCommand, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

proc.communicate()
