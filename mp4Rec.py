import os
import datetime

drive = "/dev/sda2"  # Replace X with the appropriate drive identifier (e.g., a, b, c, etc.)
size = 512  # Size of bytes to read

start_date = datetime.datetime(2023, 8, 10)  # Specify the start date
end_date = datetime.datetime(2023, 8, 25)  # Specify the end date

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
        found = byte.find(b'\x00\x00\x00\x18ftyp')
        if found >= 0:
            print(f'==== Found MP4 at location: {hex(found + (size * offs))} ====')
            drec = True
            rcvd += 1

            # Extract the MP4 segment
            mp4_segment = byte[found:]
            
            file_creation_time = os.path.getctime(drive)
            file_creation_date = datetime.datetime.fromtimestamp(file_creation_time)

            if start_date <= file_creation_date <= end_date:
                if files_in_current_rec >= 30:
                    current_rec_directory = get_next_rec_directory()
                    create_directory(current_rec_directory)
                    files_in_current_rec = 0

                files_in_current_rec += 1
                rec_directory_path = os.path.join(script_directory, current_rec_directory, f'{rcvd}.mp4')
                with open(rec_directory_path, 'wb') as fileN:
                    fileN.write(mp4_segment)
                    while drec:
                        byte = fileD.read(size)
                        if byte.startswith(b'\x00\x00\x00\x18ftyp') or byte.startswith(b'\x00\x00\x00\x1Cftyp'):  
                            # Check for the start of another MP4 segment
                            # 0x18 and 0x1C are the common box sizes for ftyp and moov atoms
                            fileN.write(byte)
                            print(f'==== Wrote MP4 to location: {rec_directory_path} ====\n')
                            drec = False
                        else:
                            fileN.write(byte)

        byte = fileD.read(size)
        offs += 1
