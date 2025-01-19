import random

# Function to add bits to a binary stream
def add_bits(binary_stream, value, num_bits):
    for j in range(num_bits):
        bit = (value >> (num_bits - 1 - j)) & 1
        binary_stream.append(bit)

# Function for compression
def compression(number_list):
    diff_list = [number_list[0]]  # Include the first value as is
    binary_stream = []

    # Add the first value
    add_bits(binary_stream, number_list[0], 8)

    for i in range(1, len(number_list)):
        diff = number_list[i] - number_list[i - 1]
        diff_list.append(diff)

    #print("Difference list:", diff_list)  # Output the corrected difference list

    i = 1  # Start from the first difference (skip the initial value)
    while i < len(diff_list):
        diff = diff_list[i]

        if -30 <= diff <= 30 and diff != 0:
            add_bits(binary_stream, 0, 2)  # Prefix 00 for difference encoding

            if -2 <= diff <= 2:
                add_bits(binary_stream, 0, 2)
                add_bits(binary_stream, diff + 2 if diff < 0 else diff + 1, 2)
            elif -6 <= diff <= 6:
                add_bits(binary_stream, 1, 2)
                add_bits(binary_stream, diff + 6 if diff < 0 else diff + 1, 3)
            elif -14 <= diff <= 14:
                add_bits(binary_stream, 2, 2)
                add_bits(binary_stream, diff + 14 if diff < 0 else diff + 1, 4)
            elif -30 <= diff <= 30:
                add_bits(binary_stream, 3, 2)
                add_bits(binary_stream, diff + 30 if diff < 0 else diff + 1, 5)
        elif diff == 0:
            add_bits(binary_stream, 1, 2)
            zero_count = 1
            while zero_count < 8 and i + 1 < len(diff_list) and diff_list[i + 1] == 0:
                zero_count += 1
                i += 1
            add_bits(binary_stream, zero_count - 1, 3)
        else:
            add_bits(binary_stream, 2, 2)  # Prefix for large differences
            add_bits(binary_stream, 0 if diff > 0 else 1, 1)  # Sign
            add_bits(binary_stream, abs(diff), 13)  # Absolute value of difference

        i += 1

    add_bits(binary_stream, 3, 2)
    return binary_stream


# Function to convert binary stream to a string
def binary_stream_to_string(binary_stream):
    return ''.join(map(str, binary_stream))

# Function to read a specified number of bits from a binary string
def read_bits(binary_string, position, num_bits):
    value = int(binary_string[position:position + num_bits], 2)
    position += num_bits
    return value, position

# Function for decompression
def decompression(compressed_stream):
    decompressed_numbers = []
    binary_string = ''.join(map(str, compressed_stream))
    position = 0

    current_number, position = read_bits(binary_string, position, 8)
    decompressed_numbers.append(current_number)

    while position < len(binary_string):
        prefix, position = read_bits(binary_string, position, 2)

        if prefix == 0b00:
            sub_prefix, position = read_bits(binary_string, position, 2)

            if sub_prefix == 0b00:
                delta, position = read_bits(binary_string, position, 2)
                delta = delta - 2 if delta < 2 else delta - 1
            elif sub_prefix == 0b01:
                delta, position = read_bits(binary_string, position, 3)
                delta = delta - 6 if delta < 4 else delta - 1
            elif sub_prefix == 0b10:
                delta, position = read_bits(binary_string, position, 4)
                delta = delta - 14 if delta < 8 else delta - 1
            elif sub_prefix == 0b11:
                delta, position = read_bits(binary_string, position, 5)
                delta = delta - 30 if delta < 16 else delta - 1

            current_number += delta
            decompressed_numbers.append(current_number)
        elif prefix == 0b01:
            zero_count, position = read_bits(binary_string, position, 3)
            decompressed_numbers.extend([current_number] * (zero_count + 1))
        elif prefix == 0b10:
            sign, position = read_bits(binary_string, position, 1)
            abs_delta, position = read_bits(binary_string, position, 13)
            delta = -abs_delta if sign == 1 else abs_delta
            current_number += delta
            decompressed_numbers.append(current_number)
        elif prefix == 0b11:
            break

    return decompressed_numbers


# Function to read numbers from a text file, compress them, and write to a .bin file
def compress_to_bin_file(input_txt_file, output_bin_file):
    # Read numbers from the text file
    try:
        with open(input_txt_file, 'r') as file:
            numbers = [int(line.strip()) for line in file if line.strip().isdigit()]
    except FileNotFoundError:
        print(f"Error: The file {input_txt_file} does not exist.")
        return


    # Compress the numbers
    compressed_stream = compression(numbers)

    # Convert binary stream to bytes
    byte_array = bytearray()
    for i in range(0, len(compressed_stream), 8):
        byte = 0
        for bit in compressed_stream[i:i + 8]:
            byte = (byte << 1) | bit
        byte_array.append(byte)

    # Write the compressed bytes to a binary file
    with open(output_bin_file, 'wb') as file:
        file.write(byte_array)

# Function to read a .bin file, decompress the numbers, and write to a .txt file
def decompress_to_txt_file(input_bin_file, output_txt_file):
    # Read the binary file
    try:
        with open(input_bin_file, 'rb') as file:
            byte_array = file.read()
    except FileNotFoundError:
        print(f"Error: The file {input_bin_file} does not exist.")
        return

    # Convert bytes back to binary stream
    binary_stream = []
    for byte in byte_array:
        for i in range(7, -1, -1):
            binary_stream.append((byte >> i) & 1)

    # Decompress the binary stream
    decompressed_numbers = decompression(binary_stream)

    # Write the decompressed numbers to the text file
    with open(output_txt_file, 'w') as file:
        for number in decompressed_numbers:
            file.write(f"{number}\n")