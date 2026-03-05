import numpy as np
import json
import random

# Select half of all painting stimuli
woodscapes = np.concatenate((np.arange(1, 12), np.arange(45, 56), np.arange(89, 97)), axis=0)
seascapes = np.concatenate((np.arange(12, 23), np.arange(56, 67), np.arange(100, 108)), axis=0)
single_person = np.concatenate((np.arange(23, 34), np.arange(67, 78), np.arange(111, 119)), axis=0)
multiple_people = np.concatenate((np.arange(34, 45), np.arange(78, 89), np.arange(122, 130)), axis=0)

# Shuffle the paintings within category
random.shuffle(woodscapes)
random.shuffle(seascapes)
random.shuffle(single_person)
random.shuffle(multiple_people)

# Create three experimental blocks each containing ten paintings from each category
block1 = np.concatenate((woodscapes[0:10], seascapes[0:10], single_person[0:10], multiple_people[0:10]), axis=0)
block2 = np.concatenate((woodscapes[10:20], seascapes[10:20], single_person[10:20], multiple_people[10:20]), axis=0)
block3 = np.concatenate((woodscapes[20:31], seascapes[20:31], single_person[20:31], multiple_people[20:31]), axis=0)

# Shuffle the order of paintings within each block
random.shuffle(block1)
random.shuffle(block2)
random.shuffle(block3)

# Combine the three blocks into painting order for full experiment
images_order = np.concatenate((block1, block2, block3), axis=0)

# Randomize the order of the three conditions for the experiment
conditions_order = np.array([0, 1, 2])
random.shuffle(conditions_order)

# Save image and condition order in expConditions json file
expConditions = {'images_order': images_order.tolist(), 'conditions_order': conditions_order.tolist()}

with open('expConditions.json', 'w') as outfile:
    json.dump(expConditions, outfile)

with open('file_durations.json', 'r') as soundfile:
    sounds = json.load(soundfile)
    
total_images = 40
image_display_time = 5
total_time = total_images * image_display_time
plays_per_sound = 1
total_sounds = len(sounds) * plays_per_sound

average_interval = total_time / total_sounds
interval_range = average_interval * 0.1

for i in range(len(conditions_order)):
    
    events = []
    current_time = 0
    trigger_number = 0
    
    random.shuffle(sounds)
    
    while current_time < total_time:
        for sound in sounds:
            for _ in range(plays_per_sound):
                time_variation = random.uniform(-interval_range, interval_range)
                sound_time = max(0, current_time + time_variation) 
                
                if sound_time + sound['duration'] <= total_time:
                    trigger_number += 1
                    events.append({
                        "trigger_number": trigger_number,
                        "time_from_start": sound_time,
                        "file": sound['file']
                    })
                
                current_time += average_interval
                
                if current_time >= total_time:
                    break
            if current_time >= total_time:
                break
                
    events.sort(key=lambda x: x['time_from_start'])
    
    outputFile = 'sound_schedule_balanced_with_triggers_{0}.json'.format(conditions_order[i])
    with open(outputFile, 'w') as file:
        json.dump(events, file, indent=4)
        
print("Two JSON files created successfully - one randomizing image and condition order and one evenly spacing out sounds.")