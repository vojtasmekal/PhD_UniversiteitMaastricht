import os
import sys
import importlib
import json
import argparse
import datetime

from enum import Enum, auto

from pythonnet import load

load("coreclr")

import time
import ctypes
import clr, System
from System import Array, Int32
from System.Runtime.InteropServices import GCHandle, GCHandleType

from System.Collections.Generic import Dictionary
from System import EventArgs
from System import EventHandler
from System import BitConverter

EEG=True

if EEG:
    from psychopy import parallel
    port = parallel.ParallelPort(address=0x3FE8)


images_order = []
conditions_order = []

class LiveEventType(Enum):
    ButtonPress = 0
    VoiceActivity = auto()
    LookAtParticipant = auto()

isrecording=False

numRecordings=0
numReplays=0

from KiinClient import Guest, AnimationMode

configname="MU_Social_Support.json"
with open(configname, "r") as file:
    config = json.load(file)

participants=config["participants"]
participantid={}

region = "EU"

cl = Guest()
time.sleep(1)
connectedusers={}
shown_image={} #dictionary to keep track of events
played_audio={} #dictionary to keep track of events
block_done={} #dictionary to keep track of events

recordingsName="MU_p02_11072024"



def signal_EEG(level):
    if EEG:
        port.setData(level)
        time.sleep(0.0001)
        port.setData(0)
    print(f"set EEG level to {level}")


def push_and_print(command, arg, optional_param=None):
    if optional_param is not None:
        cl.PushCommand(command, arg, optional_param)
    else:
        cl.PushCommand(command, arg)
    print(f"{command} {arg}")


def handler(source, args):
    global connectedusers,shown_image,played_audio, block_done

    
    if args.data["type"] == 7:
        user_id = args.data["extraData"]["userId"].strip()
        event_id = args.data["extraData"]["event_id"].strip()
        print(f"Custom event received from {user_id} with eventid {event_id}")
        if "show_image" in event_id:
            shown_image[user_id]=datetime.datetime.now()
            if (len(shown_image)>=len(participants)):
                signal_EEG(1)
                shown_image={}
        if "play_audio" in event_id:
            played_audio[user_id]=datetime.datetime.now()
            if (len(played_audio)>=len(participants)):
                signal_EEG(2)
                played_audio={}
        if "block_done" in event_id:
            block_done[user_id]=datetime.datetime.now()
            if (len(block_done)>=len(participants)):
                signal_EEG(3)
                block_done={}

        if "connected" in event_id:
            event_record = {
                "timestamp": datetime.datetime.now(),
                "count": len(connectedusers[user_id]) + 1 if user_id in connectedusers else 1
            }
            
            if user_id not in connectedusers:
                connectedusers[user_id] = [event_record]
            else:
                connectedusers[user_id].append(event_record)
            
            # Print the number of events received by this userId
#            print(f"number:{event_record['count']}")
#            print(f"Current state of connectedusers: {connectedusers}")

def resync():
    global connectedusers
    connectedusers = {user: [] for user in participants}
    event_send_count = 0
    
    # Timeout mechanism to avoid infinite loop
    timeout = 60  # seconds
    start_time = time.time()
    
    # Continue sending events until at least one event is received from all user IDs
    while len([events for events in connectedusers.values() if len(events) > 0]) < len(participants):
        cl.PushCommand("send_event", "connected")
        event_send_count += 1
        print(f"Sent custom event {event_send_count} times")
        time.sleep(1)
        
    print("Received at least one event from all participants.")
    
    # Stop sending new events and wait for all user IDs to have the same number of events
    while True:
        time.sleep(1)
        event_counts = [len(events) for events in connectedusers.values()]
        print(event_counts)
        all_synced = all(count == event_send_count for count in event_counts)
        
        if all_synced:
            print("All participants have received the same number of events.")
            break
        
        if time.time() - start_time > timeout:
            print("Timeout reached while waiting for all events to sync.")
            break

def resync_old():
    global connectedusers
    connectedusers={}
    while len(connectedusers)<len(participants): #wait until all participant headsets have sent back a connected event
        time.sleep(1)
        cl.PushCommand("send_event", "connected")
        print("sent custom event")

def PlayerIdFromNickName(Nickname):
    playerlist=cl.GetPlayersList()
    player_id = None
    for player in playerlist:
        if Nickname in player.NickName:
            player_id=player.UserId
    return player_id

def getAgentsInRoom():
    currentAgents=None
    try:
        currentAgents=cl.GetAgentsInRoom()
    except System.NullReferenceException:
        currentAgents = None
    return currentAgents

def waitForParticipants(participants):
    global participantid
    """
    Waits for a list of participants to be present, calling a push command
    with the names of those not yet present.

    :param participants: List of participant names to wait for.
    """
    present_participants = set()

    while len(present_participants) < len(participants):
        not_present_participants = [participant for participant in participants if participant not in present_participants]
        
        if not_present_participants:  # If there are still participants not present
            not_present_participants_str = '\n'.join(not_present_participants)
            cl.PushCommand("fade_out", f"0 '<size=8px>{not_present_participants_str}'")
            print(".", end="", flush=True)
        
        for participant in participants:
            if participant not in present_participants and PlayerIdFromNickName(participant) is not None:
                present_participants.add(participant)
        
        time.sleep(2)
    for participant in participants:
        participantid[participant]=PlayerIdFromNickName(participant)

    print("All participants are in the room.")

def disable_images():
    cl.PushCommand("spawn_object", "mu_social_support_images mu_social_support_images findGame")
    cl.PushCommand("set_object_scale", "mu_social_support_images 1.5,1.5,1.5 1.0")
    time.sleep(3)
    for i in range(1,241):
        cl.PushCommand("disable_object", f"mu_social_support_images/image_{i:04d}", "")

def show_all_images(delay=1):
    for i in range(1,241):
        if i > 1:
            # Disable the previous image
            cl.PushCommand("disable_object", f"mu_social_support_images/image_{i-1:04d}", "")
        # Enable the current image
        cl.PushCommand("enable_object", f"mu_social_support_images/image_{i:04d}", "")
        cl.PushCommand("show_text", f"tmwall \"<size=10px><alpha=#FF>{i:04d}</mark>\" 0.0")
        cl.PushCommand("wait",f"{delay}")
    # Disable the last image after the loop ends
    cl.PushCommand("disable_object", f"mu_social_support_images/image_0240", "")


def agentSwitch(mode):
    if mode == 0:
        if (len(participants)>1):
            push_and_print("set_agent_visible",f"false {participantid[participants[1]]}",participantid[participants[0]])
            push_and_print("set_agent_visible",f"false {participantid[participants[0]]}",participantid[participants[1]])
            push_and_print("set_character_audio_volume", f"{participantid[participants[0]]} 0.0 0",participantid[participants[1]])
            push_and_print("set_character_audio_volume", f"{participantid[participants[1]]} 0.0 0",participantid[participants[0]])
            push_and_print("set_agent_visible",f"false standing_avatar_1")
        cl.PushCommand("set_agent_visible",f"false standing_avatar_2",participantid[participants[0]])
    elif mode == 1:
        if (len(participants)>1):
            push_and_print("set_agent_visible",f"true {participantid[participants[1]]}",participantid[participants[0]])
            push_and_print("set_agent_visible",f"true {participantid[participants[0]]}",participantid[participants[1]])
            #unmute other participant in 0 time
            push_and_print("set_character_audio_volume", f"{participantid[participants[0]]} 1.0 0",participantid[participants[1]])
            push_and_print("set_character_audio_volume", f"{participantid[participants[1]]} 1.0 0",participantid[participants[0]])
            #make invisible computer agent
            push_and_print("set_agent_visible",f"false standing_avatar_1")
            push_and_print("set_agent_visible",f"false standing_avatar_2")
    elif mode == 2:
        if (len(participants)>1):
            #make invisible the other participant
            push_and_print("set_agent_visible",f"false {participantid[participants[1]]}",participantid[participants[0]])
            push_and_print("set_agent_visible",f"false {participantid[participants[0]]}",participantid[participants[1]])
            #mute other participant when computer agent visible
            push_and_print("set_character_audio_volume", f"{participantid[participants[0]]} 0.0 0",participantid[participants[1]])
            push_and_print("set_character_audio_volume", f"{participantid[participants[1]]} 0.0 0",participantid[participants[0]])
            #make visible computer agent
            push_and_print("set_agent_visible",f"true standing_avatar_1", participantid[participants[1]])
        push_and_print("set_agent_visible",f"true standing_avatar_2",participantid[participants[0]])

        
#schedule file specifies the timing of the sounds, 
# offset specifies the offset of the image to present
# mode is either
# 0... the participants are alone
# 1... the particiapnts see each other
# 2... the participants see the computer agent
def run_presentation(schedule_file, offset, mode):
    global images_order, conditions_order
    # Load the scheduled sound triggers from the JSON file
    with open(schedule_file, 'r') as file:
        sound_events = json.load(file)

    agentSwitch(mode)

    # Index to keep track of which sound event is next
    event_index = 0
    next_sound_time = sound_events[event_index]['time_from_start'] if event_index < len(sound_events) else None

    thisRecordingName=f"{recordingsName}_{mode:04d}"
    cl.PushCommand("start_recording","1011")
    num_images=40
    for i in range(1,num_images+1):  # change to 40 Assuming the presentation always involves 40 images
        push_and_print("send_event","show_image")
        if i > 1:
            push_and_print("disable_object", f"mu_social_support_images/image_{(images_order[i+offset-1]):04d}", "")
            push_and_print("enable_object", f"mu_social_support_images/image_{(images_order[i+offset]):04d}", "")
        else:
            push_and_print("enable_object", f"mu_social_support_images/image_{(images_order[i+offset]):04d}", "")
            push_and_print("play_audio_on_narrator", "what_do_you_see_in_the_image.ogg")

        current_time = i * 5  # Start time for the current image in seconds
        print(next_sound_time)
        # Calculate the total time to the next sound or the end of this image period
        if next_sound_time is not None and next_sound_time < current_time + 5:
            wait_before_sound = next_sound_time - current_time
            if wait_before_sound > 0:
                push_and_print("wait", f"{wait_before_sound:.3f}")
            push_and_print("send_event","play_audio")
            push_and_print("play_audio_clip", f"{sound_events[event_index]['file']} ambientNoise 1.0 0.0 false")
            # Calculate the remaining time after the sound
            wait_after_sound = (current_time + 5) - next_sound_time
            if wait_after_sound > 0:
                push_and_print("wait", f"{wait_after_sound:.3f}")

            # Update to the next sound event
            event_index += 1
            if event_index < len(sound_events):
                next_sound_time = sound_events[event_index]['time_from_start']
            else:
                next_sound_time = None

        else:
            # If no sound is scheduled, wait for the full 5 seconds
            push_and_print("wait", "5.0")

        # if (i%2 == 0):
        #     cl.PushCommand("set_agent_visible",f"true standing_avatar_2")
        # else:
        #     cl.PushCommand("set_agent_visible",f"false standing_avatar_2")
    push_and_print("disable_object", f"mu_social_support_images/image_{(images_order[num_images+offset]):04d}", "")
    push_and_print("fade_out",f"1 '<size=8px>Please wait...'")
    push_and_print("stop_recording",thisRecordingName + " true")

    push_and_print("wait","5.0'")
    push_and_print("fade_in",f"1.0")


def read_json(file_name):
    try:
        with open(file_name, 'r') as file:
            data = json.load(file)
        
        print(f"Successfully read data from {file_name}")
        return data
    
    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_name}' is not a valid JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    
    return None


def connectAndRecord():
    global numRecordings
    global images_order, conditions_order
#    input("Press Enter to Connect...")
    cl.StartClient(config["appId"], "1_2.40")
    time.sleep(3)
    cl.JoinRoom(config["theRoomName"], 5)
    time.sleep(3)
    print(f"waiting for {len(participants)} participants to join")
    waitForParticipants(participants)
    resync()
    disable_images() 
    push_and_print("load_avatar_at_anchor", "islandfemale standing_avatar_2 10") 
    push_and_print("load_avatar_at_anchor", "islandfemale standing_avatar_1 1") 
    push_and_print("play_animation", "standing_avatar_2 StandingIdle PingPong 1")
    push_and_print("play_animation", "standing_avatar_1 StandingIdle PingPong 1")
    push_and_print("set_agent_visible",f"false standing_avatar_1")
    push_and_print("set_agent_visible",f"false standing_avatar_2")
    cl.SetNewAvatar(participantid[participants[0]],"236abeae-afca-4952-a0c0-d807e6fc99c3") # or usermalecc4

    if (len(participants)>1):
        cl.SetNewAvatar(participantid[participants[1]],"defaultfemale")

    push_and_print("fade_in", "2.0")
    
    push_and_print("wait","5")
    if (len(participants)>1):
        push_and_print("set_agent_visible",f"false {participantid[participants[1]]}",participantid[participants[0]])
        push_and_print("set_agent_visible",f"false {participantid[participants[0]]}",participantid[participants[1]])
    push_and_print("play_audio_on_narrator","GetUsed.ogg")
    push_and_print("wait", "3")
    cl.PushCommand("play_audio_on_narrator","LookAround.ogg")
    if (len(participants)>1):
        push_and_print("set_agent_visible",f"true {participantid[participants[1]]}",participantid[participants[0]])
        push_and_print("set_agent_visible",f"true {participantid[participants[0]]}",participantid[participants[1]])

    push_and_print("wait","5")
    if (len(participants)>1):
        push_and_print("wait","30")# let the participants interact freely for 0.5 mins

    push_and_print("disable_object","MirrorURP")
    push_and_print("wait","5")

    time.sleep(20)
    # Re-sync 
    resync()
#    show_all_images()
#    run_presentation("beeps_with_triggers.json",0,conditions_order[0])
    run_presentation("sound_schedule_balanced_with_triggers_1.json",0,1)
    time.sleep(5*5)
    resync()
#    run_presentation("beeps_with_triggers.json",40,conditions_order[1])
    run_presentation("sound_schedule_balanced_with_triggers_2.json",40,2)
    time.sleep(5*5)
    resync()
#    run_presentation("beeps_with_triggers.json",80,conditions_order[2])
    run_presentation("sound_schedule_balanced_with_triggers_3.json",80,0)
    agentSwitch(1)
    if (len(participants)>1):
        push_and_print("wait","10")# let the participants interact freely for 10 seconds
    resync()
    
    push_and_print("fade_out",f"1 '<size=8px>experience finished'")
    push_and_print("unload_experience",f"2")
#    push_and_print("quit_application",f"2")


    time.sleep(10)

    # input("change avatar Fat...")
    # cl.PushCommand("fade_character_blend_shape","self Fat 50.0 10.0")
    # input("change avatar...")
    # cl.PushCommand("fade_character_blend_shape","self Fat 0.0 10.0")


    # thisRecordingName=f"{recordingsName}_{numRecordings:04d}"
    # input("Press Enter to start Recording...")
    # cl.SendGenericCommand("start_recording","1011")
    # input("Press Enter to stop Recording...")
    # cl.SendGenericCommand("stop_recording",thisRecordingName + " true")


cl.liveEventCallback=EventHandler(handler)
#run_presentation("sound_schedule_balanced_with_triggers.json")

def main():
    global images_order, conditions_order
    # if len(sys.argv) != 2:
    #     print("Usage: python script_name.py <json_file_name>")
    #     return
    # json_file = sys.argv[1]
    json_file = "expConditions.json"
    data = read_json(json_file)

    if data is not None:
        images_order = data.get('images_order', [])
        conditions_order = data.get('conditions_order', [])
    
    connectAndRecord()

#run_presentation("sound_schedule_balanced_with_triggers.json",0)
#run_presentation("sound_schedule_balanced_with_triggers.json",40)
#run_presentation("sound_schedule_balanced_with_triggers.json",80)

if __name__ == "__main__":
    main()