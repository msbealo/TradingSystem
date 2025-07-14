import os

# Specify the directory containing your Python files
source_directory = 'C:\\Users\\msbea\\Downloads\\backtrader-docs-master\\backtrader-docs-master\\py\\'

# Specify the path for the output text file
output_file = 'C:\\Users\\msbea\\Downloads\\backtrader-docs-master\\backtrader-docs-master\\py\\combined_examples.txt'

# Open the output file in write mode
with open(output_file, 'w') as outfile:
    # Iterate over all files in the source directory
    for filename in os.listdir(source_directory):
        # Check if the file has a .py extension
        if filename.endswith('.py'):
            file_path = os.path.join(source_directory, filename)
            with open(file_path, 'r') as infile:
                # Write the filename as a header
                outfile.write(f'# File: {filename}\n')
                # Write the content of the file
                outfile.write(infile.read())
                # Add a newline separator between files
                outfile.write('\n\n')

print(f'All Python files have been combined into {output_file}')
