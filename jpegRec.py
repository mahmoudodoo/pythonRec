import os
import uuid
import glob
import sys

# Configuration
FILES_PER_FOLDER = 4
BLOCK_SIZE = 512  # Bytes to read per block

def get_available_drives():
    """Get list of available drives in /dev"""
    return glob.glob('/dev/sd*') + glob.glob('/dev/hd*') + glob.glob('/dev/nvme*')

def select_drive():
    """Display available drives and let user choose"""
    drives = get_available_drives()
    
    if not drives:
        print("No drives found!")
        sys.exit(1)
    
    print("\nAvailable drives:")
    for i, drive in enumerate(drives, 1):
        print(f"{i}. {drive}")
    
    while True:
        try:
            choice = int(input("\nSelect drive (enter number): "))
            if 1 <= choice <= len(drives):
                return drives[choice-1]
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def create_directory(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

def main():
    # Create main recovery directory
    base_dir = "recovered_jpegs"
    create_directory(base_dir)
    
    # Let user select drive
    drive_path = select_drive()
    print(f"\nSelected drive: {drive_path}")
    print("Starting recovery... Press Ctrl+C to stop\n")
    
    current_group = None
    files_in_group = 0
    file_counter = 1
    last_byte = None  # For handling split markers

    try:
        with open(drive_path, "rb") as disk:
            block = disk.read(BLOCK_SIZE)
            offset = 0
            
            while block:
                # Find JPEG header signature (FF D8 FF)
                header_pos = block.find(b'\xFF\xD8\xFF')
                
                if header_pos >= 0:
                    print(f"Found JPEG signature at offset: {hex(header_pos + (BLOCK_SIZE * offset))}")
                    
                    # Create new group directory if needed
                    if files_in_group % FILES_PER_FOLDER == 0:
                        group_id = uuid.uuid4().hex
                        current_group = os.path.join(base_dir, group_id)
                        create_directory(current_group)
                        print(f"\nCreated new group: {group_id}")
                    
                    # Setup recovery variables
                    recovering = True
                    output_path = os.path.join(current_group, f"{file_counter}.jpg")
                    
                    with open(output_path, "wb") as jpg_file:
                        # Write header and remaining data from current block
                        jpg_file.write(block[header_pos:])
                        last_byte = block[-1]  # Track last byte for split markers
                        
                        # Continue reading until end marker (FF D9)
                        while recovering:
                            block = disk.read(BLOCK_SIZE)
                            offset += 1
                            
                            if not block:
                                break
                            
                            # Check for split end marker (across block boundary)
                            if last_byte == 0xFF and block[0] == 0xD9:
                                jpg_file.write(b'\xD9')
                                recovering = False
                            
                            # Check for end marker within current block
                            end_pos = block.find(b'\xFF\xD9')
                            if end_pos >= 0:
                                jpg_file.write(block[:end_pos + 2])
                                recovering = False
                            else:
                                jpg_file.write(block)
                                last_byte = block[-1]  # Update last byte
                    
                    print(f"Recovered file: {output_path}")
                    files_in_group += 1
                    file_counter += 1
                
                # Read next block
                block = disk.read(BLOCK_SIZE)
                offset += 1
                
    except PermissionError:
        print("\nError: Permission denied. Try running with sudo.")
    except KeyboardInterrupt:
        print("\nRecovery stopped by user")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    
    print(f"\nRecovery complete! Total files recovered: {file_counter-1}")

if __name__ == "__main__":
    main()