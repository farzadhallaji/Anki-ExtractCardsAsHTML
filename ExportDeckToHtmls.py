from aqt import mw, utils
from aqt.qt import *
from os.path import expanduser, join
import os
import base64
import re

html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        /* Soothing background and text colors for eye comfort */
        body {
            background-color: #2D2D2D;  /* Dark, but not black, background */
            color: #D4D4D4;  /* Soft off-white for text */
            font-family: Arial, sans-serif;
            line-height: 1.6;  /* Increased line height for better readability */
        }

        /* Card container with soft rounded edges and comfortable padding */
        .card-container {
            margin: 20px;
            padding: 20px;
            border: 1px solid #444;  /* Darker gray for subtle borders */
            border-radius: 12px;  /* Slightly larger border radius */
            background-color: #3B3B3B;  /* Slightly lighter background for card area */
        }

        /* Grid layout for aligning field-name and field-value */
        .field-container {
            display: grid;
            grid-template-columns: 150px auto; /* Define two columns: one for the field-name, one for the field-value */
            gap: 10px; /* Adds space between the columns */
            align-items: center; /* Aligns items vertically in the middle */
        }

        /* Field name is made less prominent but still readable */
        /* Field name is made less prominent but still readable */
        .field-name {
            color: #BBBBBB;  /* Lighter gray for field names */
            font-size: 12px;  /* Slightly larger for easier readability */
            font-weight: normal;
            text-align: right; /* Align field name to the right */
            padding-right: 10px; /* Add spacing between field-name and field-value */
            width: 120px; /* Set a fixed width for all field-name elements */
            display: inline-block; /* Ensure the width is respected */
        }


        /* Field values are slightly larger and in soft white */
        .field-value {
            color: #E0E0E0;  /* Soft off-white for text */
            font-size: 14px;  /* Larger text for easier reading */
        }

        .field-value-bold {
            font-weight: bold;
            font-size: 22px;  /* Larger for emphasis */
            color: #FFA500;  /* Muted, warm orange */
        }

        /* Ensure field values are aligned to the left */
        .field-value,
        .field-value-bold {
            text-align: left;
        }

        /* Images are kept small but can be adjusted easily */
        img {
            width: 100px;
            height: 100px;
            object-fit: cover;
            border-radius: 8px;  /* Slight rounding to soften the edges */
            display: inline-block;  /* This makes the audio button inline */
            vertical-align: middle; /* Aligns the button to the middle of the line */
        }

        /* Links in a calming desaturated orange */
        a {
            color: #FFA500;  /* Warm, muted orange */
        }

        /* Custom audio button with SVG icon */
        button.audio-btn {
            background: none;
            width: 32px;
            height: 32px;
            border: none;
            cursor: pointer;
            display: flex;
            justify-content: center;
            align-items: center;
            display: inline-block;  /* This makes the audio button inline */
            vertical-align: middle; /* Aligns the button to the middle of the line */
        }

        /* The play button icon with a warm orange tone */
        button.audio-btn svg {
            width: 100%;
            height: 100%;
            fill: #FFA500;  /* Warm, muted orange */
        }

        button.audio-btn:focus {
            outline: none;  /* Remove focus outline for a cleaner look */
        }

    </style>
</head>
<body>
    {{body}}

    <script>
        function playAudio(id) {
            var audio = document.getElementById(id);
            if (audio.paused) {
                audio.play();
            } else {
                audio.pause();
            }
        }
    </script>
</body>
</html>
"""

class ExportToHtmlDialog(QDialog):
    def __init__(self):
        super().__init__(mw)
        self.setWindowTitle("Export Deck to HTMLs")
        self.deck_selection = QComboBox()
        self.deck_selection.addItems(mw.col.decks.allNames())
        
        self.save_btn = QPushButton("Export")
        self.save_btn.clicked.connect(self.export_to_html)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a Deck"))
        layout.addWidget(self.deck_selection)
        layout.addWidget(self.save_btn)
        self.setLayout(layout)

    def export_to_html(self):
        # Get selected deck
        deck_name = self.deck_selection.currentText()
        query = f'deck:"{deck_name}"'
        cids = mw.col.findCards(query)

        # Select directory path using QFileDialog
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", expanduser("~/Desktop"))

        if not directory:
            utils.showInfo("No directory selected.")
            return

        # Build HTML content and save each card to a separate HTML file
        self.save_cards_as_html(cids, directory)

    def save_cards_as_html(self, cids, directory):
        errors = []
        for i, cid in enumerate(cids):
            card = mw.col.getCard(cid)
            note = card.note()
            model = note.model()

            # Extract the CSS from the card's note model (card template)
            css = model.get('css', '')

            # Build the HTML for the card
            card_html = f"<div class='card-container'>\n"
            for field_name in note.keys():
                value = note[field_name].strip()  # Strip whitespace
                if value:  # Only include non-empty fields
                    # value = re.sub(r'{{[c|C][0-9]+::(.*?)}}', r'\1', value)  # Handle cloze deletion
                    value = re.sub(r'(?i)#0000ff', '#ff8c00', value)  # Case insensitive replacement
                    value = self.process_media(value)
                    # Special styling for "Word" field
                    if field_name in ['Word', 'word']:
                        field_html = f"<div class='field-value field-value-bold'> <span class='field-name'>{field_name}:</span> {value}</div><br>\n"
                    else:
                        field_html = f"<div class='field-value'> <span class='field-name'>{field_name}:</span> {value}</div>\n"

                    card_html += field_html

            card_html += f"<h6>Card {i+1}</h6> <hr/></div>"
            card_html = html_template.replace("{{style}}", css).replace("{{body}}", card_html)

            # Determine the filename based on a field value or index
            filename = f"card_{i+1}.html"
            # Find the "Word" or "word" field for the filename
            field_name_for_filename = None
            for field_name in note.keys():
                if field_name.lower() == 'word':
                    field_name_for_filename = field_name
                    break

            if field_name_for_filename:
                # Remove [sound:] and clean the value of the word field
                word_value = note[field_name_for_filename].strip()
                # Clean the word value, remove [sound:], &nbsp;, and other HTML entities
                word_value_cleaned = re.sub(r'\[sound:[^\]]+\]', '', word_value).strip()  # Remove [sound:]
                word_value_cleaned = re.sub(r'&nbsp;', '', word_value_cleaned).strip()  # Remove &nbsp;
                
                if word_value_cleaned:
                    filename = f"{word_value_cleaned}.html"
                else:
                    filename = f"card_{i+1}.html"  # Use a unique name if the cleaned word is empty
            else:
                filename = f"card_{i+1}.html"  # Use a unique name if no "Word" field exists

            # Clean the filename to remove invalid characters (non-alphanumeric, underscore, dash, period)
            filename = re.sub(r'[^\w\-_\. ]', '_', filename).strip('_')  # Also strip trailing/leading underscores


            # Write the HTML to the file in the selected directory
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, "w", encoding="utf8") as f:
                    f.write(card_html)
            except Exception as e:
                errors.append(f"Error writing file {filename}: {str(e)}")

        # Show a dialog after all cards are processed
        if errors:
            utils.showInfo(f"Finished with errors:\n" + "\n".join(errors))
        else:
            utils.showInfo(f"All cards exported successfully to {directory}!")

    def process_media(self, text):
        # Handle both images and audio
        text = self.convert_images(text)
        text = self.convert_audio(text)
        return text

    def convert_images(self, text):
        collection_path = mw.col.media.dir()
        matches = re.findall(r'src="([^"]+)"', text)
        for match in matches:
            image_path = os.path.join(collection_path, match)
            if os.path.exists(image_path):
                # Convert the image to base64
                b64_string = self.image_to_base64(image_path)
                if b64_string:
                    # Detect the image format and correctly insert it in the src attribute
                    mime_type = self.detect_mime_type(image_path)
                    # Insert the base64 image directly without additional <img> tag
                    img_tag = f'data:{mime_type};base64,{b64_string}'
                    text = text.replace(match, img_tag)
        return text

    def image_to_base64(self, image_path):
        """Convert an image file to base64 encoding."""
        try:
            with open(image_path, "rb") as img_file:
                return base64.b64encode(img_file.read()).decode('ascii')
        except Exception as e:
            print(f"Error converting image to base64: {str(e)}")
            return None

    def detect_mime_type(self, image_path):
        """Detect the mime type based on the file extension."""
        ext = os.path.splitext(image_path)[1].lower()
        if ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        elif ext == '.gif':
            return 'image/gif'
        else:
            return 'image/jpeg'  # Default to jpeg if unknown

    def convert_audio(self, text):
        collection_path = mw.col.media.dir()
        matches = re.findall(r'\[sound:(.+?)\]', text)
        for idx, match in enumerate(matches):
            audio_path = os.path.join(collection_path, match)
            if os.path.exists(audio_path):
                with open(audio_path, "rb") as audio_file:
                    b64_string = base64.b64encode(audio_file.read()).decode('ascii')
                    audio_tag = f'''
                    <audio id="audio_{idx}" src="data:audio/mpeg;base64,{b64_string}" type="audio/mpeg"></audio>
                    <button class="audio-btn" onclick="playAudio('audio_{idx}')">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-volume-up">
                            <path d="M3 9v6h4l5 5V4L7 9zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02M14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77"></path>
                        </svg>
                    </button>
                    '''
                    text = text.replace(f'[sound:{match}]', audio_tag)
        return text

# Add the action to Anki's menu
def show_export_dialog():
    dialog = ExportToHtmlDialog()
    dialog.exec()

action = QAction("Export Deck to HTML with Media", mw)
action.triggered.connect(show_export_dialog)
mw.form.menuTools.addAction(action)

shortcut = QShortcut(QKeySequence("Ctrl+Shift+M"), mw)
shortcut.activated.connect(show_export_dialog)
