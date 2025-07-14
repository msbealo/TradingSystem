import os

# Specify the directory containing your .rst files
source_directory = r"C:\\Users\\msbea\\Downloads\\backtrader-docs-master\\backtrader-docs-master\\docs"

# Specify the path for the output text file
output_file = r"C:\\Users\\msbea\\Downloads\\backtrader-docs-master\\backtrader-docs-master\\documentation_combined.txt"

# Open the output file in write mode
with open(output_file, 'w', encoding='utf-8') as outfile:
    # Walk through all directories and files
    for root, dirs, files in os.walk(source_directory):
        for filename in files:
            # Check if the file has a .rst extension
            if filename.endswith('.rst'):
                file_path = os.path.join(root, filename)
                with open(file_path, 'r', encoding='utf-8') as infile:
                    # Write the filename and path as a header
                    outfile.write(f'# File: {file_path}\n')
                    # Write the content of the file
                    outfile.write(infile.read())
                    # Add a newline separator between files
                    outfile.write('\n\n')

print(f'All .rst files have been combined into {output_file}')
