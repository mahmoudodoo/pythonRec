import os
import datetime

drive = "/dev/sda2"  # Replace X with the appropriate drive identifier (e.g., a, b, c, etc.)
size = 512  # Size of bytes to read

start_date = datetime.datetime(2023, 8, 1)  # Specify the start date
end_date = datetime.datetime(2023, 8, 10)  # Specify the end date

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
        found = byte.find(b'\x89PNG\r\n\x1a\n')
        if found >= 0:
            print(f'==== Found PNG at location: {hex(found + (size * offs))} ====')
            drec = True
            rcvd += 1

            # Extract IHDR chunk from the PNG
            header = byte[found:found + 33]
            width = int.from_bytes(header[16:20], byteorder='big')
            height = int.from_bytes(header[20:24], byteorder='big')

            if width > 300:
                file_creation_time = os.path.getctime(drive)
                file_creation_date = datetime.datetime.fromtimestamp(file_creation_time)

                if start_date <= file_creation_date <= end_date:
                    if files_in_current_rec >= 30:
                        current_rec_directory = get_next_rec_directory()
                        create_directory(current_rec_directory)
                        files_in_current_rec = 0

                    files_in_current_rec += 1
                    rec_directory_path = os.path.join(script_directory, current_rec_directory, f'{rcvd}.png')
                    with open(rec_directory_path, 'wb') as fileN:
                        fileN.write(byte[found:])
                        while drec:
                            byte = fileD.read(size)
                            iend = byte.find(b'IEND')
                            if iend >= 0:
                                fileN.write(byte[:iend + 4])
                                print(f'==== Wrote PNG to location: {rec_directory_path} ====\n')
                                drec = False
                            else:
                                fileN.write(byte)

        byte = fileD.read(size)
        offs += 1
