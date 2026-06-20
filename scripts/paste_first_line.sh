#!/bin/bash

# 1. Get current clipboard content explicitly expecting UTF-8
current_clip=$(xclip -selection clipboard -t UTF8_STRING -o 2>/dev/null)

if [ -z "$current_clip" ]; then
    exit 0
fi

# 2. Extract the first line safely
first_line=$(echo "$current_clip" | head -n 1)

# 3. Extract everything EXCEPT the first line
remaining_lines=$(echo "$current_clip" | tail -n +2)

# 4. Put ONLY the first line back into clipboard as a UTF-8 string
echo -n "$first_line" | xclip -selection clipboard -t UTF8_STRING

# 5. Short pause to ensure Mint catches up, then paste
sleep 0.15
xdotool key --clearmodifiers ctrl+v

# 6. Pause briefly, then load the remaining text back into the clipboard queue
sleep 0.15
echo -n "$remaining_lines" | xclip -selection clipboard -t UTF8_STRING
