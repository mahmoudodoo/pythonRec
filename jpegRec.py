import os
import datetime

drive = "/dev/sda2"  # Replace X with the appropriate drive identifier (e.g., a, b, c, etc.)
size = 512  # Size of bytes to read

start_date = datetime.datetime(2023, 9, 1)  # Specify the start date
end_date = datetime.datetime(2023, 9, 2)  # Specify the end date

def create_directory(directory_name):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

def get_next_rec_directory():
    rec_directory_prefix = "rec"
    index = 1
    while True:
        rec_directory = f"{rec_directory_prefix}{index}"
        if not os.path.exists(rec_directory):
            return rec_directory
        index += 1

script_directory = os.path.dirname(os.path.abspath(__file__))
current_rec_directory = "rec"
create_directory(current_rec_directory)

with open(drive, "rb") as fileD:
    byte = fileD.read(size)
    offs = 0  # Offset location
    rcvd = 0  # Recovered file ID
    files_in_current_rec = 0

    while byte:
        found = byte.find(b'\xFF\xD8\xFF')
        if found >= 0:
            print(f'==== Found JPEG at location: {hex(found + (size * offs))} ====')
            drec = True
            rcvd += 1

            # Extract the JPEG segment
            jpeg_segment = byte[found:]
            
            file_creation_time = os.path.getctime(drive)
            file_creation_date = datetime.datetime.fromtimestamp(file_creation_time)

            if start_date <= file_creation_date <= end_date:
                if files_in_current_rec >= 30:
                    current_rec_directory = get_next_rec_directory()
                    create_directory(current_rec_directory)
                    files_in_current_rec = 0

                files_in_current_rec += 1
                rec_directory_path = os.path.join(script_directory, current_rec_directory, f'{rcvd}.jpg')
                with open(rec_directory_path, 'wb') as fileN:
                    fileN.write(jpeg_segment)
                    while drec:
                        byte = fileD.read(size)
                        if byte.startswith(b'\xFF\xD9'):  # Check for the end of the JPEG segment
                            fileN.write(byte)
                            print(f'==== Wrote JPEG to location: {rec_directory_path} ====\n')
                            drec = False
                        else:
                            fileN.write(byte)

        byte = fileD.read(size)
        offs += 1
