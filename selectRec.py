import os
import uuid
import glob
import sys
import platform

# Configuration
FILES_PER_FOLDER = 4
BLOCK_SIZE = 512  # Bytes to read per block

def get_available_drives():
    """Get list of available drives based on OS"""
    if platform.system() == 'Windows':
        import string
        from ctypes import windll
        drives = []
        # Get logical drives (C:, D:, etc.)
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drives.append(f"{letter}:\\")
            bitmask >>= 1

        # Add physical drives
        physical_drives = glob.glob(r'\\.\PhysicalDrive*')
        return drives + physical_drives
    else:  # Linux/Mac
        return glob.glob('/dev/sd*') + glob.glob('/dev/hd*') + glob.glob('/dev/nvme*') + glob.glob('/dev/disk*')

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
                selected = drives[choice-1]
                # Convert Windows logical drive to physical path
                if platform.system() == 'Windows' and selected.endswith(':\\'):
                    return f"\\\\.\\{selected[0]}:"
                return selected
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def select_recovery_type():
    """Let user select what file types to recover"""
    print("\nSelect recovery type:")
    print("1. PNG images")
    print("2. JPG/JPEG images")
    print("3. Videos (MP4, MKV)")
    print("4. All supported types (PNG, JPG, MP4, MKV)")

    while True:
        try:
            choice = int(input("\nEnter your choice (1-4): "))
            if 1 <= choice <= 4:
                return choice
            print("Invalid selection. Try again.")
        except ValueError:
            print("Please enter a valid number.")

def create_directory(path):
    """Create directory if it doesn't exist"""
    os.makedirs(path, exist_ok=True)

def get_file_signatures(recovery_type):
    """Return file signatures based on recovery type"""
    signatures = {
        'png': {
            'header': b'\x89PNG\r\n\x1a\n',
            'footer': b'IEND',
            'footer_length': 8,
            'extension': 'png'
        },
        'jpg': {
            'header': b'\xff\xd8\xff',
            'footer': b'\xff\xd9',
            'footer_length': 2,
            'extension': 'jpg'
        },
        'mp4': {
            'header': b'\x00\x00\x00\x18ftypmp42',
            'footer': None,
            'extension': 'mp4'
        },
        'mkv': {
            'header': b'\x1a\x45\xdf\xa3',
            'footer': None,
            'extension': 'mkv'
        }
    }

    if recovery_type == 1:  # PNG
        return [signatures['png']]
    elif recovery_type == 2:  # JPG
        return [signatures['jpg']]
    elif recovery_type == 3:  # Videos
        return [signatures['mp4'], signatures['mkv']]
    else:  # All types
        return list(signatures.values())

def recover_files(disk, signature, base_dir, current_group, files_in_group, file_counter):
    """Recover files based on signature pattern"""
    disk.seek(0)  # Start from beginning of disk
    block = disk.read(BLOCK_SIZE)
    offset = 0
    recovered_files = 0

    while block:
        header_pos = block.find(signature['header'])

        if header_pos >= 0:
            print(f"Found {signature['extension'].upper()} signature at offset: {hex(header_pos + (BLOCK_SIZE * offset))}")

            if files_in_group[0] % FILES_PER_FOLDER == 0:
                group_id = uuid.uuid4().hex
                current_group[0] = os.path.join(base_dir, group_id)
                create_directory(current_group[0])
                print(f"\nCreated new group: {group_id}")

            output_path = os.path.join(current_group[0], f"{file_counter[0]}.{signature['extension']}")

            with open(output_path, "wb") as output_file:
                output_file.write(block[header_pos:])
                recovering = True

                while recovering:
                    block = disk.read(BLOCK_SIZE)
                    if not block:
                        break

                    if signature['footer']:
                        end_pos = block.find(signature['footer'])
                        if end_pos >= 0:
                            output_file.write(block[:end_pos + signature['footer_length']])
                            recovering = False
                        else:
                            output_file.write(block)
                    else:
                        # For files without footer, look for next header or max size
                        next_header_pos = block.find(signature['header'])
                        if next_header_pos >= 0:
                            output_file.write(block[:next_header_pos])
                            recovering = False
                            disk.seek(disk.tell() - (BLOCK_SIZE - next_header_pos))
                        else:
                            output_file.write(block)

            print(f"Recovered file: {output_path}")
            files_in_group[0] += 1
            file_counter[0] += 1
            recovered_files += 1

        block = disk.read(BLOCK_SIZE)
        offset += 1

    return recovered_files

def main():
    base_dir = "recovered_files"
    create_directory(base_dir)

    drive_path = select_drive()
    print(f"\nSelected drive: {drive_path}")

    recovery_type = select_recovery_type()
    signatures = get_file_signatures(recovery_type)

    print("\nStarting recovery... Press Ctrl+C to stop\n")

    current_group = [None]
    files_in_group = [0]
    file_counter = [1]
    total_recovered = 0

    try:
        # Windows requires raw device access with this syntax
        if platform.system() == 'Windows':
            if not drive_path.startswith(r'\\.\'):
                drive_path = fr'\\.\{drive_path.replace(":/", ":")}'

        with open(drive_path, "rb") as disk:
            for signature in signatures:
                print(f"\nScanning for {signature['extension'].upper()} files...")
                recovered = recover_files(disk, signature, base_dir, current_group, files_in_group, file_counter)
                total_recovered += recovered
                print(f"Recovered {recovered} {signature['extension'].upper()} files")

    except PermissionError:
        print("\nError: Permission denied. Try running as administrator.")
    except FileNotFoundError:
        print("\nError: Drive not found. Make sure you're using the correct path.")
        if platform.system() == 'Windows':
            print("On Windows, use format like: \\\\.\\PhysicalDrive0 or \\\\.\\C:")
    except KeyboardInterrupt:
        print("\nRecovery stopped by user")
    except Exception as e:
        print(f"\nError occurred: {str(e)}")
    finally:
        print(f"\nRecovery complete! Total files recovered: {total_recovered}")

if __name__ == "__main__":
    main()
