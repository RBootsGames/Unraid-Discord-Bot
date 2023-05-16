import os
import io
from datetime import datetime, timedelta
import discord
import subprocess
import asyncio
import socket

from threading import Thread
from dotenv import load_dotenv
from wakeonlan import send_magic_packet
from pythonping import ping
# from time import sleep


class WakeOnLanPC:
    def __init__(self, macAdress, ipAddress):
        self.MAC = macAdress.strip()
        self.IP = ipAddress.strip()
        pass

    def __str__(self):
        return "MAC: {}  IP: {}".format(self.MAC, self.IP)
    def __repr__(self):
        return self.__str__()




load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = int(os.getenv('CHANNEL_GENERAL'))
cc = os.getenv('COMMAND_INDICATOR')
# MAC = os.getenv('MAC_ADDRESS')


# Read WOL variables
wolPCs = {}
rawWOL = os.getenv('WOL_PCS').split(",")
for pc in rawWOL:
    part = pc.split(":")
    name = part[0]
    mac = ""
    ip = ""

    if "." in part[1]:
        ip = part[1]
    else:
        mac = part[1]
    
    if "." in part[2]:
        ip = part[2]
    else:
        mac = part[2]
    
    wolPCs.update({name: WakeOnLanPC(mac, ip)})
    pass

wolDelay = 0
try: wolDelay = int(os.getenv('WOL_DELAY'))
except: pass
# print(wolPCs["default"].MAC)
# exit(0)
# Read phone IP addresses
rawPhone = os.getenv('PHONE_IPS').split(",")
phoneIPs = []
phoneAlreadyHere = False


for phone in rawPhone:
    txt = phone.strip()
    if txt != "":
        phoneIPs.append(phone)


timeLimit = int(os.getenv('POWER_CHECK_TIMEOUT'))

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

cancelWakeUp = False

# exit

@client.event
async def on_ready():
    print(f'{client.user.name} has connected.')
    # await Ugh()
    # oof = Thread(target=BeforeCheckPhoneExistence)
    # oof.start()
    # channel = client.get_channel(CHANNEL)
    # await channel.send("Hello?")

    # await SendMessage(f'{client.user.name} has connected.')

    # pingThrd = Thread()
    if len(phoneIPs) > 0:
        await CheckPhoneExistence(phoneIPs[0])
        # await CheckPhoneExistence(phoneIPs[0])
        # pingThrd = Thread(target=BeforeCheckPhoneExistence, args=(phoneIPs[0],))
        # pingThrd.start()
    pass

@client.event
async def on_message(message):
    message:discord.message.Message

    if message.author != client.user:
        await RunCommand(message.content)


async def RunCommand(command):
    command:str
    command = command.strip()
    if command.lower().startswith(cc) == False:
        return
    
    # This gets rid of any spaces between the command indicator and the actual command.
    if cc != '':
        command = command[1:].lstrip()
        command = cc + command

    global cancelWakeUp
    commandLower = command.lower()

    if commandLower.startswith(cc + "wake"):
        args = command[len(cc + "wake"):].strip()
        pcName = args.split("-")[0].strip()
        args = args.replace(pcName, "").strip()
        args = args.split(" ")

        waitTime = 0
        if "-t" in args:
            try:
                waitTime = round(float(args[args.index("-t")+1]))
            except: pass

        verbose = False
        if "-v" in args:
            verbose = True
        
        await WakeUp(pcName, waitTime, verbose)
    elif commandLower.startswith(cc + "abort"):
        cancelWakeUp = True
    elif commandLower.startswith(cc + "shutdown"):
        pcName = command.replace(cc + "shutdown", "").strip()
        pcName =  pcName.replace(cc + "Shutdown", "").strip()
        force = False
        if "-f" in pcName or "-F" in pcName:
            force = True
            pcName = pcName.replace("-f", "").replace("-F", "").strip()

        print("Name:", pcName)
        await Shutdown(pcName, force)
    elif commandLower.startswith(cc + "reboot"):
        pcName = command.replace(cc + "reboot", "").strip()
        await Reboot(pcName)
    elif commandLower.startswith(cc + "kill yourself"):
        await Kill()
    elif commandLower.startswith(cc + "status"):
        await Status()
    elif commandLower.startswith(cc + "list"):
        await ListVM()
    elif commandLower.startswith(cc + "bash"):
        await RawCommand(command)
    elif commandLower.startswith(cc + "help"):
        await ShowHelp()
    elif commandLower.startswith(cc + "test"):
        await SendSocketMessage("Test socket message")
    pass


async def CheckPower(ip:str, verbose = False, overrideWaitTime = -1):
    # global IP
    timer = 0
    success = False
    print("sending ping " + ip)

    # Use the normal wait time if one isn't specified.
    if overrideWaitTime == -1:
        overrideWaitTime = timeLimit
    
    while timer < overrideWaitTime:
        result = ping(ip, timeout=1,count=1)

        if result.success(option=1):
            success = True
            break
        
        timer+=1
        pass

    if success:
        if verbose:
            await SendMessage("Machine powered on.")
        return True
    else:
        # Only send a message if the wait time wasn't overridden.
        if overrideWaitTime == timeLimit:
            await SendMessage("Machine took too long to respond. May have failed power on.")
        
        return False

async def SendMessage(message):
    channel = client.get_channel(CHANNEL)
    await channel.send(message)
    pass

async def BashCommand(command, outputToNull=False, sendMessageWithOutput=True):
    # create a tmux sessions if it doesn't exist
    # print(0)
    subprocess.Popen("tmux new -s discordenv -d > /dev/null 2>&1", shell=True, universal_newlines=True).communicate()
    # print(1)
    # append command for tmux session
    command = "tmux send-keys -t discordenv '" + command + "' Enter"
    # print(2)

    outputPath = "/tmp/discordenv"
    # print(3)
    # start tmux output redirect
    subprocess.Popen("tmux pipe-pane -t discordenv 'cat > " + outputPath + "'", shell=True, universal_newlines=True).communicate()
    # print(4)
    
    subprocess.Popen(command, shell=True, universal_newlines=True)
    # print(5)

    await asyncio.sleep(.5)
    # wait until command is done running by checking modified time on the output file
    lastMod = os.path.getmtime(outputPath)
    while True:
        await asyncio.sleep(.5)
        newMod = os.path.getmtime(outputPath)
        if lastMod == newMod:
            break
        else:
            lastMod = newMod
            # print(lastMod)
        pass
    # print(6)
    
    # stop tmux output redirect
    subprocess.Popen("tmux pipe-pane -t discordenv", shell=True, universal_newlines=True).communicate()
    # print(7)


    rawOut = open(outputPath, "r").readlines()
    rawOut = rawOut[1:]
    if rawOut[-1][-1] == ' ' and rawOut[-1][-2] == '#':
        rawOut = rawOut[:-1]
        # print("removed last line")
    out = ""
    # remove all formating characters
    removing = False
    for line in rawOut:
        removing = False
        for c in range(len(line)):
            if not removing and line[c] == '':
                removing = True
            
            if not removing:
                out += line[c]

            if removing and line[c] == 'm':
                removing = False

    # print(rawOut)
    err = ""
    # if outputToNull: command = f"{command}> /dev/null"
    
    # proc = subprocess.Popen(command, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # out, err = proc.communicate()

    try:
        if not outputToNull:
            if out != "" and out != '\n':
                if len(out) > 2000:
                    if sendMessageWithOutput:
                        await SendMessage("The output of this command is too large to display.")
                        
                        channel = client.get_channel(CHANNEL)

                        # load the output into a buffer to be able to send a file without writing to the disk (ram only probably?)
                        buffy = io.BytesIO(bytes(out, "utf-8"))
                        await channel.send(file=discord.File(buffy, filename="output.txt"))
                else:
                    if sendMessageWithOutput:
                        await SendMessage(out)
            if err != "" and err != '\n':
                if len(out) > 2000:
                    if sendMessageWithOutput:
                        await SendMessage("The output of this command is too large to display.")
                        
                        channel = client.get_channel(CHANNEL)

                        # load the output into a buffer to be able to send a file without writing to the disk (ram only probably?)
                        buffy = io.BytesIO(bytes(out, "utf-8"))
                        await channel.send(file=discord.File(buffy, filename="output.txt"))
                else:
                    if sendMessageWithOutput:
                        await SendMessage(err)
    except:
        print("output:")
        print(repr(out))
        print("\nerror:")
        print(repr(err))
    
    # print("command done")
    # return out, err

############# Commands #############

async def TestSend():
    await SendMessage("Response...")
    pass

async def WakeUp(pc = "", waitTime = 0, verbose = False):
    global cancelWakeUp
    global wolPCs
    global phoneAlreadyHere
    
    cancelWakeUp = False
    if pc == "": # powers on main PC/default PC
        if len(wolPCs) == 1 or "default" in wolPCs:
            key = "default"
            if len(wolPCs) == 1:
                key = list(wolPCs.keys())[0]

            PCOn = await CheckPower(wolPCs[key].IP, overrideWaitTime=2)
            if PCOn:
                if verbose:
                    await SendMessage("Computer already on.")
                return

            if waitTime > 0:
                await SendMessage("Wating {} second(s) to wake up PC.".format(waitTime))
            else:
                await SendMessage("Powering on PC.")
            
            for t in range(waitTime):
                if cancelWakeUp:
                    await SendMessage("Aborted wake up for PC.")
                    return
                await asyncio.sleep(1)
            
            if verbose:
                await SendMessage("Sending wake on lan request.")
            

            try:
                send_magic_packet(wolPCs[key].MAC)
            except:
                await SendMessage("The mac address '{}' for '{}' appears to be an invalid format."
                                    .format(wolPCs[key].MAC, key))
                return

            await CheckPower(wolPCs[key].IP, verbose)
        pass
    else: # powers on virtual machine or named PCs
        if waitTime > 0:
            await SendMessage("Wating {} second(s) to wake up {}.".format(waitTime, pc))
        
        for t in range(waitTime):
            if cancelWakeUp:
                await SendMessage("Aborted wake up for {}.".format(pc))
                return
            await asyncio.sleep(1)

        if verbose:
            await SendMessage(f"Powering on {pc}")

        if pc in wolPCs:
            try:
                send_magic_packet(wolPCs[pc].MAC)
            except:
                await SendMessage("The mac address '{}' for '{}' appears to be an invalid format."
                                    .format(wolPCs[pc].MAC, pc))
                return

            await CheckPower(wolPCs[pc].IP, verbose)
            
            pass
        else:
            await BashCommand(f'virsh start "{pc}"')

    pass

async def Shutdown(pcName, force=False):
    if pcName == "": # shuts down main PC/default PC
        if len(wolPCs) == 1 or "default" in wolPCs:
            key = "default"
            if len(wolPCs) == 1:
                key = list(wolPCs.keys())[0]

            PCOn = await CheckPower(wolPCs[key].IP, overrideWaitTime=2)
            if PCOn == False:
                await SendMessage("Computer already off.")
                return

            # await SendMessage("This has not been setup yet.")
            await SendMessage("Shutting down PC.")
            
            if force == True:
                await SendSocketMessage("shutdown -f")
            else:
                await SendSocketMessage("shutdown")
        pass
    else:
        if force:
            await BashCommand(f'virsh destroy "{pcName}"')
        else:
            await BashCommand(f'virsh shutdown "{pcName}"')
    pass

async def Reboot(pcName):
        await BashCommand(f'virsh reboot "{pcName}"')
    

async def RawCommand(command):
    command = command.replace(cc + "bash", "").strip()
    command = command.replace(cc + "Bash", "").strip()
    await BashCommand(command)
    pass

async def ListVM():
    await BashCommand('virsh list --all')
    print("executed")
    if len(wolPCs) > 0:
        pcResults = " \nPhysical Computers\n--------------------------------"
        # Check if physical computers are on.
        for key in wolPCs.keys():
            isOn = await CheckPower(wolPCs[key].IP, overrideWaitTime=1)
            pcResults += "\n -    {}{}".format(str(key).ljust(23), "running" if isOn else "shut off")
        
        await SendMessage(pcResults)
    pass


async def Kill():
    await SendMessage("Killing discord bot.")
    await client.close()

async def Status():
    await SendMessage("Yes, I'm still here.")

async def ShowHelp():
    helpText = (f"{cc}wake [vm name] [-t (seconds)]\n    Without a VM name argument, it will attempt to use wake on lan to power on the only/default PC. Optional: '-t' will add a delay in seconds before booting. '-v' will increase verbosity\n"
    f"{cc}abort\n    If {cc}wake was used with a delay, this will abort the power on.\n\n"
    f"{cc}shutdown [vm name]\n    This requires a VM name. Shutting down my main PC is not implemented. This will perform a clean shutdown, if that doesn't work add -f to the command.\n\n"
    f"{cc}reboot [vm name]\n    This requires a VM name. Rebooting my main PC is not implemented.\n\n"
    f"{cc}list\n   Show a list of all VMs installed on the server.\n\n"
    f"{cc}kill yourself\n    This will shutdown the discord bot. There will be no way to start it back up again unless you have access to the unraid server.\n\n"
    f"{cc}status\n    This only confirms that discord bot is still working by reading and sending a message in response.\n\n"
    f"{cc}bash\n   Run a bash command directly on the server. This will not work on commands that require a user response. It also will not print anything with very large outputs.\n\n"
    f"{cc}help\n    That's this message.")
    await SendMessage(helpText)
########### End Commands ###########

########## PC Websockets ###########

pcSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socketPort = 9000

async def ConnectToWebsocket():
    global pcSocket
    global wolPCs
    
    print(f"Attempting connection: {wolPCs['default'].IP}:{socketPort}")

    try:
        pcSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        pcSocket.settimeout(2)
        pcSocket.connect((wolPCs["default"].IP, socketPort))
        pcSocket.settimeout(None) # I guess this is necessary
        return True
    except: 
        print("Couldn't connect to websocket")
        return False
    pass

async def SendSocketMessage(message:str):
    global pcSocket

    try:
        pcSocket.sendall(bytes(message, "utf-8"))
        print(f"sent message: {message}")
    except: # Try to connect and send again if not already connected.
        connectResult = await ConnectToWebsocket()
        if connectResult:
            pcSocket.sendall(bytes(message, "utf-8"))
            print(f"sent message: {message}")
    pass

######## End PC Websockets #########


async def CheckPhoneExistence(pingIP:str):

    # return
    global phoneAlreadyHere
    success = False
    firstRun = True
    intervalCheck = 10
    lastPhoneVisible = datetime.min
    oneHR = timedelta(hours=1)


    while True:
        result = ping(pingIP, timeout=4,count=1)

        # Check if ping was successful
        if result.packet_loss == 0:
            success = True
        else:
            success = False

        # with open ("phone.log", "a") as fil:
        #     text = " | success" if success else " | failed"
        #     fil.write("{}{}\n".format(datetime.now(), text))
                
        if firstRun:
            firstRun = False
            # Check if the phone is already here at the startup
            if success:
                phoneAlreadyHere = True
                lastPhoneVisible = datetime.now()
        else:
            if success:
                lastPhoneVisible = datetime.now()
 
                if not phoneAlreadyHere:
                    # await SendMessage("Found phone")
                    phoneAlreadyHere = True
                    await WakeUp("", wolDelay)


            elif not success and phoneAlreadyHere:
                if datetime.now() - oneHR > lastPhoneVisible:
                    # await SendMessage("phone no longer here")
                    phoneAlreadyHere = False

                # else:
                #     await SendMessage("phone not gone for long enough.")
        
        if not phoneAlreadyHere:
            await asyncio.sleep(intervalCheck)
        else:
            await asyncio.sleep(intervalCheck*10)

        pass


def Main():
    closedByError = False
    try:
        # subprocess.Popen("tmux new -s discordenv \; detach", shell=True, universal_newlines=True).communicate()

        # subprocess.Popen("tmux new -As discordenv \; detach", shell=True, universal_newlines=True).communicate()
        client.run(TOKEN)
    except KeyboardInterrupt: pass
    except:
        closedByError = True

    print("closed")

    # subprocess.Popen("tmux kill-session -t discordenv", shell=True, universal_newlines=True).communicate()
    # print("closed discordenv tmux session")


    try:
        pcSocket.close()
        print("socket closed")
    except: pass

    # Send a notification to unraid when the bot closes.
    notifMessage = '/usr/local/emhttp/webGui/scripts/notify -e "Discord Bot Notice" -s "Discord Bot" -d '

    if closedByError:
        notifMessage +='"Discord Bot has crashed and was shutdown." -i "warning"'
    else:
        notifMessage +='"Discord Bot has been gracefully shutdown."'

    notifCommand = f'{notifMessage}> /dev/null'
    proc = subprocess.Popen(notifCommand, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    proc.communicate()


if __name__ == "__main__":
    Main()
