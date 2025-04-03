import csv

# Define the shift types in order
shift_types = ['A', 'B', 'D', 'E', 'N', 'Q', 'T', 'z', '!', '#']

# Define the mapping from shift type to interval types
shift_type_to_interval_types = {
    'A': [1, 2, 3],
    'B': [4, 5],
    'D': [1, 2],
    'E': [3, 4],
    'N': [5],
    'Q': [2, 3],
    'T': [1],
    'z': [3],
    '!': [4],
    '#': [2, 3, 4]
}

# Open the CSV file for writing
with open('ShiftInterval.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write the header
    writer.writerow(['shift_id', 'workgroup_id', 'interval_id'])

    # Generate rows for all 310 shifts
    for shift_id in range(1, 311):  # 1 to 310 inclusive
        # Calculate day (1 to 31)
        day = (shift_id - 1) // 10 + 1
        # Calculate type index (0 to 9)
        type_index = (shift_id - 1) % 10
        shift_type = shift_types[type_index]
        # Get corresponding interval types
        interval_types = shift_type_to_interval_types[shift_type]

        # For each workgroup
        for workgroup_id in range(1, 5):  # 1 to 4
            # For each interval type linked to the shift type
            for interval_type in interval_types:
                # Calculate interval_id
                interval_id = (workgroup_id - 1) * 155 + (day - 1) * 5 + interval_type
                # Write the row
                writer.writerow([shift_id, workgroup_id, interval_id])

print("ShiftInterval.csv has been generated successfully.")
