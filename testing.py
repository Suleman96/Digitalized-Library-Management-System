import os

# Check if the logo path exists and confirm its format for HTML usage
logo_path = r"images\Diplotech_Logo_2.png"
html_compatible_path = logo_path.replace("\\", "/")
exists = os.path.exists(logo_path)

logo_path, html_compatible_path, exists
