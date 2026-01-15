#!/usr/bin/env python3
"""
Convert sample_data.sql to use JSONB format for name fields.
"""

import re
import sys

def convert_name_to_jsonb(name):
    """Convert 'Name' to '{"en_US": "Name"}'::jsonb"""
    # Escape backslashes first
    name = name.replace('\\', '\\\\')
    # Then escape JSON double quotes
    name = name.replace('"', '\\"')
    return f"'{{\"en_US\": \"{name}\"}}'::jsonb"

def main():
    input_file = "sample_data.sql"
    output_file = "sample_data_fixed.sql"

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix product_template names
    # Pattern: (id, 'Name', ...)
    content = re.sub(
        r"\((\d+), '([^']+)', 'product', (\d+), ([0-9.]+),",
        lambda m: f"({m.group(1)}, {convert_name_to_jsonb(m.group(2))}, 'product', {m.group(3)}, {m.group(4)},",
        content
    )

    # Fix res_partner names
    # Pattern: (id, 'Name', ...)
    content = re.sub(
        r"\((\d+), '([^']+)', '([^']+@[^']+)'",
        lambda m: f"({m.group(1)}, {convert_name_to_jsonb(m.group(2))}, '{m.group(3)}'",
        content
    )

    # Fix product_category names
    # Pattern: (id, 'Name', NULL, ...)
    content = re.sub(
        r"\((\d+), '([^']+)', NULL, now\(\), now\(\)\)",
        lambda m: f"({m.group(1)}, {convert_name_to_jsonb(m.group(2))}, NULL, now(), now())",
        content
    )

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Converted {input_file} → {output_file}")
    print("Now run: cp sample_data_fixed.sql sample_data.sql")

if __name__ == "__main__":
    main()
