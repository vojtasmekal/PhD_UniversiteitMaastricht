import random
import json

# Read sounds from a JSON file
with open('file_durations.json', 'r') as file:
    sounds = json.load(file)

# Randomize the order of sounds
random.shuffle(sounds)

total_images = 40
image_display_time = 5  # each image is displayed for 5 seconds
total_time = total_images * image_display_time

# Decide how many times you want each sound to play, roughly
plays_per_sound = 1
total_sounds = len(sounds) * plays_per_sound

# Calculate the average time interval between sounds
average_interval = total_time / total_sounds

# Range to add randomness (+/- 10% of the average interval)
interval_range = average_interval * 0.1

events = []
current_time = 0
trigger_number = 0

while current_time < total_time:
    for sound in sounds:
        for _ in range(plays_per_sound):
            # Adjust current_time within a small range to avoid clumping
            time_variation = random.uniform(-interval_range, interval_range)
            sound_time = max(0, current_time + time_variation)  # Ensure sound_time doesn't go negative
            
            # Append the event if it's within the total duration
            if sound_time + sound['duration'] <= total_time:
                trigger_number += 1
                events.append({
                    "trigger_number": trigger_number,
                    "time_from_start": sound_time,
                    "file": sound['file']
                })

            # Increment current_time by the average interval
            current_time += average_interval

            # Break if the total time is exceeded
            if current_time >= total_time:
                break
        if current_time >= total_time:
            break

# Sort events by time from start
events.sort(key=lambda x: x['time_from_start'])

# Save the events to a JSON file
with open('sound_schedule_balanced_with_triggers_3.json', 'w') as file:
    json.dump(events, file, indent=4)

print("JSON file with balanced and evenly spaced sound schedule with triggers created successfully.")