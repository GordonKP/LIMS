import re
file_path = r"\\ServerName\Lab Data\Lab\Data\Raw Data\MET\ICPMS1\25SL0064MET1.xlsx"
with open(file_path, 'rb') as f:
    raw = f.read()

# Look for anything in the control-character range except tab/newline
bad = re.findall(rb'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', raw)
print(set(bad))