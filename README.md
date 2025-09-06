# Translating Assistant
Real-time screen text recognition and translation overlay using PaddleOCR and PyQt5. 

## Feature
- Capture screen content realtime periodically.
- Text extracted by PaddleOCR from sliced screenshots with mutliple processes.
- Translate recognized text with Google Translate API.
- The transparent overlay window appear on top of the screen, showing tranlated text positioned at detected regions.
- Designed for macOS, may be adapted for other platforms (not yet tested).  


## Requirements
- Python 3.9+  
- PyQt5  
- paddleocr  
- googletrans (or another translation library)  

## Usage
python main.py

<img width="655" height="380" alt="original" src="https://github.com/user-attachments/assets/107a475a-25b9-48fb-9585-781dcadae5d3" />
<img width="655" height="414" alt="translated" src="https://github.com/user-attachments/assets/722b1063-1721-4f01-a49f-68cd4f044620" />
